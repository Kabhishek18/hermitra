import streamlit as st
import requests
import json
import os
import random
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="ASHA - Career Guidance Assistant",
    page_icon="👩‍💼",
    layout="centered"
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Load sessions data
@st.cache_data
def load_sessions():
    try:
        with open("../data/sessions.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading sessions: {e}")
        return []

sessions = load_sessions()

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

def find_relevant_sessions(query, num_sessions=2):
    """Find sessions relevant to the user's query."""
    query_terms = query.lower().split()
    
    # Simple relevance scoring
    session_scores = []
    for session in sessions:
        score = 0
        
        # Check title
        for term in query_terms:
            if term in session["title"].lower():
                score += 3
                
        # Check description
        for term in query_terms:
            if term in session["description"].lower():
                score += 2
                
        # Check topics
        for topic in session.get("topics", []):
            for term in query_terms:
                if term in topic.lower():
                    score += 2
        
        if score > 0:
            session_scores.append((session, score))
    
    # Sort by relevance and return top sessions
    session_scores.sort(key=lambda x: x[1], reverse=True)
    return [session for session, score in session_scores[:num_sessions]]

def format_sessions_for_prompt(relevant_sessions):
    """Format session information for inclusion in the prompt."""
    if not relevant_sessions:
        return ""
        
    sessions_text = "Here are some relevant sessions you can mention:\n\n"
    
    for session in relevant_sessions:
        sessions_text += f"Session: {session['title']}\n"
        sessions_text += f"Description: {session['description']}\n"
        sessions_text += f"Host: {session['host']} ({session['host_headline']})\n"
        sessions_text += f"Format: {session['format']}\n"
        sessions_text += f"Topics: {', '.join(session['topics'])}\n\n"
    
    return sessions_text

def get_asha_response(user_message):
    """Get response from ASHA BOT via Ollama API."""
    # Find relevant sessions
    relevant_sessions = find_relevant_sessions(user_message)
    sessions_text = format_sessions_for_prompt(relevant_sessions)
    
    # Add context to ensure consistent responses
    prompt = f"""You are ASHA, a career guidance assistant for women professionals.

{sessions_text}

The user asks: {user_message}

Remember to:
1. Provide specific, actionable advice for career development
2. If the user's question relates to any of the sessions above, recommend those specific sessions
3. Focus on career guidance for women professionals
4. Keep your responses concise and practical
5. Sign off with "ASHA - Advancing careers, empowering professionals."
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
    .session-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #eee;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .session-title {
        font-weight: bold;
        color: #4a3b8b;
    }
    .session-host {
        font-style: italic;
        color: #666;
    }
    .topic-tag {
        background-color: #e8eaf6;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-right: 5px;
        display: inline-block;
        margin-bottom: 5px;
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
chat_container = st.container()
with chat_container:
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
suggestions = [
    "Recommend leadership sessions", 
    "How to negotiate a salary increase?", 
    "Networking strategies for women"
]

if st.session_state.messages[-1]["role"] == "assistant":
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, key=f"suggestion_{i}"):
            st.session_state.messages.append({"role": "user", "content": suggestion})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestion)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()  # Changed from st.experimental_rerun() to st.rerun()

# User input
user_input = st.text_input("Your question:", key="user_input", placeholder="Type your question here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("ASHA is thinking..."):
        response = get_asha_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()  # Changed from st.experimental_rerun() to st.rerun()

# Add additional information in sidebar
with st.sidebar:
    st.title("About ASHA")
    st.write("ASHA is a specialized AI assistant focused on providing tailored career guidance for women professionals.")
    
    st.subheader("Key Capabilities")
    st.write("• Career guidance specific to women")
    st.write("• Session recommendations")
    st.write("• Leadership development advice")
    st.write("• Networking strategies")
    
    # Featured sessions section
    st.subheader("Featured Sessions")
    if sessions:
        # Display 2 random sessions
        featured_sessions = random.sample(sessions, min(2, len(sessions)))
        for session in featured_sessions:
            st.markdown(f"""
            <div class="session-card">
                <div class="session-title">{session['title']}</div>
                <div class="session-host">Hosted by: {session['host']}</div>
                <p>{session['description'][:100]}...</p>
                <div>
                    {"".join(f'<span class="topic-tag">{topic}</span>' for topic in session['topics'][:3])}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Optional feedback mechanism
    st.subheader("Feedback")
    cols = st.columns(2)
    if cols[0].button("👍 Helpful"):
        st.success("Thank you for your feedback!")
    if cols[1].button("👎 Not Helpful"):
        feedback = st.text_area("What can we improve?", "")
        if st.button("Submit Feedback"):
            log_file = "logs/feedback.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "feedback": feedback,
                    "last_message": st.session_state.messages[-1]["content"] if st.session_state.messages else ""
                }) + "\n")
            st.success("Thank you for your feedback! We'll use it to improve ASHA.")