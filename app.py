# asha/app.py
import streamlit as st
import sys
import os
import time
from datetime import datetime
import traceback

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules
from engines.career_guidance import CareerGuidanceEngine  # Use consolidated version
from engines.session_recommender import SessionRecommender  # Use consolidated version
from components.chat_interface import ChatInterface
from components.session_browser import SessionBrowser 
from utils.db import save_chat_history
from utils.ollama import ollama_client
import config

# Create data directory if it doesn't exist
os.makedirs(config.DATA_DIR, exist_ok=True)

@st.cache_resource
def load_career_engine():
    """Load the career guidance engine with caching"""
    print("Initializing career guidance engine")
    try:
        # Check if Ollama is available
        if ollama_client.is_available():
            print("Ollama service is available")
            engine = CareerGuidanceEngine()
            return engine
        else:
            print("Ollama service is not available")
            st.warning("Ollama service is not available. Some functionality may be limited.")
            return CareerGuidanceEngine()  # Still return the engine, it will handle errors gracefully
    except Exception as e:
        print(f"Error initializing career engine: {e}")
        traceback.print_exc()
        st.error("Error initializing career guidance engine. Some functionality may be limited.")
        return CareerGuidanceEngine()  # Return basic engine

@st.cache_resource
def load_session_recommender():
    """Load the session recommender with caching"""
    print("Initializing session recommender")
    try:
        recommender = SessionRecommender()
        return recommender
    except Exception as e:
        print(f"Error initializing session recommender: {e}")
        traceback.print_exc()
        st.error("Error initializing session recommender. Session search may not work properly.")
        return None

def main():
    # Set configuration
    st.set_page_config(
        page_title=config.APP_NAME,
        page_icon=config.APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Add custom CSS
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
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize engines
    try:
        career_engine = load_career_engine()
        session_recommender = load_session_recommender()
        
        if 'user_id' not in st.session_state:
            st.session_state.user_id = "demo_user"  # In production, use actual user authentication
        
        if 'last_save_time' not in st.session_state:
            st.session_state.last_save_time = time.time()
        
        # App title and description
        st.title("ASHA: Career Guidance Assistant")
        
        # Create tabs for different features
        tab1, tab2 = st.tabs(["Career Chat", "About ASHA"])
        
        # Tab 1: Main chat interface with integrated session search
        with tab1:
            st.markdown(
                "Your AI career guidance assistant for women professionals. Ask about career development, "
                "interviews, leadership, or find relevant sessions - all in one conversation."
            )
            
            # Create chat interface
            chat_interface = ChatInterface(career_engine, session_recommender)
            chat_interface.render()
        
        # Tab 2: About ASHA
        with tab2:
            st.markdown("""
            ## About ASHA
            
            ASHA is an AI-powered career guidance chatbot specifically designed for women professionals. 
            The solution combines personalized career guidance with community engagement features through a session recommendation system.
            
            ### Key Features
            
            #### Personalized Career Guidance
            - Resume review and optimization recommendations
            - Interview preparation and confidence-building techniques
            - Salary negotiation strategies specifically for women
            - Career transition pathways with skills gap analysis
            - Leadership development advice for women professionals
            
            #### Session Recommendation System
            - Integration with women's professional community events
            - Personalized recommendations based on career goals and interests
            - Access to recorded sessions and learning resources
            - Connection to mentorship opportunities and networking events
            
            ### Getting Started
            
            1. **Ask career questions** - Get guidance on interviews, promotions, leadership development, and more
            2. **Find relevant sessions** - Just ask "Find sessions about leadership" or "Sessions by [host name]"
            3. **Get recommendations** - ASHA will recommend relevant sessions based on your career interests
            
            ### Technical Information
            
            ASHA runs locally on your machine using:
            - Ollama with the Mistral LLM model
            - MongoDB for session data
            - FAISS for semantic search
            - Streamlit for the user interface
            """)
        
        # Save chat history periodically
        current_time = time.time()
        if ('chat_history' in st.session_state and 
            st.session_state.chat_history and 
            current_time - st.session_state.last_save_time > 30):  # Save every 30 seconds
            
            print("Saving chat history to database")
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
                                print("Chat history saved successfully")
                            except Exception as e:
                                print(f"Error saving chat history: {e}")
                            break
            
            st.session_state.last_save_time = current_time
            
    except Exception as e:
        print(f"Error in main app: {e}")
        traceback.print_exc()
        st.error("An error occurred in the application. Please try refreshing the page or contact support.")

if __name__ == "__main__":
    main()