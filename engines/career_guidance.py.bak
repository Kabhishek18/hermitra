# asha/engines/career_guidance.py
import sys
import os
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ollama import generate_text
import config

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
    
    def process_query(self, query):
        """Process a user query and return a response."""
        try:
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
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            print(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble processing your request. Could you please try again?"