# asha/engines/enhanced_career_guidance.py
import sys
import os
import re
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Set, Union

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ollama import generate_text
from utils.improved_nlp_search import improved_nlp_search
from utils.mcp_handler import mcp_session_manager
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced_career_guidance")

class EnhancedCareerGuidanceEngine:
    """
    Enhanced career guidance engine with improved session search and context management.
    
    Features:
    - Integration with Model Context Protocol (MCP) for better conversation context
    - Advanced natural language session search with semantic understanding
    - Improved follow-up handling for session references
    - Context-aware session recommendations
    """
    
    def __init__(self):
        # Define the system prompt with guidance guardrails
        self.system_prompt = """
        You are ASHA, a career guidance assistant specialized in helping women professionals.
        Your responses should:
        - Focus exclusively on career-related topics
        - Avoid gender stereotypes and biases
        - Provide practical, actionable advice
        - Reference best practices in professional development
        - Acknowledge when a question is outside your expertise
        - Keep responses concise and to the point (100-150 words maximum)
        
        When unsure, ask clarifying questions rather than making assumptions.
        """
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Define off-topic patterns for quick classification
        self.off_topic_patterns = [
            r'\b(weather|temperature|forecast)\b',
            r'\b(sports|game|match|score)\b',
            r'\b(recipe|cook|food|meal)\b',
            r'\b(movie|film|show|watch)\b',
            r'\b(music|song|band|artist)\b',
        ]
        
        # Initialize session tracking
        self.user_session_context = {}  # To track mentioned sessions per user
        
        # Career-related keywords for proactive session recommendations
        self.career_keywords = {
            'leadership': [
                'leadership', 'lead', 'leading', 'manager', 'executive', 
                'director', 'management', 'supervise', 'authority'
            ],
            'interviewing': [
                'interview', 'interviewing', 'recruiter', 'hiring', 
                'job application', 'resume', 'cv', 'cover letter'
            ],
            'salary': [
                'salary', 'compensation', 'negotiate', 'benefits', 
                'offer', 'counter offer', 'raise', 'promotion'
            ],
            'skills': [
                'skill', 'learning', 'develop', 'education', 'training',
                'certificate', 'course', 'workshop', 'upskill'
            ],
            'career_transition': [
                'transition', 'change', 'switch', 'pivot', 'new role',
                'different industry', 'career move', 'job search'
            ],
            'networking': [
                'network', 'connect', 'relationship', 'mentor', 'contact',
                'linkedin', 'referral', 'introduction', 'community'
            ]
        }
        
        logger.info("Enhanced career guidance engine initialized")
    
    def is_off_topic(self, query: str) -> bool:
        """Quickly check if query is off-topic to avoid LLM call"""
        query_lower = query.lower()
        for pattern in self.off_topic_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def is_session_query(self, query: str) -> bool:
        """Determine if a query is specifically about sessions"""
        return improved_nlp_search.is_search_query(query)
    
    def handle_session_query(self, query: str, user_id: Optional[str] = None) -> str:
        """Handle a query specifically about sessions"""
        return improved_nlp_search.process_query(query, user_id)
    
    def get_career_topic(self, query: str) -> Optional[str]:
        """
        Identify the career topic from a query
        
        Args:
            query: The query text
            
        Returns:
            Career topic if identified, None otherwise
        """
        query_lower = query.lower()
        
        # Check each topic category
        for topic, keywords in self.career_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return topic
        
        return None
    
    def get_proactive_session_recommendations(self, query: str, 
                                           user_id: Optional[str] = None, 
                                           limit: int = 2) -> Optional[str]:
        """
        Get proactive session recommendations based on a career query
        
        Args:
            query: The career-related query
            user_id: Optional user ID for context tracking
            limit: Maximum number of sessions to recommend
            
        Returns:
            Formatted recommendation text or None if no relevant sessions
        """
        # Don't recommend sessions if the query is already about sessions
        if self.is_session_query(query):
            return None
            
        # Identify career topic
        topic = self.get_career_topic(query)
        if not topic:
            return None
            
        # Search for sessions related to the topic
        search_params = {
            'description': topic,
            'title': topic
        }
        
        # Use the career topic as a search term
        sessions = improved_nlp_search.search_sessions(search_params, max_results=limit)
        
        if not sessions or len(sessions) == 0:
            return None
            
        # Add sessions to user context if user_id provided
        if user_id:
            mcp_session_manager.add_sessions_to_context(user_id, sessions, query)
        
        # Format the recommendations
        recommendation = "\n\n**You might be interested in these related sessions:**\n\n"
        
        for i, session in enumerate(sessions):
            title = session.get('session_title', 'Untitled Session')
            
            # Get host information
            host_name = "Unknown host"
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_name = host_users[0].get('username', 'Unknown host')
            
            # Format recommendation
            recommendation += f"{i+1}. **{title}** (Host: {host_name})"
            
            # Add URL if available
            if 'external_url' in session and session['external_url']:
                recommendation += f" - [Join Session]({session['external_url']})"
                
            recommendation += "\n"
        
        return recommendation
    
    def process_query(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Process a user query and return a response
        
        Args:
            query: The user query
            user_id: Optional user ID for context tracking
            
        Returns:
            Formatted response text
        """
        try:
            start_time = time.time()
            logger.info(f"Processing query: '{query}'")
            
            # Add user query to conversation history
            self.conversation_history.append({"role": "user", "content": query})
            
            # Check if this is a follow-up question about sessions
            if user_id and mcp_session_manager.is_followup_query(user_id, query):
                logger.info("Handling as session follow-up")
                response = mcp_session_manager.handle_followup_query(user_id, query)
                if response:
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            
            # Check if this is a session search query
            if self.is_session_query(query):
                logger.info("Processing as session search")
                response = self.handle_session_query(query, user_id)
                self.conversation_history.append({"role": "assistant", "content": response})
                end_time = time.time()
                logger.info(f"Query processing completed in {end_time - start_time:.2f} seconds")
                return response
            
            # Quick check if query is off-topic
            if self.is_off_topic(query):
                response = ("I'm focused on helping with career guidance for women professionals. "
                           "Could we discuss your professional development goals or challenges instead?")
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            
            # Limit history to recent messages to reduce context size
            recent_history = self.conversation_history[-6:]  # Only use last 3 exchanges
            
            # Construct the prompt with optimized history format
            conversation_text = ""
            for message in recent_history:
                role = "Human" if message["role"] == "user" else "ASHA"
                # Truncate very long messages to reduce context size
                content = message["content"]
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation_text += f"{role}: {content}\n"
            
            # Generate response with reduced max_tokens
            prompt = conversation_text + "ASHA:"
            response = generate_text(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=800,  # Reduced from default
                temperature=0.6  # Slightly reduced for more deterministic responses
            )
            
            # Check if we should add proactive session recommendations
            session_recommendations = self.get_proactive_session_recommendations(query, user_id)
            if session_recommendations:
                response += session_recommendations
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            end_time = time.time()
            logger.info(f"Query processing completed in {end_time - start_time:.2f} seconds")
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            traceback.print_exc()
            return "I'm having trouble processing your request. Could you please try asking a simpler question?"

# Initialize enhanced engine
enhanced_career_guidance_engine = EnhancedCareerGuidanceEngine()