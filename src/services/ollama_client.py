# src/services/ollama_client.py
import requests
import json
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

load_dotenv()

class OllamaClient:
    def __init__(self, options=None):
        options = options or {}
        self.endpoint = options.get('endpoint', os.getenv('OLLAMA_ENDPOINT'))
        self.default_model = options.get('model', os.getenv('OLLAMA_DEFAULT_MODEL'))
    
    def generate(self, params):
        try:
            model = params.get('model', self.default_model)
            
            # For newer Ollama API (chat endpoint)
            if 'messages' in params:
                api_url = f"{self.endpoint}/api/chat"
                request_body = {
                    "model": model,
                    "messages": params['messages'],
                    "options": {
                        "temperature": params.get('options', {}).get('temperature', 0.7),
                        "top_p": params.get('options', {}).get('top_p', 0.9),
                        "max_tokens": params.get('options', {}).get('max_tokens', 512)
                    }
                }
                
                if params.get('system'):
                    request_body["system"] = params['system']
                
                response = requests.post(api_url, json=request_body)
                response.raise_for_status()
                response_data = response.json()
                
                # Handle chat response format
                return response_data.get('message', {}).get('content', '')
            
            # For older Ollama API (generate endpoint)
            else:
                api_url = f"{self.endpoint}/api/generate"
                request_body = {
                    "model": model,
                    "prompt": params.get('prompt', ''),
                    "options": {
                        "temperature": params.get('options', {}).get('temperature', 0.7),
                        "top_p": params.get('options', {}).get('top_p', 0.9),
                        "max_tokens": params.get('options', {}).get('max_tokens', 512)
                    }
                }
                
                if params.get('system'):
                    request_body["system"] = params['system']
                
                response = requests.post(api_url, json=request_body)
                response.raise_for_status()
                
                # For debugging
                logger.debug(f"Ollama API response: {response.text[:200]}...")
                
                try:
                    response_data = response.json()
                    return response_data.get('response', '')
                except json.JSONDecodeError as e:
                    # Handle non-JSON responses
                    logger.error(f"Failed to parse JSON from Ollama: {str(e)}")
                    logger.error(f"Response text: {response.text[:200]}...")
                    
                    # Try to extract text response as a fallback
                    if "response" in response.text:
                        try:
                            # Try to extract just the response field
                            response_text = response.text.split('"response":')[1]
                            response_text = response_text.split('",')[0].strip('" ')
                            return response_text
                        except Exception:
                            pass
                    
                    return "I encountered an issue processing your request."
        except Exception as e:
            logger.error(f"Error generating response from Ollama: {str(e)}")
            return "I encountered an issue with the language model service."
    
    def classify(self, text, options=None):
        options = options or {}
        classification_model = options.get('model', os.getenv('OLLAMA_CLASSIFICATION_MODEL'))
        
        categories = options.get('classification_categories', [
            'career_guidance', 'job_search', 'skill_development', 
            'interview_preparation', 'workplace_challenges', 
            'off_topic', 'inappropriate'
        ])
        
        system_prompt = f"""
            You are an intent classifier for a career guidance chatbot.
            Classify the following text into one of these categories:
            {', '.join(categories)}
            
            Respond with ONLY the category name and nothing else.
        """
        
        try:
            # Use simple prompt/system approach for classification
            response = self.generate({
                'model': classification_model,
                'prompt': text,
                'system': system_prompt,
                'options': {
                    'temperature': 0.1,
                    'max_tokens': 20
                }
            })
            
            # Clean up the response
            response = response.strip().lower()
            
            # Simple validation - make sure it's one of our categories
            if response not in categories:
                # Find the closest match or use a default
                for category in categories:
                    if category in response:
                        response = category
                        break
                else:
                    response = 'career_guidance'  # Default to a safe category
            
            return {
                'category': response,
                'confidence': 1.0  # Simplified, actual confidence not available from basic Ollama
            }
        except Exception as e:
            logger.error(f"Error classifying text: {str(e)}")
            return {
                'category': 'general',
                'confidence': 0,
                'error': str(e)
            }