"""
Core functionality for the ASHA career guidance chatbot.
This module contains the core classes and functions that power the ASHA application.
Optimized for better performance and resource usage.
"""

import hashlib
import re
import hmac
import os
from datetime import datetime, timedelta
import base64
import io
import time
import json
import pandas as pd
import numpy as np
import faiss
import requests
import uuid
import sys
from typing import Dict, List, Tuple, Optional, Any, Union
from functools import lru_cache
from threading import Lock
import pickle
# Correct import for MongoDB's ObjectId
from bson.objectid import ObjectId
import pymongo
from pymongo import MongoClient
from PIL import Image

# Global connection pool for MongoDB
_DB_CONNECTION = None
_DB_CONNECTION_LOCK = Lock()

# Cache for embeddings and models
_MODEL_CACHE = {}
_MODEL_CACHE_LOCK = Lock()

# Safe lazy imports for AI libraries
def safe_import(module_name):
    """Safely import a module that might conflict with Streamlit"""
    try:
        return __import__(module_name)
    except Exception as e:
        print(f"Warning: Could not import {module_name}: {e}")
        return None

# Check and import AI-related libraries only when needed
LANGCHAIN_IMPORTED = False
LANGCHAIN_AVAILABLE = False
def import_langchain():
    """Import LangChain only when needed"""
    global LANGCHAIN_IMPORTED, LANGCHAIN_AVAILABLE
    
    if not LANGCHAIN_IMPORTED:
        try:
            global HuggingFaceEmbeddings, LangchainFAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS as LangchainFAISS
            LANGCHAIN_AVAILABLE = True
        except ImportError:
            LANGCHAIN_AVAILABLE = False
            print("Warning: LangChain components not installed. ChatBot functionality will be limited.")
        LANGCHAIN_IMPORTED = True
    
    return LANGCHAIN_AVAILABLE

# AI gender detection imports - lazy loaded
DEEPFACE_IMPORTED = False
DEEPFACE_AVAILABLE = False
def import_deepface():
    """Import DeepFace only when needed"""
    global DEEPFACE_IMPORTED, DEEPFACE_AVAILABLE
    
    if not DEEPFACE_IMPORTED:
        try:
            global DeepFace
            from deepface import DeepFace
            DEEPFACE_AVAILABLE = True
        except ImportError:
            DEEPFACE_AVAILABLE = False
            print("Warning: DeepFace not installed. Gender detection will be simulated.")
        DEEPFACE_IMPORTED = True
    
    return DEEPFACE_AVAILABLE

# MongoDB connection setup with connection pooling
def get_database_connection():
    """
    Connect to MongoDB with connection pooling and return database object
    
    Returns:
        pymongo.database.Database or None: MongoDB database object or None if connection fails
    """
    global _DB_CONNECTION
    
    # Return existing connection if available
    if _DB_CONNECTION is not None:
        return _DB_CONNECTION
    
    # Use lock to prevent multiple concurrent initializations
    with _DB_CONNECTION_LOCK:
        # Check again after acquiring lock
        if _DB_CONNECTION is not None:
            return _DB_CONNECTION
            
        try:
            # Replace with your actual MongoDB connection string
            conn_str = "mongodb://localhost:27017/"
            client = pymongo.MongoClient(
                conn_str, 
                maxPoolSize=10,  # Connection pool size
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                serverSelectionTimeoutMS=10000
            )
            db = client["asha_db"]
            # Test the connection
            client.admin.command('ping')
            
            # Store the connection globally
            _DB_CONNECTION = db
            return db
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

# Password hashing and verification
def hash_password(password: str, salt=None) -> bytes:
    """
    Hash a password with a salt using PBKDF2
    
    Args:
        password: The password to hash
        salt: Optional salt, will be generated if not provided
        
    Returns:
        bytes: Concatenated salt and key
    """
    if salt is None:
        salt = os.urandom(32)  # Generate a random salt
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000  # Number of iterations
    )
    
    return salt + key

def verify_password(stored_password: bytes, provided_password: str) -> bool:
    """
    Verify a password against a stored hash
    
    Args:
        stored_password: The stored password hash (salt + key)
        provided_password: The password to verify
        
    Returns:
        bool: True if password matches, False otherwise
    """
    salt = stored_password[:32]  # First 32 bytes are the salt
    stored_key = stored_password[32:]
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        provided_password.encode('utf-8'),
        salt,
        100000  # Same number of iterations as in hash_password
    )
    
    return hmac.compare_digest(stored_key, key)

# Email validation with caching for repeated checks
@lru_cache(maxsize=128)
def is_valid_email(email: str) -> bool:
    """
    Validate email format with caching
    
    Args:
        email: Email to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# Session token management
def generate_session_token(user_id: str) -> str:
    """
    Generate a session token for a user
    
    Args:
        user_id: User ID to include in token
        
    Returns:
        str: Base64 encoded token with expiry
    """
    expiry = datetime.now() + timedelta(hours=24)
    token_data = f"{user_id}:{expiry.timestamp()}"
    return base64.b64encode(token_data.encode()).decode()

def decode_session_token(token: str) -> Optional[str]:
    """
    Decode a session token and verify it's not expired
    
    Args:
        token: The session token to decode
        
    Returns:
        str or None: User ID if token is valid and not expired, None otherwise
    """
    try:
        token_data = base64.b64decode(token).decode()
        user_id, expiry = token_data.split(':')
        expiry_dt = datetime.fromtimestamp(float(expiry))
        if datetime.now() > expiry_dt:
            return None  # Token expired
        return user_id
    except:
        return None

# AI-based gender detection with caching
def detect_gender_from_image(image_file) -> Tuple[str, float]:
    """
    Detect gender from an image using DeepFace or simulation
    
    Args:
        image_file: Image file to analyze
        
    Returns:
        tuple: (detected_gender, confidence)
    """
    # Create a hash of the image for caching
    image_bytes = image_file.getvalue()
    image_hash = hashlib.md5(image_bytes).hexdigest()
    
    # Check if we have a cached result
    cache_key = f"gender_detection_{image_hash}"
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    
    # If DeepFace is not available, use simulation
    if not import_deepface():
        # Simulate gender detection for demonstration
        import random
        time.sleep(0.5)  # Reduced simulation time
        genders = ["Woman", "Man"]
        weights = [0.6, 0.4]  # Slightly biased for demonstration
        detected_gender = random.choices(genders, weights=weights)[0]
        confidence = round(random.uniform(0.7, 0.98), 2)
        result = (detected_gender, confidence)
        
        # Cache the result
        with _MODEL_CACHE_LOCK:
            _MODEL_CACHE[cache_key] = result
        
        return result
    
    try:
        # Process the image
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Using DeepFace for gender analysis
        analysis = DeepFace.analyze(image_np, actions=['gender'], enforce_detection=False)
        
        # Map DeepFace gender to our terminology
        gender_map = {
            "Woman": "Woman",
            "Female": "Woman",
            "Man": "Man", 
            "Male": "Man"
        }
        
        detected_gender = gender_map.get(analysis[0]["dominant_gender"], "Unknown")
        confidence = analysis[0]["gender"].get(analysis[0]["dominant_gender"], 0) / 100
        
        result = (detected_gender, confidence)
        
        # Cache the result
        with _MODEL_CACHE_LOCK:
            _MODEL_CACHE[cache_key] = result
        
        return result
    except Exception as e:
        print(f"Error detecting gender: {e}")
        return "Unknown", 0.0

# Ollama API integration for the ASHA model
class AshaBot:
    """ASHA career guidance chatbot using Ollama API or fallback simulation"""
    
    def __init__(self, model_name="mistral:latest", context_window_size=5):
        """
        Initialize the ASHA chatbot
        
        Args:
            model_name: Name of the Ollama model to use
            context_window_size: Number of previous messages to keep in context
        """
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/chat"
        self.context_window_size = context_window_size
        self.system_prompt = """
        You are ASHA, an AI-powered career guidance chatbot specifically designed for women professionals.
        Your purpose is to provide personalized career advice that considers gender-specific workplace dynamics,
        connect users to relevant professional development sessions, and serve as an always-available mentor
        that understands career progression challenges for women.
        
        Key areas of guidance include:
        1. Resume review and optimization recommendations
        2. Interview preparation and confidence-building techniques
        3. Salary negotiation strategies specifically for women
        4. Career transition pathways with skills gap analysis
        5. Leadership development advice for women professionals
        
        Your responses should be supportive, empowering, and practical. Avoid reinforcing gender stereotypes
        while acknowledging the unique challenges women face in professional environments.
        
        When appropriate, suggest relevant professional development sessions from the database that align
        with the user's career goals or current challenges.
        """
        self.session_context = []
        
        # Check Ollama availability at initialization to avoid repeated checks
        self._ollama_available = self._check_ollama_availability()
        
    def _check_ollama_availability(self) -> bool:
        """
        Check if Ollama API is available
        
        Returns:
            bool: True if available, False otherwise
        """
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
        
    def chat(self, user_input: str, user_gender="Woman") -> str:
        """
        Send a chat message to the Ollama API and get a response
        
        Args:
            user_input: User's message
            user_gender: User's gender for context-aware responses
            
        Returns:
            str: Chatbot response
        """
        try:
            # Adjust system prompt based on user gender
            adjusted_prompt = self.system_prompt
            if user_gender != "Woman":
                adjusted_prompt = """
                You are ASHA, an AI-powered career guidance chatbot primarily designed for women professionals,
                but also providing general career advice to all users. While you're optimized for women's 
                career challenges, you aim to provide valuable guidance to everyone.
                
                Please provide general career advice focusing on:
                1. Resume review and optimization recommendations
                2. Interview preparation techniques
                3. Salary negotiation strategies
                4. Career transition pathways
                5. Leadership development advice
                
                Your responses should be supportive, empowering, and practical.
                """
            
            # Add user message to context
            self.session_context.append({"role": "user", "content": user_input})
            
            # Limit context to window size (keep most recent messages)
            if len(self.session_context) > self.context_window_size * 2:  # *2 because each exchange is user+assistant
                self.session_context = self.session_context[-self.context_window_size*2:]
            
            # For local testing when Ollama is not available
            if not self._ollama_available:
                response = self._simulate_response(user_input, user_gender)
                # Add assistant message to context
                self.session_context.append({"role": "assistant", "content": response})
                return response
            
            # Create the payload
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": adjusted_prompt},
                    *self.session_context
                ],
                "stream": False
            }
            
            # Send request to Ollama API with timeout
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("message", {}).get("content", "")
                
                # Add assistant message to context
                self.session_context.append({"role": "assistant", "content": assistant_message})
                
                return assistant_message
            else:
                # Fall back to simulation if Ollama fails
                print(f"Ollama API error: {response.status_code}, {response.text}")
                response = self._simulate_response(user_input, user_gender)
                self.session_context.append({"role": "assistant", "content": response})
                return response
        
        except Exception as e:
            print(f"Error communicating with the AI model: {str(e)}")
            # Fall back to simulation on exception
            response = self._simulate_response(user_input, user_gender)
            self.session_context.append({"role": "assistant", "content": response})
            return response
    
    def _simulate_response(self, user_input: str, user_gender: str) -> str:
        """
        Simulate response when Ollama is not available
        
        Args:
            user_input: User's message
            user_gender: User's gender
            
        Returns:
            str: Simulated response
        """
        # Simple template-based responses for demonstration
        career_keywords = {
            "resume": "Your resume is an important professional document. I recommend highlighting your achievements with quantifiable results.",
            "interview": "Prepare for interviews by researching the company, practicing common questions, and preparing your own questions.",
            "salary": "When negotiating salary, research market rates for your position and experience level. Be confident in your value.",
            "leadership": "Leadership skills can be developed through practice. Seek opportunities to lead projects or mentor junior colleagues.",
            "transition": "Career transitions require identifying transferable skills and gaining new ones through training or education.",
            "networking": "Building a professional network is crucial. Consider joining industry groups or attending virtual events.",
            "work-life balance": "Setting boundaries is essential for work-life balance. Prioritize tasks and communicate your availability clearly."
        }
        
        # Women-specific advice for women users
        women_specific = {
            "salary": " Women often undervalue their work. Practice negotiation with a trusted friend and focus on your achievements.",
            "leadership": " Women in leadership positions may face unique challenges. Find mentors and allies who support your growth.",
            "networking": " Consider joining women-focused professional networks for additional support and opportunities."
        }
        
        # Check for keyword matches
        response = "I'm here to help with your career questions. Could you share more about what specific area you'd like guidance on?"
        
        for keyword, advice in career_keywords.items():
            if keyword in user_input.lower():
                response = advice
                # Add women-specific advice if applicable
                if user_gender == "Woman" and keyword in women_specific:
                    response += women_specific[keyword]
                break
        
        # Add session recommendation suggestion
        response += "\n\nI can also recommend professional development sessions that might help with this topic. Would you like to see some relevant sessions?"
        
        return response

# Session recommendation system with optimized FAISS index
class SessionRecommender:
    """Recommends relevant professional development sessions based on user queries"""
    
    def __init__(self, db, faiss_index_path="data/session_faiss_index.pkl"):
        """
        Initialize the session recommender
        
        Args:
            db: MongoDB database connection
            faiss_index_path: Path to save/load FAISS index
        """
        self.db = db
        self.embeddings = None
        self.session_embeddings = None
        self.session_data = None
        self.faiss_index_path = faiss_index_path
        self.last_index_update = None
        self.index_update_interval = timedelta(hours=24)  # Update index every 24 hours
        
        # Initialize embeddings (will be loaded on demand)
        self._load_or_build_index()
        
    def _load_or_build_index(self, force_rebuild=False):
        """Load existing FAISS index or build a new one"""
        # Import LangChain only when needed
        if not import_langchain():
            return
            
        try:
            # Check if index exists and is recent
            rebuild_needed = force_rebuild
            
            if os.path.exists(self.faiss_index_path) and not force_rebuild:
                # Check modification time
                index_mtime = datetime.fromtimestamp(os.path.getmtime(self.faiss_index_path))
                if datetime.now() - index_mtime < self.index_update_interval:
                    try:
                        # Load existing index
                        with open(self.faiss_index_path, 'rb') as f:
                            saved_data = pickle.load(f)
                            self.session_embeddings = saved_data['index']
                            self.session_data = saved_data['sessions']
                            print(f"Loaded FAISS index with {len(self.session_data)} sessions")
                            return
                    except Exception as e:
                        print(f"Error loading FAISS index: {e}")
                        rebuild_needed = True
                else:
                    # Index is too old
                    rebuild_needed = True
            else:
                # Index doesn't exist
                rebuild_needed = True
            
            if rebuild_needed:
                # Initialize embeddings model
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'}
                )
                
                # Build new index
                self._build_session_index()
                
                # Save index
                if self.session_embeddings is not None and self.session_data is not None:
                    os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)
                    with open(self.faiss_index_path, 'wb') as f:
                        pickle.dump({
                            'index': self.session_embeddings,
                            'sessions': self.session_data
                        }, f)
                    print(f"Saved FAISS index with {len(self.session_data)} sessions")
                
                self.last_index_update = datetime.now()
        except Exception as e:
            print(f"Error in load_or_build_index: {e}")
                
    def _build_session_index(self):
        """Build FAISS index for sessions"""
        try:
            # Ensure we have the database connection
            if self.db is None:
                print("Cannot build session index: No database connection")
                return
                
            # Fetch sessions in batches to reduce memory usage
            batch_size = 100
            session_count = self.db.sessions.count_documents({})
            sessions = []
            
            for skip in range(0, session_count, batch_size):
                batch = list(self.db.sessions.find({}).skip(skip).limit(batch_size))
                sessions.extend(batch)
            
            self.session_data = sessions
            
            if not sessions:
                print("No sessions found in database")
                return
                
            # Create texts to embed
            texts = []
            for session in sessions:
                # Combine title, description and tags for better semantic matching
                title = session.get('session_title', '')
                description = session.get('description', '')
                tags = ' '.join(session.get('tags', []))
                text = f"{title} {description} {tags}"
                texts.append(text)
            
            # Create embeddings
            session_embeddings = self.embeddings.embed_documents(texts)
            
            # Create FAISS index
            dimension = len(session_embeddings[0])
            index = faiss.IndexFlatL2(dimension)
            index.add(np.array(session_embeddings).astype('float32'))
            
            self.session_embeddings = index
            
            print(f"Built embeddings for {len(sessions)} sessions")
        except Exception as e:
            print(f"Error building session index: {e}")
    
    def recommend_sessions(self, query: str, user_id: str, top_n: int = 3) -> List[Dict]:
        """
        Recommend sessions based on user query
        
        Args:
            query: User's query text
            user_id: User's ID for storing recommendations
            top_n: Number of recommendations to return
            
        Returns:
            list: List of recommended sessions with relevance scores
        """
        # Check if we need to update the index
        if (self.last_index_update is None or 
            datetime.now() - self.last_index_update > self.index_update_interval):
            self._load_or_build_index()
        
        try:
            # Check if we have session data
            if not self.session_data:
                return []
            
            # Ensure we have the embeddings and FAISS index
            if import_langchain() and self.embeddings and self.session_embeddings:
                # Get query embedding
                query_embedding = self.embeddings.embed_query(query)
                
                # Search for similar sessions
                D, I = self.session_embeddings.search(
                    np.array([query_embedding]).astype('float32'), 
                    min(top_n, len(self.session_data))
                )
                
                # Get recommended sessions
                recommendations = []
                for i in range(len(I[0])):
                    idx = I[0][i]
                    if idx < len(self.session_data):
                        session = self.session_data[idx]
                        
                        # Add relevance score (normalize distance)
                        relevance = 1.0 / (1.0 + D[0][i])
                        
                        # Add to recommendations
                        recommendations.append({
                            "session": session,
                            "relevance_score": relevance
                        })
                        
                        # Store recommendation in database (with error handling)
                        try:
                            if self.db is not None:
                                self._store_recommendation(user_id, session["session_id"], relevance)
                        except Exception as e:
                            print(f"Error storing recommendation: {e}")
                
                return recommendations
            else:
                # Fallback: simple keyword matching
                return self._keyword_based_recommendations(query, user_id, top_n)
        except Exception as e:
            print(f"Error recommending sessions: {e}")
            return self._keyword_based_recommendations(query, user_id, top_n)
    
    def _keyword_based_recommendations(self, query: str, user_id: str, top_n: int = 3) -> List[Dict]:
        """
        Simple keyword-based recommendation as fallback
        
        Args:
            query: User's query text
            user_id: User's ID
            top_n: Number of recommendations to return
            
        Returns:
            list: List of recommended sessions with relevance scores
        """
        if not self.session_data and self.db is not None:
            try:
                # Fetch sessions directly from database
                self.session_data = list(self.db.sessions.find({}))
            except Exception as e:
                print(f"Error fetching sessions: {e}")
                return []
        
        if not self.session_data:
            return []
            
        query_words = set(query.lower().split())
        
        scored_sessions = []
        for session in self.session_data:
            score = 0
            title_words = set(session.get('session_title', '').lower().split())
            desc_words = set(session.get('description', '').lower().split())
            tags = set([tag.lower() for tag in session.get('tags', [])])
            
            # Calculate overlap
            title_overlap = len(query_words.intersection(title_words))
            desc_overlap = len(query_words.intersection(desc_words))
            tag_overlap = len(query_words.intersection(tags))
            
            # Weighted score
            score = (title_overlap * 3) + (desc_overlap * 2) + (tag_overlap * 4)
            
            if score > 0:
                scored_sessions.append({
                    "session": session,
                    "relevance_score": min(score / 10.0, 1.0)  # Normalize to 0-1 range
                })
        
        # Sort by score
        scored_sessions.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Store recommendations
        if self.db is not None:
            for rec in scored_sessions[:top_n]:
                try:
                    self._store_recommendation(
                        user_id, 
                        rec["session"]["session_id"], 
                        rec["relevance_score"]
                    )
                except Exception as e:
                    print(f"Error storing recommendation: {e}")
        
        return scored_sessions[:top_n]
    
    def _store_recommendation(self, user_id: str, session_id: str, relevance_score: float):
        """
        Store recommendation in database with error handling
        
        Args:
            user_id: User ID
            session_id: Session ID
            relevance_score: Relevance score (0-1)
        """
        if self.db is None:
            return
            
        try:
            # Check if recommendation already exists
            existing = self.db.user_recommendations.find_one({
                "user_id": user_id,
                "session_id": session_id
            })
            
            if existing:
                # Update existing recommendation
                self.db.user_recommendations.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "relevance_score": relevance_score,
                        "recommended_at": datetime.now()
                    }}
                )
            else:
                # Create new recommendation
                self.db.user_recommendations.insert_one({
                    "user_id": user_id,
                    "session_id": session_id,
                    "relevance_score": relevance_score,
                    "recommended_at": datetime.now(),
                    "user_viewed": False,
                    "recommendation_reasons": ["Based on conversation"]
                })
        except Exception as e:
            print(f"Error storing recommendation: {e}")

# Database operations with better error handling
def save_chat_history(db, user_id: str, messages: List[Dict], max_messages: int = 100):
    """
    Save chat history to the database with pagination
    
    Args:
        db: MongoDB database connection
        user_id: User ID
        messages: List of chat messages
        max_messages: Maximum number of messages to store
    """
    if db is None:
        return
        
    try:
        # Check if a conversation already exists for today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        conversation = db.conversations.find_one({
            "user_id": user_id,
            "created_at": {"$gte": today}
        })
        
        # Limit the number of messages to prevent large documents
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        if conversation:
            # Update existing conversation
            db.conversations.update_one(
                {"_id": conversation["_id"]},
                {"$set": {
                    "messages": messages,
                    "last_updated": datetime.now()
                }}
            )
        else:
            # Create new conversation
            db.conversations.insert_one({
                "user_id": user_id,
                "messages": messages,
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            })
    except Exception as e:
        print(f"Error saving chat history: {e}")

def check_mongodb_running() -> bool:
    """
    Check if MongoDB is running with timeout
    
    Returns:
        bool: True if running, False otherwise
    """
    try:
        client = pymongo.MongoClient(
            "mongodb://localhost:27017/", 
            serverSelectionTimeoutMS=2000
        )
        client.admin.command('ping')
        return True
    except Exception:
        return False

# Cache management functions
def clear_model_cache():
    """Clear the model cache to free memory"""
    global _MODEL_CACHE
    with _MODEL_CACHE_LOCK:
        _MODEL_CACHE.clear()
    print("Model cache cleared")

def close_database_connection():
    """Close the database connection pool"""
    global _DB_CONNECTION
    if _DB_CONNECTION is not None:
        try:
            _DB_CONNECTION.client.close()
            _DB_CONNECTION = None
            print("Database connection closed")
        except Exception as e:
            print(f"Error closing database connection: {e}")

# Function to optimize memory usage
def optimize_memory():
    """Optimize memory usage by clearing caches if needed"""
    try:
        import psutil
        
        # Get current memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # If memory usage is high, clear caches
        if memory_percent > 70:  # If using more than 70% of available memory
            print(f"High memory usage detected: {memory_percent:.1f}%. Clearing caches...")
            clear_model_cache()
            
        return memory_info.rss / (1024 * 1024)  # Return memory usage in MB
    except ImportError:
        return None  # psutil not available
    except Exception as e:
        print(f"Error in optimize_memory: {e}")
        return None