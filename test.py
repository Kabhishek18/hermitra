import streamlit as st
import requests
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="ASHA Test Page",
    page_icon="🧪",
    layout="wide"
)

st.title("ASHA Chatbot - Test Page")

# Simple function to call Ollama
def query_ollama(prompt, model="mistral:latest", system=None):
    try:
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        # Add system message if provided
        if system:
            payload["system"] = system
        
        st.write(f"Sending request to Ollama...")
        
        # Make the request
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60  # Set timeout to 60 seconds
        )
        
        # Show raw response for debugging
        st.write(f"Status code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            try:
                result = response.json()
                return result.get("response", "")
            except Exception as e:
                st.error(f"Error parsing response: {str(e)}")
                st.code(response.text[:500])  # Show the raw response text
                return "Error parsing model response."
        else:
            st.error(f"Ollama API error: {response.status_code}")
            st.code(response.text[:500])
            return f"Model service error: {response.status_code}"
    
    except Exception as e:
        st.error(f"Error calling Ollama: {str(e)}")
        return "Error connecting to the language model service."

# Test availability of models
st.header("1. Testing Ollama Models")

model_container = st.container()

with model_container:
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            st.success(f"✅ Connected to Ollama service")
            st.write("Available models:")
            for model in models:
                st.write(f"- {model.get('name')}")
        else:
            st.error(f"❌ Could not list models: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Error connecting to Ollama: {str(e)}")

# Simple chat interface for testing
st.header("2. Test Ollama Chat")

model = st.selectbox(
    "Select a model to test",
    ["mistral:latest", "deepseek-r1:1.5b", "llama3.3:latest"]
)

system_message = st.text_area(
    "System message (optional)",
    "You are ASHA, a helpful career guidance assistant for women professionals."
)

user_input = st.text_area("Type your message here")

if st.button("Send"):
    with st.spinner("Generating response..."):
        st.write("### Message:")
        st.write(user_input)
        
        st.write("### Response:")
        response = query_ollama(user_input, model=model, system=system_message)
        st.write(response)

# Test intent classification
st.header("3. Test Intent Classification")

intent_input = st.text_area("Enter text to classify intent", "I need help with my resume")

if st.button("Classify Intent"):
    with st.spinner("Classifying..."):
        system_prompt = """
        You are an intent classifier for a career guidance chatbot for women.
        Classify the following text into one of these categories:
        - career_guidance
        - job_search
        - skill_development
        - interview_preparation
        - workplace_challenges
        - off_topic
        - inappropriate
        
        Respond with ONLY the category name and nothing else.
        """
        
        response = query_ollama(intent_input, model="deepseek-r1:1.5b", system=system_prompt)
        
        st.write("### Classified Intent:")
        st.success(response.strip())

# Show useful information
st.header("Troubleshooting Info")
st.write("If you're experiencing issues, check the following:")

st.markdown("""
1. Make sure Ollama is running: `ollama serve`
2. Check model availability: `ollama list`
3. Verify connectivity: `curl http://localhost:11434/api/tags`
4. Check for firewall or proxy issues
5. Ensure there's enough memory for model inference
""")