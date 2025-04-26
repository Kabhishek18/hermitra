# asha/components/enhanced_chat_interface.py
import streamlit as st
from datetime import datetime
import re

class EnhancedChatInterface:
    def __init__(self, career_engine):
        self.career_engine = career_engine
    
    def _format_session_links(self, message):
        """Convert session URLs to clickable links and highlight session titles"""
        # First, wrap any URLs in proper markdown links
        url_pattern = r'(https?://[^\s]+)'
        message = re.sub(url_pattern, r'[\1](\1)', message)
        
        # Then, highlight session titles with bold formatting
        title_pattern = r'\*\*([^*]+?)\*\*'
        message = re.sub(title_pattern, r'**\1**', message)
        
        return message
    
    def _detect_session_content(self, message):
        """Detect if a message contains session information and format it accordingly"""
        # Check if this looks like a session response
        if "**1." in message and ("Host:" in message or "📅 Date:" in message):
            return True
        if "I found" in message and "sessions matching your criteria" in message:
            return True
        if "You might also be interested in these sessions" in message:
            return True
        return False
    
    def render(self):
        """Render the enhanced chat interface with optimizations"""
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
        
        # Display chat history
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"**You**: {message['content']}")
                else:
                    # Format the assistant's response
                    content = message['content']
                    
                    # Check if this contains session information
                    has_session_info = self._detect_session_content(content)
                    
                    if has_session_info:
                        # Format URLs and session titles
                        formatted_content = self._format_session_links(content)
                        
                        # Create a more visually distinct display for session info
                        st.markdown(f"**ASHA**:")
                        st.markdown(formatted_content)
                    else:
                        # Regular message display
                        st.markdown(f"**ASHA**: {content}")
        
        # Chat input - using form to prevent double submissions
        with st.form(key="chat_form", clear_on_submit=True):
            st.text_input(
                "Ask ASHA about your career or sessions...", 
                key="user_input",
                placeholder="e.g., 'Find leadership sessions' or 'How can I prepare for a salary negotiation?'"
            )
            col1, col2 = st.columns([1, 3])
            with col1:
                submit_button = st.form_submit_button("Send", on_click=handle_submit, use_container_width=True)
            with col2:
                # Add quick session-related suggestions
                st.markdown("""
                <style>
                .suggestion-btn {
                    display: inline-block; 
                    margin-right: 8px;
                    font-size: 0.8em; 
                    color: #505050;
                    background: #f0f0f0; 
                    border: none;
                    border-radius: 15px;
                    padding: 2px 10px;
                    cursor: pointer;
                }
                .suggestion-btn:hover {
                    background: #e0e0e0;
                }
                </style>
                <div style="margin-top: 8px;">
                <span onclick="document.querySelector('[data-testid=\\'stFormTextInput\\'] input').value='Find leadership development sessions'; document.querySelector('[data-testid=\\'stForm\\'] button').click();" class="suggestion-btn">Leadership sessions</span>
                <span onclick="document.querySelector('[data-testid=\\'stFormTextInput\\'] input').value='Sessions by Marissa'; document.querySelector('[data-testid=\\'stForm\\'] button').click();" class="suggestion-btn">By Marissa</span>
                <span onclick="document.querySelector('[data-testid=\\'stFormTextInput\\'] input').value='Sessions in January 2023'; document.querySelector('[data-testid=\\'stForm\\'] button').click();" class="suggestion-btn">Jan 2023 sessions</span>
                </div>
                """, unsafe_allow_html=True)
            
        # Add a subtle hint for session search
        st.markdown("""
        <div style="font-size: 0.8em; color: #888; margin-top: 5px;">
        💡 <i>You can ask about specific sessions or get career guidance - both are available in this chat!</i>
        </div>
        """, unsafe_allow_html=True)