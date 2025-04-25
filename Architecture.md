# ASHA Chatbot: Technical Implementation Guide

This document provides the technical specifications and implementation details for developing the ASHA chatbot on macOS using your existing installations of Ollama, Python (conda), and MongoDB.

## System Architecture

```
                  ┌─────────────────┐
                  │                 │
                  │  Streamlit UI   │
                  │                 │
                  └────────┬────────┘
                           │
                           ▼
┌──────────────────────────────────────────────┐
│                                              │
│           Application Core                   │
│                                              │
│  ┌─────────────┐        ┌────────────────┐   │
│  │             │        │                │   │
│  │  Career     │◄──────►│  Session       │   │
│  │  Guidance   │        │  Recommender   │   │
│  │  Engine     │        │                │   │
│  │             │        │                │   │
│  └──────┬──────┘        └────────┬───────┘   │
│         │                        │           │
└─────────┼────────────────────────┼───────────┘
          │                        │
          ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│  Ollama LLM     │      │  MongoDB        │
│  (Mistral)      │      │  Database       │
│                 │      │                 │
└─────────────────┘      └─────────────────┘
          │                        │
          ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │
│  FAISS Vector   │      │  Knowledge Base │
│  Database       │      │  & Sessions     │
│                 │      │                 │
└─────────────────┘      └─────────────────┘
```

## Project Setup

### 1. Create a Conda Environment

```bash
# Create a new conda environment
conda create -n asha_env python=3.10
conda activate asha_env

# Install required packages
pip install streamlit langchain faiss-cpu pymongo pandas sentence-transformers
```

### 2. Project Directory Structure

```
asha/
├── app.py                     # Main Streamlit application
├── config.py                  # Configuration settings
├── assets/                    # Images and static files
├── components/                # UI components
│   ├── __init__.py
│   ├── chat_interface.py
│   └── session_browser.py
├── engines/                   # Core functionality
│   ├── __init__.py
│   ├── career_guidance.py     # Career guidance logic
│   └── session_recommender.py # Session recommendation system
├── data/
│   ├── sessions.json          # Imported session data
│   └── knowledge/             # Career guidance documents
│       ├── leadership/
│       ├── interviews/
│       └── career_paths/
├── utils/
│   ├── __init__.py
│   ├── db.py                  # MongoDB utilities
│   ├── vector_store.py        # FAISS utilities
│   └── ollama.py              # Ollama API utilities
└── README.md
```

## Core Implementation Components

### 1. Career Guidance Engine

The career guidance engine handles user queries related to professional development, using the Mistral model via Ollama.

```python
# engines/career_guidance.py
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
import os

class CareerGuidanceEngine:
    def __init__(self):
        # Initialize Ollama with the Mistral model
        self.llm = Ollama(model="mistral:latest")
        
        # Set up conversation memory
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # Define the system prompt with guidance guardrails
        self.system_prompt = """
        You are ASHA, a career guidance assistant specialized in helping women professionals.
        Your responses should:
        - Focus exclusively on career-related topics
        - Avoid gender stereotypes and biases
        - Provide practical, actionable advice
        - Reference best practices in professional development
        - Acknowledge when a question is outside your expertise
        
        When unsure, ask clarifying questions rather than making assumptions.
        """
        
        # Create the prompt template
        self.template = f"""
        {self.system_prompt}
        
        Conversation History:
        {{history}}
        
        Human: {{question}}
        ASHA:
        """
        
        self.prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=self.template
        )
        
        # Create the chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            memory=self.memory,
            verbose=True
        )
    
    def process_query(self, query):
        """Process a user query and return a response."""
        try:
            response = self.chain.run(question=query)
            return response
        except Exception as e:
            print(f"Error processing query: {e}")
            return "I'm having trouble processing your request. Could you please try again?"
```

### 2. Session Recommendation Engine

The session recommendation engine analyzes user queries and history to suggest relevant professional development sessions.

```python
# engines/session_recommender.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from utils.db import get_all_sessions

class SessionRecommender:
    def __init__(self):
        # Load sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize FAISS index
        self.sessions = get_all_sessions()
        self.index = None
        self.session_ids = []
        
        # Build index if sessions exist
        if self.sessions:
            self._build_index()
    
    def _build_index(self):
        """Build FAISS index from sessions data"""
        texts = []
        self.session_ids = []
        
        for session in self.sessions:
            # Extract relevant text from session
            session_text = f"{session['session_title']} {session.get('description', '')}"
            texts.append(session_text)
            self.session_ids.append(session['session_id'])
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
    
    def recommend_sessions(self, query, top_k=3):
        """Recommend sessions based on a query"""
        if not self.index:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Search for similar sessions
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            k=top_k
        )
        
        # Get recommended sessions
        recommendations = []
        for i in indices[0]:
            if i < len(self.session_ids):
                session_id = self.session_ids[i]
                for session in self.sessions:
                    if session['session_id'] == session_id:
                        recommendations.append(session)
                        break
        
        return recommendations
```

### 3. MongoDB Integration

```python
# utils/db.py
from pymongo import MongoClient
import json
import os

class DatabaseManager:
    def __init__(self):
        # Connect to MongoDB
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['asha_db']
        
        # Initialize collections
        self.sessions_collection = self.db['sessions']
        self.user_history_collection = self.db['user_history']
        
        # Import sessions if collection is empty
        if self.sessions_collection.count_documents({}) == 0:
            self._import_sessions()
    
    def _import_sessions(self):
        """Import sessions from JSON file if available"""
        sessions_file = os.path.join('data', 'sessions.json')
        if os.path.exists(sessions_file):
            try:
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                    
                if isinstance(sessions_data, list):
                    self.sessions_collection.insert_many(sessions_data)
                else:
                    self.sessions_collection.insert_one(sessions_data)
                print(f"Imported {self.sessions_collection.count_documents({})} sessions")
            except Exception as e:
                print(f"Error importing sessions: {e}")
    
    def get_all_sessions(self):
        """Retrieve all sessions"""
        return list(self.sessions_collection.find({}, {'_id': 0}))
    
    def get_session_by_id(self, session_id):
        """Retrieve a specific session by ID"""
        return self.sessions_collection.find_one({'session_id': session_id}, {'_id': 0})
    
    def save_chat_history(self, user_id, conversation):
        """Save user chat history"""
        self.user_history_collection.update_one(
            {'user_id': user_id},
            {'$push': {'conversations': conversation}},
            upsert=True
        )
    
    def get_user_history(self, user_id):
        """Retrieve user chat history"""
        user_record = self.user_history_collection.find_one({'user_id': user_id})
        return user_record.get('conversations', []) if user_record else []

# Initialize a global instance
db_manager = DatabaseManager()

# Convenience functions
def get_all_sessions():
    return db_manager.get_all_sessions()

def get_session_by_id(session_id):
    return db_manager.get_session_by_id(session_id)

def save_chat_history(user_id, conversation):
    return db_manager.save_chat_history(user_id, conversation)

def get_user_history(user_id):
    return db_manager.get_user_history(user_id)
```

### 4. Streamlit User Interface

```python
# app.py
import streamlit as st
from engines.career_guidance import CareerGuidanceEngine
from engines.session_recommender import SessionRecommender
from utils.db import save_chat_history, get_user_history

def main():
    st.set_page_config(
        page_title="ASHA - Career Guidance Assistant",
        page_icon="👩‍💼",
        layout="wide"
    )
    
    # Initialize session state
    if 'career_engine' not in st.session_state:
        st.session_state.career_engine = CareerGuidanceEngine()
    
    if 'session_recommender' not in st.session_state:
        st.session_state.session_recommender = SessionRecommender()
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "demo_user"  # In production, use actual user authentication
    
    # App title and description
    st.title("ASHA: Career Guidance Assistant")
    st.markdown("""
    Welcome to ASHA, your personal career guidance assistant specialized in helping women professionals.
    Ask questions about career development, job search, interviews, leadership, and more!
    """)
    
    # Create columns for chat and recommendations
    col1, col2 = st.columns([3, 1])
    
    # Chat interface
    with col1:
        st.subheader("Career Guidance Chat")
        
        # Display chat history
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                st.markdown(f"**You**: {message['content']}")
            else:
                st.markdown(f"**ASHA**: {message['content']}")
        
        # Chat input
        user_query = st.text_input("Ask ASHA about your career...", key="user_input")
        
        if user_query:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_query
            })
            
            # Generate response
            response = st.session_state.career_engine.process_query(user_query)
            
            # Add assistant message to history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Save chat history to database
            save_chat_history(st.session_state.user_id, {
                'query': user_query,
                'response': response,
                'timestamp': datetime.now()
            })
            
            # Rerun to update UI
            st.experimental_rerun()
    
    # Session recommendations
    with col2:
        st.subheader("Recommended Sessions")
        
        if user_query:
            recommendations = st.session_state.session_recommender.recommend_sessions(user_query)
            
            if recommendations:
                for session in recommendations:
                    st.markdown(f"### {session['session_title']}")
                    st.markdown(f"**Host**: {session['host_user'][0]['username']}")
                    st.markdown(f"**Duration**: {session.get('duration', 'N/A')}")
                    
                    if 'external_url' in session and session['external_url']:
                        st.markdown(f"[Join Session]({session['external_url']})")
                    
                    st.markdown("---")
            else:
                st.info("No relevant sessions found. Try a different query!")

if __name__ == "__main__":
    main()
```

## Knowledge Base Setup

Create a structured knowledge base of career guidance content in the `data/knowledge` directory:

1. **Leadership for Women**
   - Documents on overcoming gender bias
   - Strategies for women in leadership
   - Negotiation techniques

2. **Interview Preparation**
   - Common interview questions
   - Industry-specific interview guides
   - Confidence-building techniques

3. **Career Paths**
   - Industry transition guides
   - Skills development roadmaps
   - Remote work strategies

## Session Data Integration

The session data from your provided sample will be stored in MongoDB. The system will process this structured data to:

1. Extract key topics and themes
2. Create vector embeddings for semantic search
3. Enable contextual recommendations based on conversation

## Implementation Steps

1. **Environment Setup**
   - Verify Ollama is properly configured with Mistral model
   - Create conda environment and install dependencies
   - Configure MongoDB for session storage

2. **Data Preparation**
   - Import session data into MongoDB
   - Create career guidance knowledge base
   - Build vector index for efficient retrieval

3. **Core Engine Development**
   - Implement career guidance engine with Ollama integration
   - Build session recommendation engine
   - Connect databases and vector stores

4. **User Interface**
   - Develop Streamlit interface with chat functionality
   - Create session recommendation display
   - Implement user history tracking

5. **Testing & Refinement**
   - Test with sample queries
   - Verify session recommendations
   - Optimize response quality and speed

## Deployment & Usage

1. Start MongoDB:
   ```bash
   brew services start mongodb-community
   ```

2. Start Ollama:
   ```bash
   ollama serve
   ```

3. Launch the ASHA application:
   ```bash
   conda activate asha_env
   streamlit run app.py
   ```

4. Access the interface at `http://localhost:8501` in your browser

## Advanced Features (Future Enhancements)

1. **User Profiles**
   - Career goals tracking
   - Skills assessment
   - Personalized learning paths

2. **Analytics Dashboard**
   - Most common career questions
   - Session engagement metrics
   - User progress tracking

3. **Multi-modal Support**
   - Resume review with document analysis
   - Video interview preparation
   - Voice interaction

4. **Integration Options**
   - Calendar scheduling for sessions
   - Learning management systems
   - Professional networking platforms