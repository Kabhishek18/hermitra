# engines/session_recommender.py (consolidated version)

import sys
import os
import re
import json
from datetime import datetime, timedelta
from functools import lru_cache

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vector_store import vector_store
from utils.db import get_all_sessions, get_recent_sessions

class SessionRecommender:
    def __init__(self):
        # Load sessions data
        self.sessions = get_all_sessions()
        self.host_names = self._extract_host_names()
        
        # Process sessions for recommendation
        if self.sessions:
            self._preprocess_sessions()
            self._build_index()
        
        # Month name mappings for date parsing
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def _extract_host_names(self):
        """Extract unique host names from all sessions"""
        host_names = set()
        
        for session in self.sessions:
            host_users = session.get('host_user', [])
            for host in host_users:
                if isinstance(host, dict) and 'username' in host:
                    host_names.add(host['username'])
        
        return sorted(list(host_names))
    
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
    
    def get_recent_sessions(self, limit=10):
        """Get most recent sessions"""
        # Sort sessions by creation date if available
        sessions_with_dates = []
        for session in self.sessions:
            # Try to extract creation date
            session_date = None
            meta_data = session.get('meta_data', {})
            if meta_data and 'created_at' in meta_data:
                session_date = self._parse_date(meta_data['created_at'])
            
            # If no creation date, try schedule date
            if not session_date:
                schedule = session.get('schedule', {})
                if schedule and 'start_time' in schedule:
                    session_date = self._parse_date(schedule['start_time'])
            
            sessions_with_dates.append((session, session_date))
        
        # Sort by date (most recent first)
        sessions_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
        
        # Return sessions only (not dates)
        return [session for session, _ in sessions_with_dates[:limit]]
    
    def _parse_date(self, date_str):
        """Parse date from string"""
        if not isinstance(date_str, str):
            return None
            
        # Try different date formats
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                pass
                
        return None
    
    def search_sessions(self, search_params, max_results=5):
        """
        Search sessions with specific criteria
        
        Args:
            search_params: Dictionary with search parameters
              - title: keywords for title search
              - host: keywords for host name search
              - description: keywords for description search
              - start_date: minimum start date (datetime)
              - end_date: maximum start date (datetime)
            max_results: Maximum number of results to return
            
        Returns:
            List of matching session objects
        """
        if not self.sessions:
            return []
            
        # Special case for "all sessions" request
        if search_params.get('all_sessions'):
            return self.get_recent_sessions(limit=max_results)
            
        # Get search parameters
        title_query = search_params.get('title', '').lower() if search_params.get('title') else None
        host_query = search_params.get('host', '').lower() if search_params.get('host') else None
        description_query = search_params.get('description', '').lower() if search_params.get('description') else None
        start_date = search_params.get('start_date')
        end_date = search_params.get('end_date')
        
        # If no search parameters, return recent sessions
        if not title_query and not host_query and not description_query and not start_date and not end_date:
            return self.get_recent_sessions(limit=max_results)
        
        matching_sessions = []
        
        for session in self.sessions:
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
            
            # Check date range
            if (start_date or end_date) and matches:
                # Extract session date
                schedule = session.get('schedule', {})
                session_start = None
                
                if schedule and 'start_time' in schedule:
                    session_start = self._parse_date(schedule['start_time'])
                
                # If we have a date to check
                if session_start:
                    # Check start date constraint
                    if start_date and session_start < start_date:
                        matches = False
                    
                    # Check end date constraint
                    if end_date and session_start > end_date:
                        matches = False
                elif start_date or end_date:
                    # If date constraints exist but session has no date, exclude it
                    matches = False
            
            # If all checks passed, add to results
            if matches:
                matching_sessions.append(session)
                
                # Limit results
                if len(matching_sessions) >= max_results:
                    break
                
        return matching_sessions
    
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
        
        # Special case for very short queries like "By [name]"
        if query_lower.startswith("by ") and len(query_lower.split()) <= 3:
            host_name = query_lower[3:].strip()
            best_match = self._find_best_host_match(host_name)
            if best_match:
                search_params['host'] = best_match
            else:
                search_params['host'] = host_name
            return search_params
        
        # Extract host name
        host_patterns = [
            r'by\s+([a-zA-Z\s]+)',
            r'host(?:ed)?\s+by\s+([a-zA-Z\s]+)',
            r'with\s+([a-zA-Z\s]+)',
            r'from\s+([a-zA-Z\s]+)',
            r'sessions?\s+(?:of|by|with|from)\s+([a-zA-Z\s]+)'
        ]
        
        for pattern in host_patterns:
            match = re.search(pattern, query_lower)
            if match:
                host = match.group(1).strip()
                # Try to find the best match among known hosts
                best_match = self._find_best_host_match(host)
                if best_match:
                    search_params['host'] = best_match
                else:
                    search_params['host'] = host
                break
        
        # Check for direct host name mentions
        if 'host' not in search_params:
            for host in self.host_names:
                host_lower = host.lower()
                if host_lower in query_lower:
                    search_params['host'] = host
                    break
        
        # Extract topic/title
        topic_patterns = [
            r'about\s+([a-zA-Z\s]+)',
            r'on\s+([a-zA-Z\s]+)',
            r'related\s+to\s+([a-zA-Z\s]+)',
            r'sessions?\s+(?:about|on|regarding)\s+([a-zA-Z\s]+)'
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, query_lower)
            if match:
                title = match.group(1).strip()
                # Remove common words if they appear at the end
                title = re.sub(r'\s+(a|an|the|this|that|these|those)$', '', title)
                search_params['title'] = title
                search_params['description'] = title  # Search in both fields
                break
        
        # Extract date information
        
        # Check for specific month references
        for month_name, month_num in self.month_names.items():
            if month_name in query_lower:
                # Look for year after month name
                year_match = re.search(r'{}\s+(\d{{4}})'.format(month_name), query_lower)
                year = int(year_match.group(1)) if year_match else datetime.now().year
                
                # Create date range for the entire month
                start_date = datetime(year, month_num, 1)
                if month_num == 12:
                    end_date = datetime(year+1, 1, 1) - timedelta(microseconds=1)
                else:
                    end_date = datetime(year, month_num+1, 1) - timedelta(microseconds=1)
                
                search_params['start_date'] = start_date
                search_params['end_date'] = end_date
                break
        
        # Check for relative time references
        if 'start_date' not in search_params and 'end_date' not in search_params:
            time_period_match = re.search(r'(?:in|from|during|past|last)\s+(\d+)\s+(day|days|week|weeks|month|months)', query_lower)
            if time_period_match:
                number = int(time_period_match.group(1))
                unit = time_period_match.group(2)
                
                # Calculate days
                if 'day' in unit:
                    days = number
                elif 'week' in unit:
                    days = number * 7
                elif 'month' in unit:
                    days = number * 30
                
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                search_params['start_date'] = start_date
                search_params['end_date'] = end_date
        
        # Check for special keywords
        if 'start_date' not in search_params and 'end_date' not in search_params:
            if 'upcoming' in query_lower:
                search_params['start_date'] = datetime.now()
                search_params['end_date'] = datetime.now() + timedelta(days=365)  # Next year
            elif 'recent' in query_lower or 'latest' in query_lower:
                search_params['start_date'] = datetime.now() - timedelta(days=30)  # Last 30 days
                search_params['end_date'] = datetime.now()
            elif 'past' in query_lower:
                search_params['start_date'] = datetime.now() - timedelta(days=365)  # Last year
                search_params['end_date'] = datetime.now()
        
        # If no specific parameters found, try to extract keywords
        if not search_params:
            # Remove common words
            common_words = ['sessions', 'session', 'find', 'search', 'looking', 'for', 'me', 'the', 'a', 'an']
            words = query_lower.split()
            keywords = [word for word in words if word not in common_words and len(word) > 3]
            
            if keywords:
                search_params['title'] = ' '.join(keywords)
                search_params['description'] = ' '.join(keywords)
            else:
                # If still no parameters, return all recent sessions
                search_params['all_sessions'] = True
        
        return search_params
    
    def _find_best_host_match(self, partial_name):
        """Find the best matching host name for a partial name"""
        if not partial_name or len(partial_name.strip()) < 2:
            return None
            
        partial_name = partial_name.lower().strip()
        
        # First try exact matches
        for host in self.host_names:
            if host.lower() == partial_name:
                return host
        
        # Then try starts with matches
        starts_with_matches = []
        for host in self.host_names:
            if host.lower().startswith(partial_name):
                starts_with_matches.append(host)
                
        if starts_with_matches:
            # Return the shortest match (likely the first name if partial name is a first name)
            return min(starts_with_matches, key=len)
        
        # Then try contains matches
        contains_matches = []
        for host in self.host_names:
            if partial_name in host.lower():
                contains_matches.append(host)
                
        if contains_matches:
            # Return the shortest match that contains the partial name
            return min(contains_matches, key=len)
            
        return None
    
    def is_session_search_query(self, query):
        """Determine if a query is looking for sessions"""
        query_lower = query.lower()
        
        # Check for session-related keywords
        session_keywords = [
            'session', 'sessions', 'workshop', 'workshops', 
            'find session', 'search session', 'looking for session'
        ]
        
        for keyword in session_keywords:
            if keyword in query_lower:
                return True
                
        # Check for patterns like "sessions by [name]" or "sessions about [topic]"
        session_patterns = [
            r'sessions?\s+by\s+',
            r'sessions?\s+about\s+',
            r'sessions?\s+on\s+',
            r'sessions?\s+with\s+',
            r'find\s+sessions?\s+',
            r'looking\s+for\s+sessions?\s+',
            r'are\s+there\s+sessions?\s+'
        ]
        
        for pattern in session_patterns:
            if re.search(pattern, query_lower):
                return True
                
        # Special case for short "By [name]" queries
        if query_lower.startswith("by ") and len(query_lower.split()) <= 3:
            return True
            
        # Check for direct host mentions
        for host in self.host_names:
            if host.lower() in query_lower and 'session' in query_lower:
                return True
                
        return False
    
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
                session_date = self._parse_date(schedule['start_time'])
                if session_date:
                    date_info = f" | 📅 {session_date.strftime('%Y-%m-%d %H:%M')}"
            
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
        
    def get_all_sessions(self):
        """Return all processed sessions"""
        if hasattr(self, 'processed_sessions'):
            return self.processed_sessions
        return self.sessions