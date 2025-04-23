import streamlit as st
import requests
import json
import os
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="ASHA - Career Guidance Assistant",
    page_icon="👩‍💼",
    layout="centered"
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def log_interaction(user_query, bot_response):
    """Log each interaction for later analysis."""
    log_file = f"logs/asha_interactions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "bot_response": bot_response,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def get_asha_response(user_message):
    """Get response from ASHA BOT via Ollama API."""
    # Add context to ensure consistent responses
    prompt = f"""You are ASHA, a career guidance assistant for women professionals.
You know about a session titled "Online vs in-person group discussion" hosted by Udhaya C.
This session discusses pros and cons of online vs in-person formats.

The user asks: {user_message}

Remember to provide specific, actionable advice and sign off with "ASHA - Advancing careers, empowering professionals."
"""
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "asha-bot",
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            bot_response = response.json()["response"]
            
            # Ensure response has signature
            if not bot_response.endswith("ASHA - Advancing careers, empowering professionals."):
                bot_response += "\n\nASHA - Advancing careers, empowering professionals."
            
            # Log the interaction
            log_interaction(user_message, bot_response)
            
            return bot_response
        else:
            return f"I'm sorry, I encountered an error (Status code: {response.status_code}). Please try again later. ASHA - Advancing careers, empowering professionals."
    
    except Exception as e:
        return f"I'm sorry, I encountered an error: {str(e)}. Please try again later. ASHA - Advancing careers, empowering professionals."

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem !important;
        color: #4a3b8b;
    }
    .sub-header {
        font-size: 1.2rem !important;
        color: #666;
    }
    .stTextInput>div>div>input {
        border-radius: 20px;
    }
    .user-bubble {
        background-color: #e1f5fe;
        color: #01579b;
        padding: 15px;
        border-radius: 20px 20px 5px 20px;
        margin-bottom: 10px;
    }
    .bot-bubble {
        background-color: #f0f0f0;
        color: #333;
        padding: 15px;
        border-radius: 20px 20px 20px 5px;
        margin-bottom: 10px;
    }
    .signature {
        font-style: italic;
        font-size: 0.8em;
        opacity: 0.8;
    }
    .suggestion-chip {
        display: inline-block;
        background-color: #e8eaf6;
        padding: 5px 15px;
        border-radius: 18px;
        margin: 5px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.markdown('<p class="main-header">ASHA - Career Guidance Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Advancing careers, empowering professionals</p>', unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm ASHA (Advancement Support & Help Assistant), your specialized assistant for career guidance. I can help you with professional development, recommend sessions, and provide career advice tailored for women professionals. How can I assist you today?"}
    ]

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        # Format bot message to separate signature
        content = message["content"]
        if "ASHA - Advancing careers, empowering professionals." in content:
            main_content = content.replace("ASHA - Advancing careers, empowering professionals.", "").strip()
            st.markdown(f'<div class="bot-bubble">{main_content}<div class="signature">ASHA - Advancing careers, empowering professionals.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bot-bubble">{content}</div>', unsafe_allow_html=True)

# Suggestion chips (clickable)
st.markdown('<div>', unsafe_allow_html=True)
suggestions = [
    "Tell me about the Online vs in-person session", 
    "How can I improve my leadership skills?", 
    "Professional development recommendations"
]

if st.session_state.messages[-1]["role"] == "assistant":
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, key=f"suggestion_{i}"):
            st.session_state.messages.append({"role": "user", "content": suggestion})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestion)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.experimental_rerun()

# User input
user_input = st.text_input("Your question:", key="user_input", placeholder="Type your question here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("ASHA is thinking..."):
        response = get_asha_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    st.experimental_rerun()

# Add additional information in sidebar
with st.sidebar:
    st.title("About ASHA")
    st.write("ASHA is a specialized AI assistant focused on providing tailored career guidance for women professionals.")
    
    st.subheader("Key Capabilities")
    st.write("• Career guidance specific to women")
    st.write("• Session recommendations")
    st.write("• Leadership development advice")
    st.write("• Networking strategies")
    
    st.subheader("Featured Session")
    st.write("**Online vs in-person group discussion**")
    st.write("Host: Udhaya C")
    st.write("Topic: Pros and cons of different discussion formats")
    
    # Optional feedback mechanism
    st.subheader("Feedback")
    if st.button("👍 Helpful"):
        st.success("Thank you for your feedback!")
    if st.button("👎 Not Helpful"):
        st.error("We'll work to improve our responses.")
