# asha/components/chat_interface.py
import streamlit as st
from datetime import datetime
import re
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ChatInterface:
    def __init__(self, career_engine, session_recommender=None):
        self.career_engine = career_engine
        self.session_recommender = session_recommender
    
    def _format_session_links(self, message):
        """Convert session URLs to clickable links and highlight session titles"""
        # Wrap URLs in proper markdown links
        url_pattern = r'(https?://[^\s]+)'
        message = re.sub(url_pattern, r'[\1](\1)', message)
        
        # Highlight session titles with bold formatting
        title_pattern = r'\*\*([^*]+?)\*\*'
        message = re.sub(title_pattern, r'**\1**', message)
        
        return message
    
    def _detect_session_content(self, message):
        """Detect if a message contains session information"""
        session_indicators = [
            "session", "sessions", "host", 
            "📅 Date:", "👤 Host:", "⏱️ Duration:", 
            "matching your criteria", "scheduled for",
            "found", "might interest you"
        ]
        
        for indicator in session_indicators:
            if indicator.lower() in message.lower():
                return True
                
        return False
    
    def _process_session_search(self, query):
        """Process a session search query if session recommender is available"""
        if not self.session_recommender:
            return None
            
        # Extract search parameters
        search_params = self.session_recommender.extract_search_params_from_query(query)
        
        if not search_params:
            # If no parameters detected, use the query for vector search
            recommended_sessions = self.session_recommender.recommend_sessions(query, top_k=5)
        else:
            # Perform filtered search
            recommended_sessions = self.session_recommender.search_sessions(search_params)
        
        # Format the results
        if recommended_sessions:
            return self.session_recommender.format_session_recommendations(recommended_sessions, query)
        else:
            return "I couldn't find any sessions matching your criteria. Could you try a different search term or topic?"
    
    def render(self):
        """Render the chat interface with optimizations"""
        # Initialize session state variables if not present
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'is_processing' not in st.session_state:
            st.session_state.is_processing = False
            
        if 'last_query' not in st.session_state:
            st.session_state.last_query = ""
        
        # Function to handle form submission - prevents double submissions
        def handle_submit():
            query = st.session_state.user_input
            if query and not st.session_state.is_processing:
                st.session_state.is_processing = True
                st.session_state.last_query = query
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
                    query = last_msg['content']
                    
                    # Check if this is a session search query
                    if self.session_recommender and self.career_engine.is_session_search_query(query):
                        # Process as session search
                        response = self._process_session_search(query)
                    else:
                        # Process as regular career guidance query
                        response = self.career_engine.process_query(query)
                
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
                <span onclick="document.querySelector('[data-testid=\\'stFormTextInput\\'] input').value='How to prepare for a job interview?'; document.querySelector('[data-testid=\\'stForm\\'] button').click();" class="suggestion-btn">Interview tips</span>
                </div>
                """, unsafe_allow_html=True)
        
        # Add a subtle hint for session search
        st.markdown("""
        <div style="font-size: 0.8em; color: #888; margin-top: 5px;">
        💡 <i>You can ask about specific sessions or get career guidance - both are available in this chat!</i>
        </div>
        """, unsafe_allow_html=True)