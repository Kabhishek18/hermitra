# asha/components/chat_interface.py
import streamlit as st
from datetime import datetime

class ChatInterface:
    def __init__(self, career_engine):
        self.career_engine = career_engine
    
    def render(self):
        """Render the chat interface with optimizations"""
        st.subheader("Career Guidance Chat")
        
        # Initialize session state variables if not present
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'is_processing' not in st.session_state:
            st.session_state.is_processing = False
        
        # Cache for checking if we need to update the display
        if 'last_history_length' not in st.session_state:
            st.session_state.last_history_length = 0
        
        # Function to handle form submission - prevents double submissions
        def handle_submit():
            query = st.session_state.user_input
            if query and not st.session_state.is_processing:
                st.session_state.is_processing = True
                st.session_state.user_input = ""  # Clear input
                
                # Add user message to history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': query,
                    'timestamp': datetime.now()
                })
                
                # Update UI to show user message immediately
                st.rerun()
        
        # Display chat container
        chat_container = st.container()
        
        # Process any pending message
        if st.session_state.is_processing and st.session_state.chat_history:
            last_msg = st.session_state.chat_history[-1]
            if last_msg['role'] == 'user':
                with st.spinner("ASHA is thinking..."):
                    # Generate response
                    response = self.career_engine.process_query(last_msg['content'])
                
                # Add assistant message to history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response,
                    'timestamp': datetime.now()
                })
                
                # Clear processing flag
                st.session_state.is_processing = False
                
                # Update UI with new response
                st.rerun()
        
        # Display chat history if it changed
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**You**: {message['content']}")
                else:
                    st.markdown(f"**ASHA**: {message['content']}")
        
        # Chat input - using form to prevent double submissions
        with st.form(key="chat_form", clear_on_submit=True):
            st.text_input(
                "Ask ASHA about your career...", 
                key="user_input"
            )
            submit_button = st.form_submit_button("Send", on_click=handle_submit)
            
            # Note: the on_click function above will handle the submission logic