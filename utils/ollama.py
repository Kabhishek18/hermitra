# asha/utils/ollama.py
import requests
import json
import sys
import os
import time
from functools import lru_cache

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class OllamaClient:
    def __init__(self, model=config.OLLAMA_MODEL, host=config.OLLAMA_HOST):
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"
        # Track last request time for rate limiting
        self.last_request_time = 0
        # Minimum time between requests (in seconds)
        self.rate_limit = 0.1
    
    @lru_cache(maxsize=32)  # Cache recent responses
    def generate_cached(self, prompt_key, system_prompt, max_tokens, temperature):
        """Cached version of generate for repeated queries"""
        prompt = prompt_key  # Unpacking from the hashable key
        return self.generate(prompt, system_prompt, max_tokens, temperature)
 
    def generate(self, prompt, system_prompt=None, max_tokens=1000, temperature=0.7):
        """Generate text using Ollama API with rate limiting and optimizations"""
        # Apply rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Streaming increases overhead
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                # Add context size limit to prevent unnecessary memory usage
                "num_ctx": config.MAX_CONTEXT_SIZE
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            # Update last request time
            self.last_request_time = time.time()
            
            response = requests.post(self.api_url, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.Timeout:
            return "I'm currently experiencing high demand. Could you please try your question again in a moment?"
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            return "I'm having trouble accessing my knowledge. Please try a simpler question or try again shortly."

    def is_available(self):
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

# Initialize a global client
ollama_client = OllamaClient()

# Convenience function with caching for common queries
def generate_text(prompt, system_prompt=None, max_tokens=config.MAX_RESPONSE_TOKENS, temperature=0.7):
    """Generate text with caching for common prompts"""
    # For common system prompts, use caching
    if len(prompt) < 1000 and (system_prompt is None or len(system_prompt) < 500):
        # Make immutable for caching
        prompt_key = prompt
        return ollama_client.generate_cached(prompt_key, system_prompt, max_tokens, temperature)
    else:
        # For unique or very long prompts, skip cache
        return ollama_client.generate(prompt, system_prompt, max_tokens, temperature)