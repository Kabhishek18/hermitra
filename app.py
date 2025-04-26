# asha/app.py
import streamlit as st
import sys
import os
from datetime import datetime
import time
import traceback

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules
from engines.career_guidance import CareerGuidanceEngine
from engines.simple_career_guidance import SimpleCareerGuidanceEngine
from components.chat_interface import ChatInterface
from components.enhanced_session_search import EnhancedSessionSearch
from utils.db import save_chat_history
from utils.ollama import ollama_client
import config

# Create data directory if it doesn't exist
os.makedirs(config.DATA_DIR, exist_ok=True)

# Enable debug logging
DEBUG_MODE = True

def debug_log(message):
    """Log debug messages if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"[APP DEBUG] {message}")

@st.cache_resource
def load_career_engine():
    """Load the career guidance engine with caching"""
    debug_log("Initializing career guidance engine")
    try:
        # Check if Ollama is available
        if ollama_client.is_available():
            debug_log("Ollama service is available, using CareerGuidanceEngine")
            engine = CareerGuidanceEngine()
            return engine
        else:
            debug_log("Ollama service is not available, using SimpleCareerGuidanceEngine")
            st.warning("Ollama service is not available. Using simplified responses.")
            return SimpleCareerGuidanceEngine()
    except Exception as e:
        debug_log(f"Error initializing career engine: {e}")
        traceback.print_exc()
        st.error("Error initializing career guidance engine. Using simplified responses.")
        return SimpleCareerGuidanceEngine()

@st.cache_resource
def load_session_search():
    """Load the session search with caching"""
    debug_log("Initializing enhanced session search")
    try:
        search = EnhancedSessionSearch()
        # Check if sessions were loaded
        if hasattr(search, 'sessions'):
            debug_log(f"Session search initialized with {len(search.sessions)} sessions")
        else:
            debug_log("Session search initialized but no sessions found")
        return search
    except Exception as e:
        debug_log(f"Error initializing session search: {e}")
        traceback.print_exc()
        st.error("Error initializing session search. Some features may not work properly.")
        return None

def main():
    # Set configuration to reduce memory usage
    st.set_page_config(
        page_title=config.APP_NAME,
        page_icon=config.APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed"  # Save screen space
    )
    
    # Add custom CSS to reduce whitespace and optimize UI
    st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 1rem}
        .st-emotion-cache-1kyxreq {margin-top: -60px}
        .st-emotion-cache-r421ms {padding-top: 0.5rem}
        div.stButton > button {width: 100%}
        
        /* Styling for session cards */
        .session-card {
            border: 1px solid #f0f0f0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
        }
        .session-card h4 {
            margin-top: 0;
        }
        .session-card:hover {
            border-color: #e0e0e0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Debug sidebar
    if DEBUG_MODE:
        with st.sidebar:
            st.title("Debug Controls")
            if st.button("Clear Chat History"):
                if 'chat_history' in st.session_state:
                    st.session_state.chat_history = []
                if 'last_query' in st.session_state:
                    st.session_state.last_query = ""
                st.session_state.is_processing = False
                st.session_state.retry_count = 0
                st.success("Chat history cleared!")
                
            if st.button("Reset Session State"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Session state reset!")
                st.rerun()
    
    # Initialize engines using cached functions
    try:
        debug_log("Loading career engine and session search")
        career_engine = load_career_engine()
        session_search = load_session_search()
        
        if 'user_id' not in st.session_state:
            st.session_state.user_id = "demo_user"  # In production, use actual user authentication
        
        if 'last_save_time' not in st.session_state:
            st.session_state.last_save_time = time.time()
        
        # App title and description - kept minimal
        st.title("ASHA: Career Guidance Assistant")
        
        # Create tabs for different features
        tab1, tab2 = st.tabs(["Career Chat", "Advanced Session Search"])
        
        # Tab 1: Main chat interface with integrated session search
        with tab1:
            st.markdown(
                "Your AI career guidance assistant for women professionals. Ask about career development, "
                "interviews, leadership, or find relevant sessions - all in one conversation."
            )
            
            # Create a single-column layout focusing on the chat experience
            chat_interface = ChatInterface(career_engine)
            chat_interface.render()
        
        # Tab 2: Advanced session search
        with tab2:
            st.markdown(
                "Search for sessions by title, host, description, or date. "
                "Use this feature to find specific sessions in the database."
            )
            if session_search:
                session_search.render()
            else:
                st.error("Session search is not available. Please restart the application.")
        
        # Save chat history periodically instead of after every message
        current_time = time.time()
        if ('chat_history' in st.session_state and 
            st.session_state.chat_history and 
            current_time - st.session_state.last_save_time > 30):  # Save every 30 seconds
            
            debug_log("Saving chat history to database")
            # Find last complete exchange
            if len(st.session_state.chat_history) >= 2:
                # Find the last user and assistant message pair
                user_msgs = [(i, msg) for i, msg in enumerate(st.session_state.chat_history) if msg['role'] == 'user']
                assistant_msgs = [(i, msg) for i, msg in enumerate(st.session_state.chat_history) if msg['role'] == 'assistant']
                
                if user_msgs and assistant_msgs:
                    last_user_idx, last_user_msg = user_msgs[-1]
                    for idx, msg in reversed(assistant_msgs):
                        if idx > last_user_idx:
                            try:
                                save_chat_history(st.session_state.user_id, {
                                    'query': last_user_msg['content'],
                                    'response': msg['content'],
                                    'timestamp': datetime.now()
                                })
                                debug_log("Chat history saved successfully")
                            except Exception as e:
                                debug_log(f"Error saving chat history: {e}")
                            break
            
            st.session_state.last_save_time = current_time
            
    except Exception as e:
        debug_log(f"Error in main app: {e}")
        traceback.print_exc()
        st.error("An error occurred in the application. Please try refreshing the page or contact support.")

if __name__ == "__main__":
    main()