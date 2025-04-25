# ASHA Chatbot Architecture Document

## Architecture Overview

ASHA is designed using a hybrid Conversational AI Generation (CAG) + Retrieval Augmented Generation (RAG) architecture to provide tailored career guidance for women. This architecture enables contextual understanding, knowledge retrieval, and specialized response generation while maintaining appropriate guardrails.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   User Query    │────▶│Intent Classifier│────▶│    Retriever    │
│                 │     │      (CAG)      │     │      (RAG)      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     Response    │◀────│ Post-Processing │◀────│   Local LLM     │
│                 │     │    Guardrails   │     │    (Ollama)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## System Components

### 1. Infrastructure Components

#### 1.1 Local Resources
- **MongoDB**: Stores session data, conversation history, and vector embeddings
  - Collections: `sessions`, `embeddings`, `interaction_logs`, `error_logs`
  - Indexes: Vector search-enabled index on embeddings collection

- **Ollama**: Provides local LLM capabilities
  - Models:
    - `mistral:latest` (4.1 GB) - Primary generation model
    - `deepseek-r1:1.5b` (1.1 GB) - Intent classification model
    - `llama3.3:latest` (42 GB) - Advanced response generation for complex queries

#### 1.2 Cloud Resources
- **AWS Bedrock**:
  - Used for generating text embeddings with `amazon.titan-embed-text-v2:0`
  - Region: `us-east-1`

### 2. Data Components

#### 2.1 Session Data
- `herkey.session.json`: Contains raw session data without vector embeddings
  - Structure:
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

#### 2.2 Embedding Data
- `herkey.sessions.embedding.json`: Contains session data with AWS vector embeddings
  - Structure:
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

### 3. Functional Components

#### 3.1 Intent Classification (CAG)
- **Purpose**: Determine the category and relevance of user queries
- **Implementation**:
  - Uses lightweight `deepseek-r1:1.5b` model for efficient classification
  - Categorizes queries into predefined intents related to career guidance
  - Acts as first-line filtering mechanism for off-topic or inappropriate content

#### 3.2 Retrieval System (RAG)
- **Purpose**: Find relevant context from previous conversations and knowledge base
- **Implementation**:
  - Generates embeddings for user queries using AWS Bedrock's Titan model
  - Performs vector search in MongoDB to find similar content
  - Retrieves top-k most relevant contexts based on semantic similarity
  - Assembles retrieved context with user session history

#### 3.3 Generation System (LLM)
- **Purpose**: Generate contextually appropriate, helpful responses
- **Implementation**:
  - Uses local Ollama models (`mistral:latest` or `llama3.3:latest`)
  - Constructs prompts with system instructions, user context, and retrieval results
  - Parameters optimized for conversational quality and guardrail adherence

#### 3.4 Post-Processing & Guardrails
- **Purpose**: Ensure responses adhere to system guidelines and quality standards
- **Implementation**:
  - Filter responses for personal opinions or predictions
  - Check for and mitigate gender bias and stereotypes
  - Ensure focus remains on career guidance
  - Format responses for readability and engagement

#### 3.5 Session Management
- **Purpose**: Maintain conversation context and user preferences
- **Implementation**:
  - Store and retrieve conversation history
  - Track user preferences and career interests
  - Update session data with each interaction
  - Generate and store embeddings for future retrieval

## Data Flow Architecture

### 1. Query Processing Flow

```
User Query
   │
   ▼
┌─────────────────────┐
│  Input Processing   │
│ - Query sanitization│
│ - Initial filtering │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Intent Classification│
│ - deepseek-r1 model  │
│ - Category detection │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Intent Router     │
└─────────┬───────────┘
          │
          ├───────────────┐
          │               │
          ▼               ▼
┌─────────────────┐ ┌────────────────┐
│Career-Related   │ │Non-Career      │
│Intent           │ │Intent          │
└─────────┬───────┘ └────────┬───────┘
          │                  │
          ▼                  ▼
┌─────────────────┐ ┌────────────────┐
│RAG Pipeline     │ │Direct Response │
└─────────┬───────┘ └────────┬───────┘
          │                  │
          └──────────┬───────┘
                     │
                     ▼
┌─────────────────────────────┐
│     Response Generation     │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│    Post-Processing          │
│  - Guardrail application    │
│  - Quality assurance        │
└─────────────┬───────────────┘
              │
              ▼
          Response
```

### 2. RAG Pipeline Flow

```
┌─────────────────────┐
│  User Query + History│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Generate Embeddings │
│  - AWS Bedrock       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Vector Search      │
│  - MongoDB vector   │
│    search           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Context Assembly   │
│  - Combine retrieved│
│    context          │
│  - Session history  │
│  - User preferences │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Prompt Engineering │
│  - System message   │
│  - User query       │
│  - Context          │
│  - Guardrails       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  LLM Generation     │
│  - Ollama model     │
└─────────┬───────────┘
          │
          ▼
     LLM Response
```

### 3. Session Management Flow

```
┌─────────────────────┐
│  User Interaction   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Session Lookup     │
└─────────┬───────────┘
          │
          ├───────────────┐
          │               │
          ▼               ▼
┌─────────────────┐ ┌────────────────┐
│Existing Session │ │New Session     │
└─────────┬───────┘ └────────┬───────┘
          │                  │
          │                  ▼
          │         ┌────────────────┐
          │         │Initialize      │
          │         │Session         │
          │         └────────┬───────┘
          │                  │
          └──────────┬───────┘
                     │
                     ▼
┌─────────────────────────────┐
│  Process Interaction        │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Update Session Data        │
│  - Add conversation         │
│  - Update last active       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Generate & Store Embedding │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Update User Preferences    │
│  (if applicable)            │
└─────────────────────────────┘
```

## Security Architecture

### 1. Authentication & Authorization
- **User Authentication**: Integrated with application-level authentication
- **API Security**: Secured endpoints with proper authentication
- **AWS Credential Management**: Secure handling of AWS credentials

### 2. Data Security
- **Encryption**: Data encrypted at rest and in transit
- **PII Handling**: Minimization of personal identifiable information
- **Data Retention**: Clear policies on session data retention and purging

### 3. Input/Output Security
- **Input Validation**: Sanitization and validation of all user inputs
- **Output Filtering**: Post-processing to prevent sensitive information disclosure
- **Prompt Injection Prevention**: Guards against prompt manipulation attempts

## Monitoring & Observability

### 1. Performance Monitoring
- **Response Times**: Tracking of query processing times
- **Resource Utilization**: Monitoring of CPU, memory, and storage
- **Model Performance**: Tracking inference times and quality metrics

### 2. Quality Monitoring
- **Response Relevance**: Measuring response appropriateness
- **Guardrail Effectiveness**: Tracking guardrail triggers and interventions
- **User Satisfaction**: Collecting and analyzing feedback

### 3. Error Handling
- **Error Logging**: Comprehensive error capture and categorization
- **Graceful Degradation**: Fallback strategies for component failures
- **Alerting**: Notification system for critical errors

## Scalability Considerations

### 1. Horizontal Scaling
- MongoDB sharding capabilities for growing data
- Load balancing for multiple Ollama instances
- Distributed processing for high-concurrency scenarios

### 2. Performance Optimization
- Caching frequently accessed data
- Optimizing embedding generation and storage
- Query optimization for vector search

### 3. Resource Management
- Efficient model loading and unloading
- Memory management for embedding operations
- Connection pooling for database operations

## Architecture Constraints & Limitations

### 1. Technical Constraints
- Local Ollama models limited by available hardware resources
- Vector search performance dependent on MongoDB capabilities
- AWS Bedrock rate limits and quotas

### 2. Known Limitations
- Cold start latency for infrequently used models
- Context window limitations of underlying LLMs
- Vector search recall vs. precision tradeoffs

### 3. Future Considerations
- Support for multi-modal interactions
- Integration with additional external knowledge sources
- Advanced personalization based on user behavior analytics