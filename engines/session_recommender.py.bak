# asha/engines/session_recommender.py
import sys
import os
import re
import json
from datetime import datetime
from functools import lru_cache

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vector_store import vector_store
from utils.db import get_all_sessions, get_recent_sessions

class SessionRecommender:
    def __init__(self):
        # Load sessions data
        self.sessions = get_all_sessions()
        
        # Process sessions for recommendation
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
        if isinstance(node, dict):
            if 'text' in node:
                text_parts.append(node['text'])
                
            if 'children' in node:
                for child in node['children']:
                    self._extract_text_from_lexical(child, text_parts)
        elif isinstance(node, list):
            for item in node:
                self._extract_text_from_lexical(item, text_parts)
    
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
                
            # Create the index
            vector_store.create_index(self.session_texts, self.processed_sessions)
            print("Session index built successfully")
        except Exception as e:
            print(f"Error building session index: {e}")
            import traceback
            traceback.print_exc()
    
    @lru_cache(maxsize=32)
    def recommend_sessions(self, query, top_k=3):
        """Recommend sessions based on a query with caching"""
        # For very short queries, don't do vector search
        if len(query.strip()) < 3:
            return self.processed_sessions[:top_k] if self.processed_sessions else []
        
        results = vector_store.search(query, top_k=top_k)
        
        # Extract recommended sessions
        recommendations = [result['item'] for result in results]
        
        return recommendations
    
    def search_sessions(self, search_params, max_results=5):
        """
        Search sessions with specific criteria
        
        Args:
            search_params: Dictionary with search parameters
              - title: keywords for title search
              - host: keywords for host name search
              - description: keywords for description search
            max_results: Maximum number of results to return
            
        Returns:
            List of matching session objects
        """
        if not self.sessions:
            return []
            
        # Get search parameters
        title_query = search_params.get('title', '').lower() if search_params.get('title') else None
        host_query = search_params.get('host', '').lower() if search_params.get('host') else None
        description_query = search_params.get('description', '').lower() if search_params.get('description') else None
        
        # If no search parameters, return recent sessions
        if not title_query and not host_query and not description_query:
            return self.processed_sessions[:max_results] if self.processed_sessions else []
        
        matching_sessions = []
        
        for session in self.processed_sessions:
            # Default to True, and set to False if any criteria fails
            matches = True
            
            # Check title
            if title_query and matches:
                session_title = session.get('session_title', '').lower()
                if title_query not in session_title:
                    matches = False
            
            # Check host name
            if host_query and matches:
                host_found = False
                host_users = session.get('host_user', [])
                for host_user in host_users:
                    username = host_user.get('username', '').lower()
                    if host_query in username:
                        host_found = True
                        break
                if not host_found:
                    matches = False
            
            # Check description
            if description_query and matches:
                session_desc = self._extract_description_text(session.get('description', '')).lower()
                if description_query not in session_desc:
                    matches = False
            
            # If all checks passed, add to results
            if matches:
                matching_sessions.append(session)
                
        # Limit results
        return matching_sessions[:max_results]
    
    def extract_search_params_from_query(self, query):
        """
        Extract search parameters from a natural language query
        
        Args:
            query: The natural language query
            
        Returns:
            Dictionary of search parameters
        """
        search_params = {}
        query_lower = query.lower()
        
        # Extract host name
        host_patterns = [
            r'by\s+([a-zA-Z\s]+)',
            r'host(?:ed)?\s+by\s+([a-zA-Z\s]+)',
            r'with\s+([a-zA-Z\s]+)',
            r'from\s+([a-zA-Z\s]+)'
        ]
        
        for pattern in host_patterns:
            match = re.search(pattern, query_lower)
            if match:
                host = match.group(1).strip()
                search_params['host'] = host
                break
        
        # Extract topic/title
        title_patterns = [
            r'about\s+([a-zA-Z\s]+)',
            r'on\s+([a-zA-Z\s]+)',
            r'related\s+to\s+([a-zA-Z\s]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, query_lower)
            if match:
                title = match.group(1).strip()
                search_params['title'] = title
                search_params['description'] = title  # Search in both fields
                break
        
        # If no specific patterns matched, try to extract keywords
        if not search_params:
            # Remove common words
            common_words = ['sessions', 'session', 'find', 'search', 'looking', 'for', 'me', 'the', 'a', 'an']
            words = query_lower.split()
            keywords = [word for word in words if word not in common_words and len(word) > 3]
            
            if keywords:
                search_params['title'] = ' '.join(keywords)
                search_params['description'] = ' '.join(keywords)
        
        return search_params
    
    def format_session_recommendations(self, sessions, query=""):
        """
        Format session recommendations as a readable message
        
        Args:
            sessions: List of session objects
            query: The original query (optional)
            
        Returns:
            Formatted text
        """
        if not sessions:
            return "I couldn't find any relevant sessions for your query. You can try another search with different keywords."
        
        response = f"I found {len(sessions)} sessions that might interest you:\n\n"
        
        for i, session in enumerate(sessions):
            title = session.get('session_title', 'Untitled Session')
            
            # Format host information
            host_info = "Unknown host"
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_info = host_users[0].get('username', 'Unknown host')
            
            # Format date if available
            date_info = ""
            schedule = session.get('schedule', {})
            if schedule and 'start_time' in schedule:
                start_time = schedule['start_time']
                if isinstance(start_time, str):
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
                        try:
                            dt = datetime.strptime(start_time, fmt)
                            date_info = f" | 📅 {dt.strftime('%Y-%m-%d %H:%M')}"
                            break
                        except:
                            continue
            
            # Format session entry
            response += f"**{i+1}. {title}**\n"
            response += f"👤 Host: {host_info} | ⏱️ Duration: {session.get('duration', 'N/A')}{date_info}\n"
            
            # Add URL if available
            if 'external_url' in session and session['external_url']:
                response += f"🔗 [Join Session]({session['external_url']})\n"
            
            # Add separator between sessions
            if i < len(sessions) - 1:
                response += "\n"
        
        return response