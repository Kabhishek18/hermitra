"""
Core functionality for the ASHA career guidance chatbot.
This module contains the core classes and functions that power the ASHA application.
"""

import hashlib
import re
import hmac
import os
from datetime import datetime, timedelta
import base64
import io
import time
import cv2
import numpy as np
import json
import pandas as pd
import faiss
import requests
import uuid
import sys
from typing import Dict, List, Tuple, Optional, Any, Union
# Correct import for MongoDB's ObjectId
from bson.objectid import ObjectId
import pymongo
from pymongo import MongoClient
from PIL import Image

# Import torch safely using lazy loading to prevent Streamlit conflicts
# This is a simplified version - in production we would use the torch_isolation module
def safe_import(module_name):
    """Safely import a module that might conflict with Streamlit"""
    try:
        return __import__(module_name)
    except Exception as e:
        print(f"Warning: Could not import {module_name}: {e}")
        return None

# Check and import AI-related libraries
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS as LangchainFAISS
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain components not installed. ChatBot functionality will be limited.")

# AI gender detection imports
try:
    # We defer loading DeepFace until needed to avoid Streamlit conflicts
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("Warning: DeepFace not installed. Gender detection will be simulated.")

# MongoDB connection setup
def get_database_connection():
    """
    Connect to MongoDB and return database object
    
    Returns:
        pymongo.database.Database or None: MongoDB database object or None if connection fails
    """
    try:
        # Replace with your actual MongoDB connection string
        conn_str = "mongodb://localhost:27017/"
        client = pymongo.MongoClient(conn_str)
        db = client["asha_db"]
        # Test the connection by running a simple command
        client.admin.command('ping')
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

# Email validation
def is_valid_email(email: str) -> bool:
    """
    Validate email format
    
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

# AI-based gender detection
def detect_gender_from_image(image_file) -> Tuple[str, float]:
    """
    Detect gender from an image using DeepFace or simulation
    
    Args:
        image_file: Image file to analyze
        
    Returns:
        tuple: (detected_gender, confidence)
    """
    if not DEEPFACE_AVAILABLE:
        # Simulate gender detection for demonstration
        import random
        time.sleep(1)  # Simulate processing time
        genders = ["Woman", "Man"]
        weights = [0.6, 0.4]  # Slightly biased for demonstration
        detected_gender = random.choices(genders, weights=weights)[0]
        confidence = round(random.uniform(0.7, 0.98), 2)
        return detected_gender, confidence
    
    try:
        # Only import DeepFace when actually needed
        # This prevents Streamlit from monitoring it during startup
        from deepface import DeepFace
        
        # Convert uploaded file to image for processing
        image_bytes = image_file.getvalue()
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
        
        return detected_gender, confidence
    except Exception as e:
        print(f"Error detecting gender: {e}")
        return "Unknown", 0.0

# Ollama API integration for the ASHA model
class AshaBot:
    """ASHA career guidance chatbot using Ollama API or fallback simulation"""
    
    def __init__(self, model_name="mistral:latest"):
        """
        Initialize the ASHA chatbot
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/chat"
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
            
            # Create the payload
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": adjusted_prompt},
                    *self.session_context
                ],
                "stream": False
            }
            
            # For local testing when Ollama is not available
            if not self._is_ollama_available():
                return self._simulate_response(user_input, user_gender)
            
            # Send request to Ollama API
            response = requests.post(self.ollama_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get("message", {}).get("content", "")
                
                # Add assistant message to context
                self.session_context.append({"role": "assistant", "content": assistant_message})
                
                # Keep context manageable
                if len(self.session_context) > 10:
                    # Remove oldest message pair (user + assistant)
                    self.session_context = self.session_context[2:]
                
                return assistant_message
            else:
                return f"Error: {response.status_code}, {response.text}"
        
        except Exception as e:
            return f"Error communicating with the AI model: {str(e)}"
    
    def _is_ollama_available(self) -> bool:
        """
        Check if Ollama API is available
        
        Returns:
            bool: True if available, False otherwise
        """
        try:
            response = requests.get("http://localhost:11434/api/tags")
            return response.status_code == 200
        except:
            return False
    
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

# Session recommendation system
class SessionRecommender:
    """Recommends relevant professional development sessions based on user queries"""
    
    def __init__(self, db):
        """
        Initialize the session recommender
        
        Args:
            db: MongoDB database connection
        """
        self.db = db
        self.embeddings = None
        self.session_embeddings = None
        self.session_data = None
        self.initialize_embeddings()
        
    def initialize_embeddings(self):
        """Initialize the embedding model and session embeddings"""
        try:
            if LANGCHAIN_AVAILABLE:
                # Initialize the embedding model
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'}
                )
                
                # Load sessions from database
                sessions = list(self.db.sessions.find({}))
                self.session_data = sessions
                
                if sessions:
                    # Create texts to embed
                    texts = []
                    for session in sessions:
                        # Combine title, description and tags for better semantic matching
                        text = f"{session['session_title']} {session['description']} {' '.join(session.get('tags', []))}"
                        texts.append(text)
                    
                    # Create embeddings
                    session_embeddings = self.embeddings.embed_documents(texts)
                    
                    # Create FAISS index
                    dimension = len(session_embeddings[0])
                    index = faiss.IndexFlatL2(dimension)
                    index.add(np.array(session_embeddings).astype('float32'))
                    
                    self.session_embeddings = index
                    
                    print(f"Initialized embeddings for {len(sessions)} sessions")
        except Exception as e:
            print(f"Error initializing embeddings: {e}")
            # Fallback to simple keyword matching if embeddings fail
            self.embeddings = None
            self.session_embeddings = None
    
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
        try:
            if not self.session_data:
                return []
                
            if self.embeddings and self.session_embeddings:
                # Get query embedding
                query_embedding = self.embeddings.embed_query(query)
                
                # Search for similar sessions
                D, I = self.session_embeddings.search(
                    np.array([query_embedding]).astype('float32'), 
                    top_n
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
                        
                        # Store recommendation in database
                        self._store_recommendation(user_id, session["session_id"], relevance)
                
                return recommendations
            else:
                # Fallback: simple keyword matching
                return self._keyword_based_recommendations(query, user_id, top_n)
        except Exception as e:
            print(f"Error recommending sessions: {e}")
            return []
    
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
        query_words = set(query.lower().split())
        
        scored_sessions = []
        for session in self.session_data:
            score = 0
            title_words = set(session['session_title'].lower().split())
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
                    "relevance_score": score / 10.0  # Normalize to 0-1 range
                })
        
        # Sort by score
        scored_sessions.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Store recommendations
        for rec in scored_sessions[:top_n]:
            self._store_recommendation(
                user_id, 
                rec["session"]["session_id"], 
                rec["relevance_score"]
            )
        
        return scored_sessions[:top_n]
    
    def _store_recommendation(self, user_id: str, session_id: str, relevance_score: float):
        """
        Store recommendation in database
        
        Args:
            user_id: User ID
            session_id: Session ID
            relevance_score: Relevance score (0-1)
        """
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

# Database operations
def save_chat_history(db, user_id: str, messages: List[Dict]):
    """
    Save chat history to the database
    
    Args:
        db: MongoDB database connection
        user_id: User ID
        messages: List of chat messages
    """
    try:
        if db is None:
            return
            
        # Check if a conversation already exists for today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        conversation = db.conversations.find_one({
            "user_id": user_id,
            "created_at": {"$gte": today}
        })
        
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
    Check if MongoDB is running
    
    Returns:
        bool: True if running, False otherwise
    """
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return True
    except Exception:
        return False