# asha/app.py
import streamlit as st
import sys
import os
from datetime import datetime
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules
from engines.career_guidance import CareerGuidanceEngine
from engines.simple_career_guidance import SimpleCareerGuidanceEngine
from engines.session_recommender import SessionRecommender
from components.chat_interface import ChatInterface
from components.session_browser import SessionBrowser
from components.enhanced_session_search import EnhancedSessionSearch
from utils.db import save_chat_history
from utils.ollama import ollama_client
import config

# Create data directory if it doesn't exist
os.makedirs(config.DATA_DIR, exist_ok=True)

@st.cache_resource
def load_career_engine():
    """Load the career guidance engine with caching"""
    # Check if Ollama is available
    if ollama_client.is_available():
        engine = CareerGuidanceEngine()
        return engine
    else:
        st.warning("Ollama service is not available. Using simplified responses.")
        return SimpleCareerGuidanceEngine()

@st.cache_resource
def load_session_recommender():
    """Load the session recommender with caching"""
    return SessionRecommender()

@st.cache_resource
def load_session_search():
    """Load the session search with caching"""
    return EnhancedSessionSearch()

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
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize engines using cached functions
    career_engine = load_career_engine()
    session_recommender = load_session_recommender()
    session_search = load_session_search()
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "demo_user"  # In production, use actual user authentication
    
    if 'last_save_time' not in st.session_state:
        st.session_state.last_save_time = time.time()
    
    # App title and description - kept minimal
    st.title("ASHA: Career Guidance Assistant")
    
    # Create tabs for different features
    tab1, tab2 = st.tabs(["Career Chat", "Search Sessions"])
    
    # Tab 1: Main chat interface
    with tab1:
        st.markdown(
            "Your AI career guidance assistant for women professionals. Ask about career development, "
            "interviews, leadership, and more."
        )
        
        # Create columns for chat and recommendations with responsive layout
        col1, col2 = st.columns([3, 1])
        
        # Render chat interface in main column
        with col1:
            chat_interface = ChatInterface(career_engine)
            chat_interface.render()
        
        # Render session browser in second column
        with col2:
            session_browser = SessionBrowser(session_recommender)
            latest_query = None
            if 'chat_history' in st.session_state and st.session_state.chat_history:
                user_messages = [msg for msg in st.session_state.chat_history if msg['role'] == 'user']
                if user_messages:
                    latest_query = user_messages[-1]['content']
            session_browser.render(latest_query)
    
    # Tab 2: Session search
    with tab2:
        st.markdown(
            "Search for sessions by title, host, description, or date. "
            "Use this feature to find specific sessions in the database."
        )
        session_search.render()
    
    # Save chat history periodically instead of after every message
    current_time = time.time()
    if ('chat_history' in st.session_state and 
        st.session_state.chat_history and 
        current_time - st.session_state.last_save_time > 30):  # Save every 30 seconds
        
        # Find last complete exchange
        if len(st.session_state.chat_history) >= 2:
            # Find the last user and assistant message pair
            user_msgs = [(i, msg) for i, msg in enumerate(st.session_state.chat_history) if msg['role'] == 'user']
            assistant_msgs = [(i, msg) for i, msg in enumerate(st.session_state.chat_history) if msg['role'] == 'assistant']
            
            if user_msgs and assistant_msgs:
                last_user_idx, last_user_msg = user_msgs[-1]
                for idx, msg in reversed(assistant_msgs):
                    if idx > last_user_idx:
                        save_chat_history(st.session_state.user_id, {
                            'query': last_user_msg['content'],
                            'response': msg['content'],
                            'timestamp': datetime.now()
                        })
                        break
        
        st.session_state.last_save_time = current_time

if __name__ == "__main__":
    main()