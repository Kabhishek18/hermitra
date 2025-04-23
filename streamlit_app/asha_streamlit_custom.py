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

# Load and process the session JSON file
@st.cache_data
def load_session_data():
    try:
        file_path = "../data/raw/sessions.json"
        if not os.path.exists(file_path):
            st.error(f"File not found: {file_path}")
            return None
            
        with open(file_path, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        st.error(f"Error loading session data: {e}")
        return None

def extract_session_info(data):
    """Extract usable session information"""
    session_title = data.get("session_title", "Untitled Session")
    
    # Extract description
    description = "No description available"
    desc_raw = data.get("description", "{}")
    try:
        desc_json = json.loads(desc_raw)
        if "root" in desc_json and "children" in desc_json["root"]:
            for child in desc_json["root"]["children"]:
                if "children" in child:
                    for text_block in child["children"]:
                        if "text" in text_block:
                            description = text_block["text"]
    except:
        description = desc_raw
    
    # Extract host
    host = "Unknown host"
    hosts = data.get("host_user", [])
    if hosts and len(hosts) > 0:
        host = hosts[0].get("username", "Unknown host")
    
    return {
        "title": session_title,
        "description": description,
        "host": host
    }

def get_asha_response(user_message, session_info):
    """Get response from ASHA BOT via Ollama API"""
    # Create prompt with session context
    prompt = f"""You are ASHA, a career guidance assistant for women professionals.

Session information:
- Title: {session_info['title']}
- Description: {session_info['description']}
- Host: {session_info['host']}

The user asks: {user_message}

Remember to:
1. Provide specific, actionable advice for career development
2. Recommend the session when relevant to the user's question
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
            with open(f"logs/interactions_{datetime.now().strftime('%Y%m%d')}.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "user_query": user_message,
                    "bot_response": bot_response
                }) + "\n")
            
            return bot_response
        else:
            return f"I'm sorry, I encountered an error. Please try again later. ASHA - Advancing careers, empowering professionals."
    
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
</style>
""", unsafe_allow_html=True)

# App header
st.markdown('<p class="main-header">ASHA - Career Guidance Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Advancing careers, empowering professionals</p>', unsafe_allow_html=True)

# Load session data
session_data = load_session_data()
if session_data:
    session_info = extract_session_info(session_data)
    st.sidebar.success(f"Session loaded: {session_info['title']}")
else:
    st.sidebar.error("No session data found")
    session_info = {
        "title": "Online vs in-person group discussion",
        "description": "Pros and cons of online and in-person group discussions",
        "host": "Udhaya C"
    }

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

# Suggestion chips
suggestions = [
    "Tell me about this session", 
    "How can I improve my leadership skills?", 
    "Networking strategies for women"
]

if st.session_state.messages[-1]["role"] == "assistant":
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, key=f"suggestion_{i}"):
            st.session_state.messages.append({"role": "user", "content": suggestion})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestion, session_info)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.experimental_rerun()

# User input
user_input = st.text_input("Your question:", key="user_input", placeholder="Type your question here...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("ASHA is thinking..."):
        response = get_asha_response(user_input, session_info)
        st.session_state.messages.append({"role": "assistant", "content": response})
    st.experimental_rerun()

# Sidebar with info about ASHA
with st.sidebar:
    st.title("About ASHA")
    st.write("ASHA is a specialized AI assistant focused on providing tailored career guidance for women professionals.")
    
    st.subheader("Key Capabilities")
    st.write("• Career guidance specific to women")
    st.write("• Session recommendations")
    st.write("• Leadership development advice")
    st.write("• Networking strategies")
    
    # Session information
    st.subheader("Current Session")
    st.markdown(f"""
    **Title:** {session_info['title']}
    
    **Host:** {session_info['host']}
    
    **Description:** {session_info['description']}
    """)
    
    # Feedback mechanism
    st.subheader("Feedback")
    if st.button("👍 Helpful"):
        st.success("Thank you for your feedback!")
    if st.button("👎 Not Helpful"):
        st.error("We'll work to improve our responses.")