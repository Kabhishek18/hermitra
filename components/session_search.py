# asha/components/session_search.py
import streamlit as st
from utils.db import get_all_sessions
import re

class SessionSearch:
    def __init__(self):
        # Load sessions once during initialization
        self.sessions = get_all_sessions()
    
    def search_by_host(self, host_name):
        """Search for sessions by host name (case-insensitive partial match)"""
        if not host_name or not self.sessions:
            return []
        
        host_name_lower = host_name.lower()
        matching_sessions = []
        
        for session in self.sessions:
            # Check host users
            host_users = session.get('host_user', [])
            for host in host_users:
                username = host.get('username', '').lower()
                if host_name_lower in username:
                    matching_sessions.append(session)
                    break
        
        return matching_sessions
    
    def search_by_title(self, title_keywords):
        """Search for sessions by title keywords"""
        if not title_keywords or not self.sessions:
            return []
        
        title_lower = title_keywords.lower()
        matching_sessions = []
        
        for session in self.sessions:
            # Check title
            session_title = session.get('session_title', '').lower()
            if title_lower in session_title:
                matching_sessions.append(session)
        
        return matching_sessions
    
    def render(self):
        """Render a dedicated session search interface"""
        st.subheader("Session Search")
        
        # Search options
        search_option = st.radio(
            "Search by:",
            ["Host", "Title"],
            horizontal=True
        )
        
        # Search input
        if search_option == "Host":
            search_term = st.text_input("Enter host name:")
            if search_term:
                results = self.search_by_host(search_term)
                self._display_results(results, search_term, "host")
        else:  # Title
            search_term = st.text_input("Enter keywords in title:")
            if search_term:
                results = self.search_by_title(search_term)
                self._display_results(results, search_term, "title")
    
    def _display_results(self, results, search_term, search_type):
        """Display search results"""
        if results:
            st.success(f"Found {len(results)} sessions matching '{search_term}' in {search_type}")
            
            for session in results:
                title = session.get('session_title', 'Untitled Session')
                
                # Create expandable card for each session
                with st.expander(f"📅 {title}"):
                    # Host information
                    host_users = session.get('host_user', [])
                    if host_users and len(host_users) > 0:
                        host = host_users[0]
                        st.markdown(f"**Host**: {host.get('username', 'Unknown')}")
                    
                    # Duration
                    st.markdown(f"**Duration**: {session.get('duration', 'N/A')}")
                    
                    # Description (simplified)
                    description = session.get('description', '')
                    if isinstance(description, str) and description.strip().startswith('{'):
                        try:
                            st.markdown("**Description**: _Formatted content available_")
                        except:
                            st.markdown("**Description**: _Available_")
                    elif description:
                        st.markdown(f"**Description**: {str(description)[:100]}...")
                    
                    # Session URL
                    if 'external_url' in session and session['external_url']:
                        st.markdown(f"[Join Session]({session['external_url']})")
        else:
            st.warning(f"No sessions found with '{search_term}' in {search_type}")