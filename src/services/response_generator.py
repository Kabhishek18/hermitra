import re
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

load_dotenv()

class ResponseGenerator:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.default_model = os.getenv('OLLAMA_DEFAULT_MODEL', 'mistral:latest')
        self.advanced_model = os.getenv('OLLAMA_ADVANCED_MODEL', 'llama3.3:latest')
    
    def generate_response(self, prompt_context, options=None):
        options = options or {}
        try:
            # Determine which model to use based on query complexity
            model_to_use = self.advanced_model if options.get('use_advanced_model') else self.default_model
            
            # Construct system prompt with guardrails
            system_prompt = f"""
                You are ASHA, a specialized career guidance assistant for women professionals.
                
                Guidelines:
                - Provide tailored career guidance based on the user's background and goals
                - Maintain professional and supportive tone
                - Do not offer personal opinions or predictions
                - Do not reinforce stereotypes
                - Keep responses focused on career development
                - Use concrete examples when appropriate
                - If unsure, acknowledge limitations instead of making up information
                
                User Preferences:
                {prompt_context.get('user_preferences', '')}
                
                Retrieved Context:
                {prompt_context.get('retrieved_context', '')}
            """
            
            # Format conversation history for the LLM
            response = self.ollama_client.generate({
                'model': model_to_use,
                'prompt': prompt_context.get('current_query', ''),
                'system': system_prompt,
                'context': prompt_context.get('history', []),
                'options': {
                    'temperature': options.get('temperature', 0.7),
                    'max_tokens': options.get('max_tokens', 1024)
                }
            })
            
            return self.apply_safeguards(response)
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return "I'm sorry, I encountered an issue while processing your request. Let's try a different approach or question."
    
    def apply_safeguards(self, response):
        safeguarded_response = response
        
        # Apply post-processing safeguards
        
        # Check for personal opinions markers
        opinion_markers = ['I believe', 'In my opinion', 'I think', 'I feel']
        for marker in opinion_markers:
            safeguarded_response = re.sub(
                f"{marker}\\s", 
                "Research suggests ", 
                safeguarded_response, 
                flags=re.IGNORECASE
            )
        
        # Check for gender stereotypes
        stereotype_markers = [
            'women are naturally', 'women tend to be more', 'women should',
            'men are better at', 'typical female', 'typical male'
        ]
        
        for marker in stereotype_markers:
            if marker.lower() in safeguarded_response.lower():
                safeguarded_response += "\n\nI want to note that individual capabilities vary greatly regardless of gender, and career success depends on many factors including skills, experience, and opportunities."
                break
        
        return safeguarded_response