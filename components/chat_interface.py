# asha/components/chat_interface.py
import streamlit as st
from datetime import datetime

class ChatInterface:
    def __init__(self, career_engine):
        self.career_engine = career_engine
    
    def render(self):
        """Render the chat interface"""
        st.subheader("Career Guidance Chat")
        
        # Initialize chat history in session state if not present
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Display chat container
        chat_container = st.container()
        
        # Chat input
        user_query = st.text_input("Ask ASHA about your career...", key="user_input")
        
        # Process user query
        if user_query:
            # Add user message to history
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_query,
                'timestamp': datetime.now()
            })
            
            # Generate response with spinner
            with st.spinner("ASHA is thinking... This may take a moment for AI-related queries"):
                response = self.career_engine.process_query(user_query)

            
            # Add assistant message to history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now()
            })
            
            # Clear input
            st.rerun()
        
        # Display chat history
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**You**: {message['content']}")
                else:
                    st.markdown(f"**ASHA**: {message['content']}")