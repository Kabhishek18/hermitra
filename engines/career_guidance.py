# asha/engines/career_guidance.py
import sys
import os
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
    
    def process_query(self, query):
        """Process a user query and return a response."""
        try:
            # Add user query to conversation history
            self.conversation_history.append({"role": "user", "content": query})
            
            # Construct the prompt with history
            conversation_text = ""
            for message in self.conversation_history[-5:]:  # Only use the last 5 messages
                role = "Human" if message["role"] == "user" else "ASHA"
                conversation_text += f"{role}: {message['content']}\n"
            
            # Generate response
            prompt = conversation_text + "ASHA:"
            response = generate_text(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0.7
            )
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            print(f"Error processing query: {e}")
            return "I'm having trouble processing your request. Could you please try again?"