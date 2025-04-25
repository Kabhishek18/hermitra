# asha/utils/ollama.py
import requests
import json
import config

class OllamaClient:
    def __init__(self, model=config.OLLAMA_MODEL, host=config.OLLAMA_HOST):
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"
 
    def generate(self, prompt, system_prompt=None, max_tokens=2000, temperature=0.7):
        """Generate text using Ollama API with a strict timeout"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            # Very short timeout to fail fast
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            # Hard-coded fallback response for quick testing
            return "I am ASHA, your career guidance assistant. I'm here to help with your professional development questions. How can I assist you today?"

    def is_available(self):
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except:
            return False

# Initialize a global client
ollama_client = OllamaClient()

# Convenience function
def generate_text(prompt, system_prompt=None, max_tokens=2000, temperature=0.7):
    return ollama_client.generate(prompt, system_prompt, max_tokens, temperature)