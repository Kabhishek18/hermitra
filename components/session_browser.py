# asha/components/session_browser.py
import streamlit as st
from datetime import datetime

class SessionBrowser:
    def __init__(self, session_recommender):
        self.session_recommender = session_recommender
    
    def render(self, query=None):
        """Render session recommendations"""
        st.subheader("Recommended Sessions")
        
        if not query:
            st.info("Ask a career question to get relevant session recommendations!")
            return
        
        # Get recommendations
        with st.spinner("Finding relevant sessions..."):
            recommendations = self.session_recommender.recommend_sessions(query)
        
        # Display recommendations
        if recommendations:
            for session in recommendations:
                with st.expander(f"📅 {session.get('session_title', 'Session')}"):
                    # Host information
                    host_users = session.get('host_user', [])
                    if host_users and len(host_users) > 0:
                        host = host_users[0]
                        st.markdown(f"**Host**: {host.get('username', 'Unknown')}")
                    
                    # Schedule information
                    schedule = session.get('schedule', {})
                    if schedule:
                        start_time = schedule.get('start_time', '')
                        # Handle different date formats after our cleaning
                        if isinstance(start_time, str):
                            # Try to parse as ISO format if it's a string now
                            try:
                                if start_time.endswith('Z'):
                                    start_time = start_time[:-1]  # Remove Z if present
                                start_date = datetime.fromisoformat(start_time)
                                st.markdown(f"**Date**: {start_date.strftime('%Y-%m-%d %H:%M')}")
                            except:
                                # If parsing fails, just show the raw string
                                st.markdown(f"**Date**: {start_time}")
                    
                    st.markdown(f"**Duration**: {session.get('duration', 'N/A')}")
                    
                    # External URL
                    if 'external_url' in session and session['external_url']:
                        st.markdown(f"[Join Session]({session['external_url']})")
        else:
            st.info("No relevant sessions found. Try a different query!")