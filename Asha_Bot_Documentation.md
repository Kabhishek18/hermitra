# ASHA Chatbot Documentation

## Introduction

ASHA is a specialized AI chatbot designed to provide tailored career guidance for women professionals. Built with a focus on understanding unique career challenges and opportunities for women, ASHA offers contextual, continuous conversations while maintaining ethical AI practices and robust security measures.

This documentation provides comprehensive information about ASHA's features, technical implementation, usage guidelines, and development roadmap.

## Table of Contents

1. [Key Offerings](#key-offerings)
2. [Technical Overview](#technical-overview)
3. [System Architecture](#system-architecture)
4. [Data Management](#data-management)
5. [Implementation Guide](#implementation-guide)
6. Implement guardrails and post-processing
7. Set up monitoring and logging
8. Deploy the system

### Example Code Snippets

#### 1. System Initialization

```javascript
// app.js - Main application file
const express = require('express');
const { MongoClient } = require('mongodb');
const { OllamaClient } = require('./services/ollama-client');
const { AWSBedrockClient } = require('./services/aws-client');
const { SessionManager } = require('./services/session-manager');
const { IntentClassifier } = require('./services/intent-classifier');
const { ResponseGenerator } = require('./services/response-generator');
const { ContextRetriever } = require('./services/context-retriever');

// Load environment variables
require('dotenv').config();

// Initialize Express app
const app = express();
app.use(express.json());

// Database connection
let db;
const mongoClient = new MongoClient(process.env.MONGODB_URI);

// Services initialization
let ollamaClient;
let awsClient;
let sessionManager;
let intentClassifier;
let contextRetriever;
let responseGenerator;

// Initialize services
async function initServices() {
  // Connect to MongoDB
  await mongoClient.connect();
  db = mongoClient.db(process.env.MONGODB_DB_NAME);
  console.log('Connected to MongoDB');
  
  // Initialize clients
  ollamaClient = new OllamaClient({
    endpoint: process.env.OLLAMA_ENDPOINT,
    model: process.env.OLLAMA_MODEL
  });
  
  awsClient = new AWSBedrockClient({
    region: process.env.AWS_BEDROCK_REGION,
    accessKeyId: process.env.AWS_BEDROCK_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_BEDROCK_SECRET_ACCESS_KEY,
    modelId: process.env.TITAN_MODEL_ID
  });
  
  // Initialize services
  sessionManager = new SessionManager(db);
  contextRetriever = new ContextRetriever(db, awsClient);
  intentClassifier = new IntentClassifier(ollamaClient);
  responseGenerator = new ResponseGenerator(ollamaClient);
  
  console.log('All services initialized');
}

// Start server
initServices().then(() => {
  app.listen(3000, () => {
    console.log('ASHA chatbot server running on port 3000');
  });
});
```

#### 2. Intent Classification Implementation

```javascript
// services/intent-classifier.js
class IntentClassifier {
  constructor(ollamaClient) {
    this.ollamaClient = ollamaClient;
    this.classificationModel = 'deepseek-r1:1.5b';
    this.careerIntents = [
      'career_guidance', 'job_search', 'skill_development',
      'interview_preparation', 'workplace_challenges'
    ];
  }
  
  async classifyIntent(query) {
    try {
      // Prepare system prompt for intent classification
      const systemPrompt = `
        You are an intent classifier for a career guidance chatbot.
        Classify the user query into one of the following categories:
        - career_guidance: Questions about career paths, growth, or decisions
        - job_search: Questions about finding jobs, applications, or job market
        - skill_development: Questions about learning new skills or improving existing ones
        - interview_preparation: Questions about interview techniques or preparation
        - workplace_challenges: Questions about handling situations at work
        - off_topic: Queries not related to career or professional development
        - inappropriate: Queries containing inappropriate content
        
        Respond with ONLY the category name.
      `;
      
      // Get classification from LLM
      const response = await this.ollamaClient.generate({
        model: this.classificationModel,
        prompt: systemPrompt,
        system: systemPrompt,
        user: query,
        options: {
          temperature: 0.1,
          max_tokens: 20
        }
      });
      
      // Extract category from response
      const category = response.trim().toLowerCase();
      
      return {
        intent: category,
        isCareerRelated: this.careerIntents.includes(category),
        isSafeQuery: category !== 'inappropriate',
      };
    } catch (error) {
      console.error('Intent classification error:', error);
      // Default to safe, career-related intent in case of error
      return {
        intent: 'general',
        isCareerRelated: true,
        isSafeQuery: true,
        error: error.message
      };
    }
  }
}

module.exports = { IntentClassifier };
```

#### 3. Context Retrieval Implementation

```javascript
// services/context-retriever.js
class ContextRetriever {
  constructor(db, awsClient) {
    this.db = db;
    this.awsClient = awsClient;
    this.embeddingsCollection = db.collection('embeddings');
    this.topK = 5; // Number of similar contexts to retrieve
  }
  
  async retrieveContext(query, userId) {
    try {
      // Generate embedding for the query
      const queryEmbedding = await this.awsClient.createEmbedding(query);
      
      // Perform vector search in MongoDB
      const relevantDocuments = await this.embeddingsCollection.aggregate([
        {
          $search: {
            knnBeta: {
              vector: queryEmbedding,
              path: "embedding",
              k: this.topK
            }
          }
        },
        {
          $project: {
            _id: 0,
            content: 1,
            metadata: 1,
            score: { $meta: "searchScore" }
          }
        }
      ]).toArray();
      
      // Filter by userId if specified
      const filteredDocuments = userId 
        ? relevantDocuments.filter(doc => doc.metadata.userId === userId)
        : relevantDocuments;
      
      // Format context for use in prompt
      return filteredDocuments.map(doc => ({
        content: doc.content,
        relevance: doc.score,
        timestamp: doc.metadata.timestamp
      }));
    } catch (error) {
      console.error('Context retrieval error:', error);
      return []; // Return empty context in case of error
    }
  }
  
  async assembleContext(userSession, retrievedContext, query) {
    // Get recent conversation history (last 5 exchanges)
    const recentHistory = userSession.conversations
      .slice(-5)
      .map(conv => ({
        role: 'user',
        content: conv.query,
        timestamp: conv.timestamp
      }))
      .concat(userSession.conversations.slice(-5).map(conv => ({
        role: 'assistant',
        content: conv.response,
        timestamp: conv.timestamp
      })))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    // Format user preferences if available
    const userPreferences = userSession.preferences 
      ? `User Preferences:
         - Career Interests: ${userSession.preferences.career_interests?.join(', ') || 'Not specified'}
         - Experience Level: ${userSession.preferences.experience_level || 'Not specified'}
         - Industry: ${userSession.preferences.industry || 'Not specified'}`
      : 'No user preferences available.';
    
    // Format retrieved context
    const formattedContext = retrievedContext
      .map(ctx => `Related Information:\n${ctx.content}`)
      .join('\n\n');
    
    return {
      history: recentHistory,
      currentQuery: query,
      userPreferences,
      retrievedContext: formattedContext
    };
  }
}

module.exports = { ContextRetriever };
```

#### 4. Response Generation Implementation

```javascript
// services/response-generator.js
class ResponseGenerator {
  constructor(ollamaClient) {
    this.ollamaClient = ollamaClient;
    this.defaultModel = 'mistral:latest';
    this.advancedModel = 'llama3.3:latest';
  }
  
  async generateResponse(promptContext, options = {}) {
    try {
      // Determine which model to use based on query complexity
      const modelToUse = options.useAdvancedModel ? this.advancedModel : this.defaultModel;
      
      // Construct system prompt with guardrails
      const systemPrompt = `
        You are ASHA, a specialized career guidance assistant for women professionals.
        
        Guidelines:
        - Provide tailored career guidance based on the user's background and goals
        - Maintain professional and supportive tone
        - Do not offer personal opinions or predictions
        - Do not reinforce stereotypes
        - Keep responses focused on career development
        - Use concrete examples when appropriate
        - If unsure, acknowledge limitations instead of making up information
        
        User Preferences:
        ${promptContext.userPreferences}
        
        Retrieved Context:
        ${promptContext.retrievedContext}
      `;
      
      // Format conversation history for the LLM
      const messages = [
        ...promptContext.history,
        { role: 'user', content: promptContext.currentQuery }
      ];
      
      // Generate response
      const response = await this.ollamaClient.generate({
        model: modelToUse,
        messages: messages,
        system: systemPrompt,
        options: {
          temperature: 0.7,
          max_tokens: 1024,
          ...options
        }
      });
      
      return this.applySafeguards(response);
    } catch (error) {
      console.error('Response generation error:', error);
      return "I'm sorry, I encountered an issue while processing your request. Let's try a different approach or question.";
    }
  }
  
  applySafeguards(response) {
    let safeguardedResponse = response;
    
    // Apply post-processing safeguards
    
    // Check for personal opinions markers
    const opinionMarkers = ['I believe', 'In my opinion', 'I think', 'I feel'];
    opinionMarkers.forEach(marker => {
      safeguardedResponse = safeguardedResponse.replace(
        new RegExp(`${marker}\\s`, 'gi'),
        'Research suggests '
      );
    });
    
    // Check for off-topic content
    if (!this.isCareerRelated(safeguardedResponse)) {
      safeguardedResponse += "\n\nI'd be happy to discuss more about your career goals and professional development if you'd like to explore that further.";
    }
    
    // Check for gender stereotypes
    const stereotypeMarkers = [
      'women are naturally', 'women tend to be more', 'women should',
      'men are better at', 'typical female', 'typical male'
    ];
    
    stereotypeMarkers.forEach(marker => {
      if (safeguardedResponse.toLowerCase().includes(marker.toLowerCase())) {
        safeguardedResponse += "\n\nI want to note that individual capabilities vary greatly regardless of gender, and career success depends on many factors including skills, experience, and opportunities.";
        break;
      }
    });
    
    return safeguardedResponse;
  }
  
  isCareerRelated(text) {
    const careerTerms = [
      'career', 'job', 'work', 'profession', 'skill', 'interview',
      'resume', 'workplace', 'industry', 'position', 'role',
      'employment', 'company', 'business', 'leadership'
    ];
    
    const lowerText = text.toLowerCase();
    return careerTerms.some(term => lowerText.includes(term));
  }
}

module.exports = { ResponseGenerator };
```

## API Reference {#api-reference}

### Core API Endpoints

#### 1. Chat Endpoint

```
POST /api/chat
```

Request Body:
```json
{
  "userId": "string",
  "message": "string"
}
```

Response:
```json
{
  "response": "string",
  "conversationId": "string",
  "intent": "string"
}
```

#### 2. User Session Endpoint

```
GET /api/user/:userId/session
```

Response:
```json
{
  "userId": "string",
  "preferences": {
    "career_interests": ["string"],
    "experience_level": "string",
    "industry": "string"
  },
  "conversationCount": "number",
  "firstInteraction": "datetime",
  "lastActive": "datetime"
}
```

#### 3. Update User Preferences

```
PUT /api/user/:userId/preferences
```

Request Body:
```json
{
  "preferences": {
    "career_interests": ["string"],
    "experience_level": "string",
    "industry": "string"
  }
}
```

Response:
```json
{
  "success": "boolean",
  "message": "string"
}
```

### Internal API Methods

#### Session Manager

- `getUserSession(userId)`: Retrieves or creates a user session
- `updateUserSession(userId, query, response)`: Updates session with new conversation
- `updateUserPreferences(userId, preferences)`: Updates user preferences

#### Context Retriever

- `retrieveContext(query, userId)`: Retrieves relevant context based on query
- `assembleContext(userSession, retrievedContext, query)`: Assembles context for LLM

#### Intent Classifier

- `classifyIntent(query)`: Classifies user query into intent categories

#### Response Generator

- `generateResponse(promptContext, options)`: Generates response using LLM
- `applySafeguards(response)`: Applies post-processing guardrails

## Guardrails & Limitations {#guardrails-limitations}

### System Guardrails

ASHA implements the following guardrails to ensure appropriate and helpful interactions:

#### 1. Content Guardrails
- **Focus on Career Guidance**: Responses are limited to career-related topics
- **No Personal Opinions**: The system avoids offering personal opinions or predictions
- **No Stereotyping**: Responses are designed to avoid reinforcing gender stereotypes
- **Ethical Guidance**: Career advice follows ethical principles and practices

#### 2. Interaction Guardrails
- **Stay On Topic**: The system redirects off-topic conversations back to career guidance
- **No Sensitive Data Retention**: Personal identifiable information is minimized
- **Error Handling**: Graceful fallbacks for unanswerable questions
- **Clear Limitations**: Transparent communication about system capabilities and limitations

### Known Limitations

1. **Domain Specialization**: ASHA is specialized for career guidance and not designed as a general-purpose assistant
2. **Model Limitations**: 
   - Context window constraints of underlying LLMs
   - Performance dependent on quality of training data
3. **Technical Limitations**:
   - Local processing constraints based on hardware
   - Vector search performance trade-offs
4. **Knowledge Boundaries**:
   - Limited to information available in its knowledge base
   - Not connected to real-time job market data unless integrated

## Deployment Guide {#deployment-guide}

### System Requirements

#### Minimum Requirements
- CPU: 4+ cores
- RAM: 16GB+ (32GB recommended for llama3.3)
- Storage: 50GB+ SSD
- Operating System: Linux (Ubuntu 22.04 LTS recommended)

#### Recommended Setup for Production
- CPU: 8+ cores
- RAM: 64GB
- Storage: 500GB SSD
- GPU: NVIDIA with 8GB+ VRAM (for accelerated inference)

### Deployment Steps

#### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/asha-chatbot.git
cd asha-chatbot

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Install dependencies
npm install
```

#### 2. Database Setup

```bash
# Start MongoDB (if using local installation)
mongod --dbpath ./data

# Initialize database and collections
node scripts/init-db.js
```

#### 3. Ollama Setup

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull mistral:latest
ollama pull deepseek-r1:1.5b
ollama pull llama3.3:latest
```

#### 4. Application Deployment

```bash
# Development mode
npm run dev

# Production mode
npm run build
npm start
```

#### 5. Docker Deployment (Optional)

```bash
# Build Docker image
docker build -t asha-chatbot .

# Run container
docker run -p 3000:3000 --env-file .env asha-chatbot
```

### Deployment Considerations

1. **Security**: Ensure AWS credentials are properly secured
2. **Scalability**: Consider containerization for horizontal scaling
3. **Backups**: Implement regular MongoDB backups
4. **Logging**: Configure appropriate logging levels
5. **Monitoring**: Set up health checks and performance monitoring

## Monitoring & Maintenance {#monitoring-maintenance}

### Key Metrics to Monitor

#### Performance Metrics
- Response generation time
- Intent classification accuracy
- Vector search latency
- Database query performance
- Memory and CPU utilization

#### Quality Metrics
- Response relevance rating
- User satisfaction scores
- Conversation completion rate
- Guardrail trigger frequency
- Error rates by component

### Maintenance Tasks

#### Regular Maintenance
1. Database optimization and cleanup
2. Model updates and evaluation
3. Security patches and dependency updates
4. Log rotation and analysis
5. Performance tuning

#### Troubleshooting Common Issues
1. High latency troubleshooting steps
2. Error handling and recovery procedures
3. Database connection issues
4. Model loading failures
5. AWS connectivity problems

### Logging Strategy

```javascript
// Example logging configuration
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'asha-chatbot' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    })
  ]
});

// Usage
logger.info('Service started', { component: 'app' });
logger.error('Error occurred', { component: 'responseGenerator', error: err.message });
```

## Future Development {#future-development}

### Roadmap

#### Short-term Improvements
1. Enhanced personalization based on user interaction patterns
2. Integration with additional career resources and databases
3. Improved guardrails and bias detection algorithms
4. Performance optimizations for local model inference
5. Enhanced error recovery mechanisms

#### Medium-term Goals
1. Multi-modal support (voice interactions)
2. Integration with job market analytics
3. Industry-specific specialization modules
4. Advanced personalization based on career stage
5. Collaborative filtering for resource recommendations

#### Long-term Vision
1. Adaptive learning from aggregate user interactions
2. Integration with mentorship platforms
3. Specialized modules for entrepreneurship, leadership, and other career paths
4. Real-time job market insights and forecasting
5. Cross-platform availability and API access

### Extension Points

The ASHA system is designed with the following extension points:

1. **Model Swapping**: Architecture supports changing underlying LLMs
2. **Knowledge Integration**: Additional knowledge sources can be added to the RAG pipeline
3. **Intent Expansion**: New intent categories can be added to the classifier
4. **UI Integration**: API endpoints support various frontend implementations
5. **Analytics Extension**: Monitoring framework can be extended for deeper insights

### Contribution Guidelines

For developers looking to contribute to ASHA:

1. Follow the code style guide in the repository
2. Write unit tests for new components
3. Document API changes and new features
4. Submit PRs with clear descriptions of changes
5. Address security and ethical considerations in all contributions. [API Reference](#api-reference)
7. [Guardrails & Limitations](#guardrails-limitations)
8. [Deployment Guide](#deployment-guide)
9. [Monitoring & Maintenance](#monitoring-maintenance)
10. [Future Development](#future-development)

## Key Offerings {#key-offerings}

### Tailored Career Guidance for Women
ASHA provides specialized career guidance that addresses the unique challenges and opportunities women face in their professional journeys. This includes advice on:
- Career advancement strategies
- Workplace gender dynamics
- Negotiation techniques
- Leadership development
- Work-life balance
- Industry-specific guidance

### Contextual and Continuous Conversations
ASHA maintains conversation context across sessions, allowing for more personalized and coherent interactions over time. The system:
- Remembers user preferences and career history
- Builds on previous conversations
- Provides increasingly tailored advice as it learns about the user
- Maintains professional context without requiring repetitive information

### Integration with Women's Professional Communities
ASHA is designed to complement existing women's professional networks and resources, with the ability to:
- Reference relevant community resources
- Suggest networking opportunities
- Provide information on women-focused professional events
- Connect advice to broader support ecosystems

## Technical Overview {#technical-overview}

### Technology Stack

#### Local Resources
- **Database**: MongoDB (local)
- **LLM Deployment**: Ollama with the following models:
  - `mistral:latest` (4.1 GB)
  - `deepseek-r1:1.5b` (1.1 GB)
  - `llama3.3:latest` (42 GB)

#### Cloud Resources
- **Vector Embeddings**: AWS Bedrock with Titan embedding model
  - Model ID: `amazon.titan-embed-text-v2:0`
  - Region: `us-east-1`

### AI Architecture
ASHA employs a hybrid architecture combining:
- **CAG (Conversational AI Generation)**: For intent classification and maintaining conversation flow
- **RAG (Retrieval Augmented Generation)**: For retrieving relevant information from previous conversations and knowledge base

This architecture enables ASHA to provide responses that are both contextually relevant and grounded in reliable information.

## System Architecture {#system-architecture}

ASHA's system architecture follows a modular design with the following key components:

### 1. Intent Classification Module
- Uses lightweight models (deepseek-r1:1.5b) to determine user intent
- Categorizes queries into career-related and non-career-related intents
- Acts as the first layer of guardrails to keep conversations on track

### 2. Context Retrieval System
- Generates vector embeddings for user queries using AWS Bedrock
- Performs semantic search against the vector database to find relevant context
- Retrieves prior conversation history to maintain continuity
- Assembles the retrieved context for the response generation phase

### 3. Response Generation Engine
- Utilizes local Ollama models (mistral or llama3.3) to generate responses
- Incorporates retrieved context, conversation history, and user preferences
- Implements system prompts with appropriate guardrails and guidelines
- Balances helpfulness with ethical considerations

### 4. Session Management System
- Tracks user sessions and conversation history
- Stores and retrieves user preferences
- Manages vector embeddings for past interactions
- Ensures data privacy and security

### 5. Post-Processing & Guardrails
- Filters responses for alignment with guidelines
- Removes potential biases or stereotypes
- Ensures responses remain focused on career guidance
- Handles edge cases and error scenarios

## Data Management {#data-management}

### Data Sources
ASHA works with two primary data sources:
1. `herkey.session.json`: Raw session data without vector embeddings
2. `herkey.sessions.embedding.json`: Session data with AWS vector embeddings

### Data Models

#### Session Data Model
```json
{
  "userId": "string",
  "conversations": [
    {
      "timestamp": "datetime",
      "query": "string",
      "response": "string"
    }
  ],
  "preferences": {
    "career_interests": ["string"],
    "experience_level": "string",
    "industry": "string"
  },
  "createdAt": "datetime",
  "lastActive": "datetime"
}
```

#### Embedding Data Model
```json
{
  "userId": "string",
  "queryId": "string",
  "content": "string",
  "embedding": [float],
  "metadata": {
    "timestamp": "datetime",
    "type": "string"
  }
}
```

### Database Schema

ASHA uses MongoDB with the following collections:

#### Collections
1. `sessions`: Stores user session data
2. `embeddings`: Stores vector embeddings for conversation context
3. `interaction_logs`: Tracks system interactions for monitoring
4. `error_logs`: Records system errors for troubleshooting

#### Indexes
- Vector search index on the `embeddings` collection
- User ID index on the `sessions` collection
- Timestamp indexes for efficient date-based queries

### Data Privacy & Retention
- Sensitive data is encrypted at rest and in transit
- Clear data retention policies with automatic purging of old data
- Compliance with data privacy regulations
- Minimization of PII (Personally Identifiable Information)

## Implementation Guide {#implementation-guide}

### Prerequisites
- MongoDB installed and running locally
- Ollama installed with required models
- AWS Bedrock account with appropriate permissions
- Node.js environment for the application server

### Environment Setup

1. Configure environment variables:
```
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=asha_chatbot

# Ollama Configuration
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=mistral:latest

# AWS Bedrock Configuration
AWS_BEDROCK_SERVICE_NAME=bedrock-runtime
AWS_BEDROCK_ACCESS_KEY_ID=your_access_key
AWS_BEDROCK_SECRET_ACCESS_KEY=your_secret_key
AWS_BEDROCK_REGION=us-east-1
TITAN_MODEL_ID=amazon.titan-embed-text-v2:0
```

2. Initialize MongoDB collections:
```javascript
db.createCollection("sessions");
db.createCollection("embeddings");
db.createCollection("interaction_logs");
db.createCollection("error_logs");

// Create indexes
db.embeddings.createIndex({ userId: 1 });
db.sessions.createIndex({ userId: 1 }, { unique: true });
db.interaction_logs.createIndex({ timestamp: 1 });
db.error_logs.createIndex({ timestamp: 1 });
```

3. Set up vector search capability in MongoDB:
```javascript
db.embeddings.createIndex(
  { embedding: "vector" },
  {
    name: "vector_index",
    vectorOptions: {
      dimensions: 1536, // Titan embedding dimensions
      similarity: "cosine"
    }
  }
);
```

### Core Implementation Steps

1. Initialize the system
2. Set up intent classification
3. Implement the RAG pipeline
4. Configure response generation
5. Establish session management
6. Apply post-processing and guardrails