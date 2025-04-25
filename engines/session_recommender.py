# asha/engines/session_recommender.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vector_store import vector_store
from utils.db import get_all_sessions
import config
import json
import re
from functools import lru_cache

class SessionRecommender:
    def __init__(self):
        # Get all sessions only once during initialization
        self.sessions = get_all_sessions()
        
        # Process session data for recommendation
        if self.sessions:
            self._preprocess_sessions()
            self._build_index()
    
    def _extract_description_text(self, description):
        """Extract plain text from structured description"""
        # If description is a string that looks like JSON, try to parse it
        if isinstance(description, str) and description.strip().startswith('{'):
            try:
                desc_obj = json.loads(description)
                # Try to extract text from Lexical JSON structure
                if 'root' in desc_obj and 'children' in desc_obj['root']:
                    text_parts = []
                    self._extract_text_from_lexical(desc_obj['root'], text_parts)
                    return ' '.join(text_parts)
            except:
                # If parsing fails, return the original string
                pass
        return str(description)
    
    def _extract_text_from_lexical(self, node, text_parts):
        """Recursively extract text from Lexical editor JSON structure"""
        if 'children' in node:
            for child in node['children']:
                if 'text' in child:
                    text_parts.append(child['text'])
                self._extract_text_from_lexical(child, text_parts)
    
    def _preprocess_sessions(self):
        """Preprocess session data to extract and clean text"""
        processed_sessions = []
        texts = []
        
        for session in self.sessions:
            # Clean and extract text from session data
            session_title = session.get('session_title', '')
            
            # Extract text from description
            description = session.get('description', '')
            description_text = self._extract_description_text(description)
            
            # Get host information
            host_info = ""
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_info = host_users[0].get('username', '')
            
            # Combine metadata into searchable text
            session_text = f"Title: {session_title} Description: {description_text} Host: {host_info}"
            
            # Clean the text (remove extra whitespace, etc.)
            session_text = re.sub(r'\s+', ' ', session_text).strip()
            
            # Add to processed data
            processed_sessions.append(session)
            texts.append(session_text)
        
        self.processed_sessions = processed_sessions
        self.session_texts = texts
    
    def _build_index(self):
        """Build vector index from processed sessions"""
        try:
            # Make sure we have data to index
            if not hasattr(self, 'session_texts') or not self.session_texts:
                print("No session texts available to build index")
                return
                
            if not hasattr(self, 'processed_sessions') or not self.processed_sessions:
                print("No processed sessions available to build index")
                return
                
            # Print some debugging info
            print(f"Building index with {len(self.session_texts)} session texts")
            
            # Create the index
            vector_store.create_index(self.session_texts, self.processed_sessions)
            print("Session index built successfully")
        except Exception as e:
            print(f"Error building session index: {e}")
            import traceback
            traceback.print_exc()
    
    @lru_cache(maxsize=64)
    def recommend_sessions(self, query, top_k=3):
        """Recommend sessions based on a query with caching"""
        # For very short queries, don't do vector search
        if len(query.strip()) < 3:
            return self.processed_sessions[:top_k] if self.processed_sessions else []
        
        results = vector_store.search(query, top_k=top_k)
        
        # Extract recommended sessions
        recommendations = [result['item'] for result in results]
        
        return recommendations