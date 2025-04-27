# engines/career_guidance.py (consolidated version)

import sys
import os
import re
import time
import logging
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ollama import generate_text
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("career_guidance")

class CareerGuidanceEngine:
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
        - Keep responses concise and focused
        
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
            r'\b(politics|election|vote|president)\b',
            r'\b(religion|god|worship|pray)\b'
        ]
        
        # User context tracking
        self.user_contexts = {}
        
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
    
    def is_off_topic(self, query):
        """Quickly check if query is off-topic to avoid LLM call"""
        query_lower = query.lower()
        for pattern in self.off_topic_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
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
                
        return False
    
    def get_career_topic(self, query):
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
    
    def get_proactive_session_recommendations(self, query, session_recommender):
        """
        Get proactive session recommendations based on a career query
        
        Args:
            query: The career-related query
            session_recommender: Session recommender instance
            
        Returns:
            Formatted recommendation text or None if no relevant sessions
        """
        # Don't recommend sessions if the query is already about sessions
        if self.is_session_search_query(query):
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
        sessions = session_recommender.search_sessions(search_params, max_results=2)
        
        if not sessions or len(sessions) == 0:
            return None
            
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
    
    def process_query(self, query, user_id=None, session_recommender=None):
        """
        Process a user query and return a response
        
        Args:
            query: The user query
            user_id: Optional user ID for context tracking
            session_recommender: Optional session recommender for proactive recommendations
            
        Returns:
            Formatted response text
        """
        try:
            start_time = time.time()
            logger.info(f"Processing query: '{query}'")
            
            # Add user query to conversation history
            self.conversation_history.append({"role": "user", "content": query})
            
            # Quick check if query is off-topic
            if self.is_off_topic(query):
                response = ("I'm focused on helping with career guidance for women professionals. "
                           "Could we discuss your professional development goals or challenges instead?")
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            
            # Limit history to recent messages to reduce context size
            recent_history = self.conversation_history[-6:]  # Last 3 exchanges
            
            # Construct the prompt with conversation history
            conversation_text = ""
            for message in recent_history:
                role = "Human" if message["role"] == "user" else "ASHA"
                # Truncate very long messages
                content = message["content"]
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation_text += f"{role}: {content}\n"
            
            # Generate response
            prompt = conversation_text + "ASHA:"
            response = generate_text(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=config.MAX_RESPONSE_TOKENS,
                temperature=0.7
            )
            
            # Check if we should add proactive session recommendations
            if session_recommender and not self.is_session_search_query(query):
                recommendations = self.get_proactive_session_recommendations(query, session_recommender)
                if recommendations:
                    response += recommendations
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Track processing time for performance monitoring
            end_time = time.time()
            logger.info(f"Query processed in {end_time - start_time:.2f} seconds")
            
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble processing your request. Could you please try again?"