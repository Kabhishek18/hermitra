# asha/utils/mcp_handler.py
import time
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_handler")

class MCPSessionManager:
    """
    Model Context Protocol (MCP) Session Manager
    
    Handles context management for session-related conversations, enabling:
    - Long-term memory of mentioned sessions in conversation
    - Semantic linking between user queries and session data
    - Context-aware session recommendations
    - Better handling of follow-up questions about sessions
    """
    
    def __init__(self):
        # Context storage indexed by user_id
        self.session_context: Dict[str, Dict[str, Any]] = {}
        
        # Maximum sessions to store in context per user
        self.max_sessions = 20
        
        # Context decay parameters
        self.context_ttl = 3600  # Time to live for context in seconds (1 hour)
        self.last_cleanup = time.time()
        
        # Session metadata field mappings
        self.field_mappings = {
            'title': ['session_title', 'title'],
            'host': ['host_user', 'host', 'presenter', 'speaker'],
            'date': ['schedule', 'start_time', 'date', 'time'],
            'duration': ['duration'],
            'description': ['description', 'about', 'content'],
            'url': ['external_url', 'url', 'link'],
            'metadata': ['meta_data', 'metadata']
        }
        
        # Follow-up question patterns
        self.followup_patterns = [
            # General session reference patterns
            r'(that|this|the) session',
            r'(first|second|third|last|latest|previous|next) session',
            r'session (you|we) (mentioned|talked about|discussed)',
            
            # Specific information patterns
            r'(who|what|when|where|how) (is|are|was|were) the (host|presenter|speaker)',
            r'(what|when) (is|are|was|were) the (date|time|schedule)',
            r'how (long|much time) (is|does|will)',
            r'(what|tell me) about the (content|description|details)',
            r'(what|where) (is|are) the (url|link|website)',
            
            # Action patterns
            r'(can|how can|how do) I (join|register|sign up|attend|participate)',
            r'(show|give) me (more|details|information) about',
        ]
    
    def add_session_to_context(self, user_id: str, session: Dict[str, Any], query: str = "", relevance: float = 1.0):
        """
        Add a session to a user's conversation context
        
        Args:
            user_id: The user identifier
            session: The session data to add
            query: The query that led to this session (optional)
            relevance: How relevant this session is to the query (0.0-1.0)
        """
        if not user_id or not session:
            return
            
        # Create user context if it doesn't exist
        if user_id not in self.session_context:
            self.session_context[user_id] = {
                'mentioned_sessions': [],
                'last_updated': time.time(),
                'session_index': {},  # Index by session_id for quick lookup
                'query_history': []   # Track query history
            }
        
        user_context = self.session_context[user_id]
        
        # Get session ID
        session_id = session.get('session_id')
        if not session_id:
            # Generate a fallback ID if none exists
            title = session.get('session_title', 'Untitled')
            session_id = f"gen_{hash(title)}"
            session['session_id'] = session_id
        
        # Check if this session is already in context
        if session_id in user_context['session_index']:
            # Update existing session with fresh data
            for i, s in enumerate(user_context['mentioned_sessions']):
                if s['session']['session_id'] == session_id:
                    # Update the session data
                    user_context['mentioned_sessions'][i]['session'] = session
                    # Update metadata
                    user_context['mentioned_sessions'][i]['last_mentioned'] = time.time()
                    user_context['mentioned_sessions'][i]['mention_count'] += 1
                    user_context['mentioned_sessions'][i]['relevance'] = max(
                        user_context['mentioned_sessions'][i]['relevance'], 
                        relevance
                    )
                    if query:
                        user_context['mentioned_sessions'][i]['queries'].append(query)
                    
                    # Move this session to the front (most recently mentioned)
                    mentioned_session = user_context['mentioned_sessions'].pop(i)
                    user_context['mentioned_sessions'].insert(0, mentioned_session)
                    break
        else:
            # Add new session to context
            mentioned_session = {
                'session': session,
                'first_mentioned': time.time(),
                'last_mentioned': time.time(),
                'mention_count': 1,
                'relevance': relevance,
                'queries': [query] if query else []
            }
            
            # Add to front of list (most recent)
            user_context['mentioned_sessions'].insert(0, mentioned_session)
            
            # Add to index
            user_context['session_index'][session_id] = mentioned_session
            
            # Trim list if needed
            if len(user_context['mentioned_sessions']) > self.max_sessions:
                # Remove oldest session
                removed = user_context['mentioned_sessions'].pop()
                # Remove from index
                if removed['session']['session_id'] in user_context['session_index']:
                    del user_context['session_index'][removed['session']['session_id']]
        
        # Update last updated time
        user_context['last_updated'] = time.time()
        
        # Add query to history
        if query:
            user_context['query_history'].append({
                'query': query,
                'timestamp': time.time(),
                'related_session_id': session_id
            })
            # Limit query history
            if len(user_context['query_history']) > 20:
                user_context['query_history'] = user_context['query_history'][-20:]
    
    def add_sessions_to_context(self, user_id: str, sessions: List[Dict[str, Any]], query: str = ""):
        """Add multiple sessions to context with diminishing relevance"""
        if not sessions:
            return
            
        # Add each session with diminishing relevance
        for i, session in enumerate(sessions):
            # Relevance diminishes with position (first result is most relevant)
            relevance = max(0.2, 1.0 - (i * 0.15))
            self.add_session_to_context(user_id, session, query, relevance)
    
    def get_session_context(self, user_id: str, max_sessions: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent sessions from user's context
        
        Args:
            user_id: The user identifier
            max_sessions: Maximum number of sessions to return
            
        Returns:
            List of session data dictionaries
        """
        if user_id not in self.session_context:
            return []
            
        # Get user context
        user_context = self.session_context[user_id]
        
        # Return most recent sessions
        return [
            s['session'] 
            for s in user_context['mentioned_sessions'][:max_sessions]
        ]
    
    def get_session_by_reference(self, user_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by a reference in a query (e.g., "tell me more about that session")
        
        Args:
            user_id: The user identifier
            query: The query containing the reference
            
        Returns:
            The referenced session data dictionary or None if not found
        """
        if user_id not in self.session_context:
            return None
            
        user_context = self.session_context[user_id]
        
        # If no sessions in context, return None
        if not user_context['mentioned_sessions']:
            return None
            
        # Normalize query
        query = query.lower()
        
        # Check for specific session title references
        for mentioned in user_context['mentioned_sessions']:
            session = mentioned['session']
            title = session.get('session_title', '').lower()
            
            # If title is in query, this is likely the referenced session
            if title and len(title) > 5 and title in query:
                return session
        
        # Check for indexical references (first, second, last, etc.)
        if 'first session' in query:
            # First mentioned overall
            if len(user_context['mentioned_sessions']) > 0:
                return user_context['mentioned_sessions'][-1]['session']
        elif 'last session' in query or 'latest session' in query:
            # Most recently mentioned
            if len(user_context['mentioned_sessions']) > 0:
                return user_context['mentioned_sessions'][0]['session']
        elif 'second session' in query:
            if len(user_context['mentioned_sessions']) > 1:
                return user_context['mentioned_sessions'][-2]['session']
        
        # For general references like "that session", return the most recently mentioned
        for pattern in self.followup_patterns:
            if re.search(pattern, query):
                if user_context['mentioned_sessions']:
                    return user_context['mentioned_sessions'][0]['session']
        
        # No specific reference found
        return None
    
    def _extract_text_from_json(self, node: Dict[str, Any], text_parts: List[str]):
        """
        Recursively extract text from a JSON structure like the one used in session descriptions
        
        Args:
            node: The JSON node to extract text from
            text_parts: List to append text parts to
        """
        if isinstance(node, dict):
            # Extract text field if present
            if 'text' in node:
                text_parts.append(node['text'])
                
            # Recursively process children
            if 'children' in node:
                for child in node['children']:
                    self._extract_text_from_json(child, text_parts)
        elif isinstance(node, list):
            # Process list of nodes
            for item in node:
                self._extract_text_from_json(item, text_parts)
    
    def extract_session_field(self, session: Dict[str, Any], field_type: str) -> Any:
        """
        Extract a specific field from a session using field mappings
        
        Args:
            session: The session data dictionary
            field_type: The type of field to extract (title, host, date, etc.)
            
        Returns:
            The extracted field value or None if not found
        """
        if not session or field_type not in self.field_mappings:
            return None
            
        # Get possible field names
        field_names = self.field_mappings[field_type]
        
        # Check direct fields
        for name in field_names:
            if name in session:
                value = session[name]
                
                # Special handling for different field types
                if field_type == 'host' and isinstance(value, list):
                    # Extract host name from host_user array
                    for host in value:
                        if isinstance(host, dict) and 'username' in host:
                            return host.get('username')
                    return None
                elif field_type == 'date' and name == 'schedule':
                    # Extract date from schedule object
                    if isinstance(value, dict) and 'start_time' in value:
                        return value.get('start_time')
                    return None
                
                return value
        
        return None
    
    def format_session_response(self, session: Dict[str, Any], query: str) -> str:
        """
        Format a session as a natural language response based on the query
        
        Args:
            session: The session data dictionary
            query: The query that led to this response
            
        Returns:
            Formatted response text
        """
        query = query.lower()
        
        # Get session fields
        title = self.extract_session_field(session, 'title') or "Untitled Session"
        host = self.extract_session_field(session, 'host') or "Unknown host"
        date_str = self.extract_session_field(session, 'date') or "Unscheduled"
        duration = self.extract_session_field(session, 'duration') or "Unknown duration"
        description = self.extract_session_field(session, 'description') or ""
        url = self.extract_session_field(session, 'url') or ""
        
        # Try to format date if it's a string
        formatted_date = date_str
        if isinstance(date_str, str):
            # Try different date formats
            for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    formatted_date = dt.strftime("%A, %B %d, %Y at %I:%M %p")
                    break
                except:
                    pass
        
        # Clean description if it's JSON
        if isinstance(description, str) and description.strip().startswith('{'):
            try:
                desc_obj = json.loads(description)
                # Try to extract text
                if 'root' in desc_obj and 'children' in desc_obj['root']:
                    text_parts = []
                    self._extract_text_from_json(desc_obj['root'], text_parts)
                    description = ' '.join(text_parts)
            except:
                # If parsing fails, use as is
                pass
                
        # Truncate description if needed
        if description and len(description) > 200:
            description = description[:197] + "..."
            
        # Format response based on query type
        if any(term in query for term in ['when', 'date', 'time', 'schedule']):
            # Date/time query
            return f"The session \"{title}\" is scheduled for {formatted_date}. It has a duration of {duration}."
        
        elif any(term in query for term in ['who', 'host', 'presenter', 'speaker']):
            # Host query
            return f"The session \"{title}\" is hosted by {host}."
            
        elif any(term in query for term in ['how long', 'duration']):
            # Duration query
            return f"The session \"{title}\" has a duration of {duration}."
            
        elif any(term in query for term in ['link', 'url', 'join', 'attend', 'register']):
            # URL query
            if url:
                return f"You can join the session \"{title}\" using this link: {url}"
            else:
                return f"I don't have a registration link for the session \"{title}\". Please check the platform for registration details."
                
        elif any(term in query for term in ['about', 'what is', 'tell me about', 'describe']):
            # Description query
            response = f"The session \"{title}\" is hosted by {host} and scheduled for {formatted_date}."
            if description:
                response += f" Here's what it's about: {description}"
            return response
            
        else:
            # General information
            response = f"**Session: {title}**\n\n"
            response += f"📅 Scheduled for: {formatted_date}\n"
            response += f"👤 Host: {host}\n"
            response += f"⏱️ Duration: {duration}\n"
            
            if description:
                response += f"\n**Description**: {description}\n"
                
            if url:
                response += f"\n🔗 [Join Session]({url})\n"
                
            return response
    
    def is_followup_query(self, user_id: str, query: str) -> bool:
        """
        Determine if a query is a follow-up about a previously mentioned session
        
        Args:
            user_id: The user identifier
            query: The query to check
            
        Returns:
            True if this appears to be a follow-up query, False otherwise
        """
        if not user_id or not query or user_id not in self.session_context:
            return False
            
        # If no sessions have been mentioned, can't be a follow-up
        if not self.session_context[user_id]['mentioned_sessions']:
            return False
            
        # Normalize query
        query_lower = query.lower()
        
        # Check for session title references
        for mentioned in self.session_context[user_id]['mentioned_sessions']:
            session = mentioned['session']
            title = session.get('session_title', '').lower()
            
            # If title is substantial and in the query, this is a follow-up
            if title and len(title) > 5 and title in query_lower:
                return True
                
        # Check for follow-up patterns
        for pattern in self.followup_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False
    
    def handle_followup_query(self, user_id: str, query: str) -> Optional[str]:
        """
        Generate a response for a follow-up query about a session
        
        Args:
            user_id: The user identifier
            query: The follow-up query
            
        Returns:
            Formatted response text or None if not handled
        """
        # Get the referenced session
        session = self.get_session_by_reference(user_id, query)
        if not session:
            return None
            
        # Mark this session as mentioned again
        self.add_session_to_context(user_id, session, query, 1.0)
        
        # Format a response based on the query
        return self.format_session_response(session, query)
    
    def cleanup_old_contexts(self):
        """Remove expired contexts to prevent memory leaks"""
        if time.time() - self.last_cleanup < 300:  # Only check every 5 minutes
            return
            
        self.last_cleanup = time.time()
        current_time = time.time()
        
        # Find expired contexts
        expired_keys = []
        for user_id, context in self.session_context.items():
            if current_time - context['last_updated'] > self.context_ttl:
                expired_keys.append(user_id)
                
        # Remove expired contexts
        for key in expired_keys:
            del self.session_context[key]
            
        logger.info(f"Cleaned up {len(expired_keys)} expired contexts")
    
    def get_context_serializable(self, user_id: str) -> Dict[str, Any]:
        """
        Get a serializable representation of the user's context for debugging
        
        Args:
            user_id: The user identifier
            
        Returns:
            Dictionary with context information
        """
        if user_id not in self.session_context:
            return {"error": "No context found for this user"}
            
        context = self.session_context[user_id]
        
        # Create a simplified version for display
        serializable = {
            "mentioned_sessions_count": len(context['mentioned_sessions']),
            "last_updated": datetime.fromtimestamp(context['last_updated']).isoformat(),
            "recent_sessions": [],
            "recent_queries": context['query_history'][-5:] if 'query_history' in context else []
        }
        
        # Add recent sessions info
        for mentioned in context['mentioned_sessions'][:5]:
            session = mentioned['session']
            serializable["recent_sessions"].append({
                "title": session.get('session_title', 'Untitled'),
                "first_mentioned": datetime.fromtimestamp(mentioned['first_mentioned']).isoformat(),
                "last_mentioned": datetime.fromtimestamp(mentioned['last_mentioned']).isoformat(),
                "mention_count": mentioned['mention_count'],
                "relevance": mentioned['relevance']
            })
            
        return serializable

# Initialize global MCP session manager
mcp_session_manager = MCPSessionManager()