# asha/engines/career_guidance.py
import sys
import os
import re
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
    
    def is_off_topic(self, query):
        """Quickly check if query is off-topic to avoid LLM call"""
        query_lower = query.lower()
        for pattern in self.off_topic_patterns:
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
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            print(f"Error processing query: {e}")
            return "I'm having trouble processing your request. Could you please try asking a simpler question?"