# ASHA Chatbot Implementation Approach

## Overview
This document outlines the implementation approach for ASHA, a specialized chatbot designed to provide career guidance for women. The implementation follows a hybrid CAG (Conversational AI Generation) + RAG (Retrieval Augmented Generation) architecture to deliver contextual, continuous conversations with appropriate guardrails.

## Implementation Workflow

### 1. System Initialization
- **Configuration Loading**: Load environment variables and configuration parameters.
- **Model Initialization**: Initialize local Ollama models and AWS Bedrock connections.
- **Database Connection**: Establish connection to local MongoDB instance.
- **Vector Database Setup**: Configure vector search capabilities for session embeddings.

```javascript
// Sample initialization code
const config = require('./config');
const { MongoClient } = require('mongodb');
const { OllamaClient } = require('./ollama-client');
const { AWSBedrockClient } = require('./aws-client');

// Initialize MongoDB
const mongoClient = new MongoClient(config.MONGODB_URI);
const db = mongoClient.db('asha_chatbot');
const sessionsCollection = db.collection('sessions');
const embeddingsCollection = db.collection('embeddings');

// Initialize Ollama client with preferred model
const ollamaClient = new OllamaClient({
  endpoint: config.OLLAMA_ENDPOINT,
  model: config.OLLAMA_MODEL || 'mistral:latest'
});

// Initialize AWS Bedrock client for embeddings
const awsClient = new AWSBedrockClient({
  region: process.env.AWS_BEDROCK_REGION,
  accessKeyId: process.env.AWS_BEDROCK_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_BEDROCK_SECRET_ACCESS_KEY,
  modelId: process.env.TITAN_MODEL_ID
});
```

### 2. User Query Processing

#### 2.1 Preprocessing & Intent Classification
- **Query Sanitization**: Clean and normalize user input.
- **Intent Classification**: Use a lightweight model to determine if the query is career-related.
- **Safety Checks**: Apply initial filtering for inappropriate content.

```javascript
async function processUserQuery(query, userId) {
  // Sanitize query
  const sanitizedQuery = sanitizeInput(query);
  
  // Classify intent using CAG
  const intentClassification = await classifyIntent(sanitizedQuery);
  
  if (intentClassification.isSafeQuery === false) {
    return generateSafetyResponse(intentClassification.reason);
  }
  
  if (intentClassification.isCareerRelated) {
    // Proceed with RAG pipeline
    return await generateCareerResponse(sanitizedQuery, userId);
  } else {
    // Handle non-career related query with appropriate guardrails
    return generateOffTopicResponse(intentClassification.intent);
  }
}

async function classifyIntent(query) {
  // Use a smaller, efficient model for classification
  const response = await ollamaClient.classify(query, {
    model: 'deepseek-r1:1.5b', // Lighter model for classification
    options: {
      classificationCategories: [
        'career_guidance', 'job_search', 'skill_development', 
        'interview_preparation', 'workplace_challenges',
        'off_topic', 'inappropriate'
      ]
    }
  });
  
  return {
    intent: response.category,
    isCareerRelated: ['career_guidance', 'job_search', 'skill_development', 
                     'interview_preparation', 'workplace_challenges'].includes(response.category),
    isSafeQuery: response.category !== 'inappropriate',
    confidence: response.confidence,
    reason: response.reason
  };
}
```

#### 2.2 Context Retrieval (RAG)
- **Session Context Loading**: Retrieve user's conversation history.
- **Vector Search**: Use AWS embeddings to find relevant information.
- **Context Assembly**: Combine conversation history with retrieved information.

```javascript
async function generateCareerResponse(query, userId) {
  // Get user session
  const userSession = await getUserSession(userId);
  
  // Generate embeddings using AWS Bedrock
  const queryEmbedding = await awsClient.createEmbedding(query);
  
  // Retrieve relevant context using vector search
  const relevantContexts = await retrieveRelevantContext(queryEmbedding);
  
  // Assemble context for LLM
  const promptContext = assembleContext(userSession, relevantContexts, query);
  
  // Generate response using Ollama
  const response = await generateResponse(promptContext);
  
  // Apply post-processing guardrails
  const safeguardedResponse = applySafeguards(response);
  
  // Update user session
  await updateUserSession(userId, query, safeguardedResponse);
  
  return safeguardedResponse;
}

async function retrieveRelevantContext(queryEmbedding) {
  // Vector search in MongoDB
  const relevantDocuments = await embeddingsCollection.aggregate([
    {
      $search: {
        knnBeta: {
          vector: queryEmbedding,
          path: "embedding",
          k: 5
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
  
  return relevantDocuments;
}
```

#### 2.3 Response Generation
- **Prompt Construction**: Format the context and query for the LLM.
- **LLM Processing**: Use Ollama model to generate the response.
- **Post-processing**: Apply guardrails and ensure response quality.

```javascript
async function generateResponse(promptContext) {
  // Construct the prompt with system message and guardrails
  const systemPrompt = `You are ASHA, a specialized career guidance assistant for women professionals.
  - Provide tailored career guidance based on the user's background and goals
  - Maintain professional and supportive tone
  - Do not offer personal opinions or predictions
  - Do not reinforce stereotypes
  - Keep responses focused on career development
  - Use concrete examples when appropriate
  - If unsure, acknowledge limitations instead of making up information`;
  
  const fullPrompt = {
    system: systemPrompt,
    messages: [
      ...promptContext.history,
      { role: 'user', content: promptContext.currentQuery }
    ],
    context: promptContext.retrievedContext
  };
  
  // Generate response using Ollama
  const response = await ollamaClient.generate(fullPrompt, {
    model: 'llama3.3:latest',
    temperature: 0.7,
    maxTokens: 1024
  });
  
  return response.content;
}

function applySafeguards(response) {
  // Apply post-processing safeguards to ensure response adheres to guidelines
  let safeguardedResponse = response;
  
  // Check for and remove personal opinions
  safeguardedResponse = removePersonalOpinions(safeguardedResponse);
  
  // Check for and correct stereotypes
  safeguardedResponse = mitigateStereotypes(safeguardedResponse);
  
  // Ensure response stays on career topic
  safeguardedResponse = enforceCareerFocus(safeguardedResponse);
  
  return safeguardedResponse;
}
```

### 3. Session Management
- **Session Creation**: Initialize new user sessions.
- **Session Updates**: Store conversations and context.
- **Session Retrieval**: Load past conversations to maintain context.

```javascript
async function getUserSession(userId) {
  // Get or create user session
  let userSession = await sessionsCollection.findOne({ userId });
  
  if (!userSession) {
    // Initialize new session
    userSession = {
      userId,
      conversations: [],
      preferences: {},
      createdAt: new Date(),
      lastActive: new Date()
    };
    
    await sessionsCollection.insertOne(userSession);
  }
  
  return userSession;
}

async function updateUserSession(userId, query, response) {
  // Update user session with new conversation
  const conversation = {
    timestamp: new Date(),
    query,
    response,
  };
  
  await sessionsCollection.updateOne(
    { userId },
    { 
      $push: { conversations: conversation },
      $set: { lastActive: new Date() }
    }
  );
  
  // Generate and store embedding for this conversation
  const embedding = await awsClient.createEmbedding(query + " " + response);
  
  await embeddingsCollection.insertOne({
    userId,
    queryId: conversation.timestamp.toISOString(),
    content: query + " " + response,
    embedding,
    metadata: {
      timestamp: conversation.timestamp,
      type: 'conversation'
    }
  });
}
```

### 4. System Monitoring & Feedback Loop
- **Performance Tracking**: Monitor response times and quality.
- **Error Handling**: Capture and process errors gracefully.
- **Feedback Integration**: Collect and utilize user feedback.

```javascript
function logInteraction(userId, query, response, metrics) {
  // Log interaction for monitoring and improvement
  const logEntry = {
    timestamp: new Date(),
    userId,
    query,
    response,
    metrics: {
      processingTimeMs: metrics.processingTime,
      intentConfidence: metrics.intentConfidence,
      retrievalCount: metrics.retrievalCount
    }
  };
  
  db.collection('interaction_logs').insertOne(logEntry);
}

function handleError(error, userId, query) {
  // Log error
  console.error(`Error processing query for user ${userId}:`, error);
  
  // Store error in database for later analysis
  db.collection('error_logs').insertOne({
    timestamp: new Date(),
    userId,
    query,
    error: {
      message: error.message,
      stack: error.stack
    }
  });
  
  // Return graceful error message to user
  return {
    type: 'error',
    message: "I'm sorry, I encountered an issue processing your request. Let's try a different approach."
  };
}
```

## Implementation Phases

### Phase 1: Core Functionality
- Set up basic infrastructure (MongoDB, Ollama)
- Implement intent classification
- Build RAG pipeline with AWS embeddings
- Create basic conversation flow

### Phase 2: Guardrails & Enhancement
- Implement comprehensive safeguards
- Add specialized career guidance features
- Enhance context management
- Improve response quality

### Phase 3: Integration & Scaling
- Connect with women's professional communities
- Implement feedback loops
- Optimize performance
- Enhance monitoring and analytics

## Testing Strategy

### Unit Testing
Test individual components:
- Intent classifier accuracy
- Embedding generation
- Safeguard effectiveness

### Integration Testing
Test interaction between components:
- Full conversation flows
- Context retrieval accuracy
- Session management

### System Testing
Test the entire system:
- End-to-end conversation scenarios
- Performance under load
- Error handling

### User Testing
Gather feedback from real users:
- Response quality and relevance
- Conversation naturalness
- Career guidance effectiveness

## Deployment Considerations

### Environment Setup
- Configure development, staging, and production environments
- Set up proper security measures for AWS credentials
- Implement proper logging and monitoring

### Scaling Plan
- Monitor system performance metrics
- Identify bottlenecks
- Plan for incremental scaling as user base grows

### Maintenance Strategy
- Regular model updates
- Database maintenance
- Security audits

## Success Metrics
- Response relevance rate
- User satisfaction scores
- Conversation completion rate
- Average session duration
- Return user percentage