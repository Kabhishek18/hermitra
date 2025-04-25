# asha/app.py
import streamlit as st
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules
from engines.career_guidance import CareerGuidanceEngine
from engines.simple_career_guidance import SimpleCareerGuidanceEngine
from engines.session_recommender import SessionRecommender
from components.chat_interface import ChatInterface
from components.session_browser import SessionBrowser
from utils.db import save_chat_history
import config

def main():
    st.set_page_config(
        page_title=config.APP_NAME,
        page_icon=config.APP_ICON,
        layout="wide"
    )
    
    # Initialize engines
    if 'career_engine' not in st.session_state:
        st.session_state.career_engine = SimpleCareerGuidanceEngine()
    
    if 'session_recommender' not in st.session_state:
        st.session_state.session_recommender = SessionRecommender()
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "demo_user"  # In production, use actual user authentication
    
    # App title and description
    st.title("ASHA: Career Guidance Assistant")
    st.markdown("""
    Welcome to ASHA, your personal career guidance assistant specialized in helping women professionals.
    Ask questions about career development, job search, interviews, leadership, and more!
    """)
    
    # Create columns for chat and recommendations
    col1, col2 = st.columns([3, 1])
    
    # Render chat interface
    with col1:
        chat_interface = ChatInterface(st.session_state.career_engine)
        chat_interface.render()
    
    # Render session browser
    # with col2:
    #     session_browser = SessionBrowser(st.session_state.session_recommender)
    #     # Get the most recent user query from chat history if available
    #     latest_query = None
    #     if 'chat_history' in st.session_state and st.session_state.chat_history:
    #         user_messages = [msg for msg in st.session_state.chat_history if msg['role'] == 'user']
    #         if user_messages:
    #             latest_query = user_messages[-1]['content']
        
    #     session_browser.render(latest_query)
    
    # Save chat history to database
    if 'chat_history' in st.session_state and st.session_state.chat_history:
        # Only save if we have at least one complete exchange
        if len(st.session_state.chat_history) >= 2:
            last_user_msg = None
            last_assistant_msg = None
            
            for msg in reversed(st.session_state.chat_history):
                if msg['role'] == 'user' and not last_user_msg:
                    last_user_msg = msg
                elif msg['role'] == 'assistant' and not last_assistant_msg:
                    last_assistant_msg = msg
                
                if last_user_msg and last_assistant_msg:
                    break
            
            if last_user_msg and last_assistant_msg:
                save_chat_history(st.session_state.user_id, {
                    'query': last_user_msg['content'],
                    'response': last_assistant_msg['content'],
                    'timestamp': datetime.now()
                })

if __name__ == "__main__":
    main()