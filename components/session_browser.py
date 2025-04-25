# asha/components/session_browser.py
import streamlit as st
from datetime import datetime
import time

class SessionBrowser:
    def __init__(self, session_recommender):
        self.session_recommender = session_recommender
        # Keep track of last query to avoid redundant searches
        self.last_query = None
        self.last_results = []
        self.last_query_time = 0
    
    def render(self, query=None):
        """Render session recommendations with performance optimizations"""
        st.subheader("Recommended Sessions")
        
        if not query:
            # If no query, display default message or recent sessions
            st.info("Ask a career question to get relevant session recommendations!")
            return
        
        # Check if we need to run a new search or can use cached results
        current_time = time.time()
        should_search = (
            query != self.last_query or  # Different query
            current_time - self.last_query_time > 300  # Cache expired (5 minutes)
        )
        
        # Only fetch new recommendations if needed
        if should_search:
            with st.spinner("Finding relevant sessions..."):
                # Use a smaller number of recommendations for performance
                recommendations = self.session_recommender.recommend_sessions(query, top_k=3)
                self.last_query = query
                self.last_results = recommendations
                self.last_query_time = current_time
        else:
            recommendations = self.last_results
        
        # Display recommendations
        if recommendations:
            for session in recommendations:
                # Extract key information with error handling
                title = session.get('session_title', 'Untitled Session')
                duration = session.get('duration', 'N/A')
                
                # Create a simplified display with less nesting
                st.markdown(f"### {title}")
                
                # Host information - simplified
                host_name = "Unknown Host"
                host_users = session.get('host_user', [])
                if host_users and len(host_users) > 0:
                    host_name = host_users[0].get('username', 'Unknown Host')
                
                st.markdown(f"**Host**: {host_name} | **Duration**: {duration}")
                
                # External URL - simplified
                external_url = session.get('external_url', '')
                if external_url:
                    st.markdown(f"[Join Session]({external_url})")
                
                st.markdown("---")
        else:
            st.info("No relevant sessions found. Try a different query!")