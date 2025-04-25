# asha/components/enhanced_session_search.py
import streamlit as st
from utils.db import get_all_sessions
import json
import re
from datetime import datetime

class EnhancedSessionSearch:
    def __init__(self):
        # Load sessions once during initialization
        self.sessions = get_all_sessions()
    
    def _extract_date(self, date_value):
        """Extract date from various formats"""
        if isinstance(date_value, str):
            # Try different date formats
            for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_value, fmt)
                except:
                    pass
        return None
    
    def _extract_text_from_description(self, description):
        """Extract plain text from structured description"""
        if not description:
            return ""
            
        # If description is a string that looks like JSON, try to parse it
        if isinstance(description, str):
            # If it's already plain text, return it
            if not description.strip().startswith('{'):
                return description
                
            # Try to parse as JSON
            try:
                desc_obj = json.loads(description)
                # Try to extract text from Lexical JSON structure
                if 'root' in desc_obj and 'children' in desc_obj['root']:
                    text_parts = []
                    self._extract_text_from_lexical(desc_obj['root'], text_parts)
                    return ' '.join(text_parts)
            except:
                # If parsing fails, return the original string
                return description
                
        # If it's already a dictionary
        if isinstance(description, dict):
            if 'root' in description and 'children' in description.get('root', {}):
                text_parts = []
                self._extract_text_from_lexical(description['root'], text_parts)
                return ' '.join(text_parts)
                
        # Fallback: convert to string
        return str(description)
    
    def _extract_text_from_lexical(self, node, text_parts):
        """Recursively extract text from Lexical editor JSON structure"""
        if isinstance(node, dict):
            if 'text' in node:
                text_parts.append(node['text'])
            if 'children' in node:
                for child in node['children']:
                    self._extract_text_from_lexical(child, text_parts)
        elif isinstance(node, list):
            for item in node:
                self._extract_text_from_lexical(item, text_parts)
    
    def search_sessions(self, search_params):
        """
        Search sessions with multiple criteria
        
        Args:
            search_params: Dictionary with search parameters
              - title: keywords for title search
              - host: keywords for host name search
              - description: keywords for description search
              - start_date: minimum start date (datetime)
              - end_date: maximum start date (datetime)
        """
        if not self.sessions:
            return []
            
        # Get search parameters, defaulting to None if not provided
        title = search_params.get('title')
        host = search_params.get('host')
        description = search_params.get('description')
        start_date = search_params.get('start_date')
        end_date = search_params.get('end_date')
        
        # Convert to lowercase for case-insensitive search
        if title:
            title = title.lower()
        if host:
            host = host.lower()
        if description:
            description = description.lower()
        
        matching_sessions = []
        
        for session in self.sessions:
            # Default to True, and set to False if any criteria fails
            matches = True
            
            # Check title
            if title and matches:
                session_title = session.get('session_title', '').lower()
                if title not in session_title:
                    matches = False
            
            # Check host name
            if host and matches:
                host_found = False
                host_users = session.get('host_user', [])
                for host_user in host_users:
                    username = host_user.get('username', '').lower()
                    if host in username:
                        host_found = True
                        break
                if not host_found:
                    matches = False
            
            # Check description
            if description and matches:
                session_desc = self._extract_text_from_description(session.get('description', '')).lower()
                if description not in session_desc:
                    matches = False
            
            # Check date range
            if (start_date or end_date) and matches:
                # Extract session date
                schedule = session.get('schedule', {})
                session_start = None
                
                if schedule and 'start_time' in schedule:
                    session_start = self._extract_date(schedule['start_time'])
                
                # If we have a date to check
                if session_start:
                    # Check start date constraint
                    if start_date and session_start < start_date:
                        matches = False
                    
                    # Check end date constraint
                    if end_date and session_start > end_date:
                        matches = False
                elif start_date or end_date:
                    # If date constraints exist but session has no date, exclude it
                    matches = False
            
            # If all checks passed, add to results
            if matches:
                matching_sessions.append(session)
        
        return matching_sessions
    
    def render(self):
        """Render an enhanced session search interface"""
        st.subheader("Session Search")
        
        with st.form(key="search_form"):
            # Title search
            title_search = st.text_input("Title contains:", "")
            
            # Host search
            host_search = st.text_input("Host name contains:", "")
            
            # Description search
            desc_search = st.text_input("Description contains:", "")
            
            # Date range
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("From date:", value=None)
            with col2:
                end_date = st.date_input("To date:", value=None)
            
            # Submit button
            submit_button = st.form_submit_button("Search Sessions")
        
        # Process search when form is submitted
        if submit_button:
            # Prepare search parameters
            search_params = {}
            
            if title_search:
                search_params['title'] = title_search
                
            if host_search:
                search_params['host'] = host_search
                
            if desc_search:
                search_params['description'] = desc_search
                
            # Convert dates to datetime objects
            if start_date is not None:
                search_params['start_date'] = datetime.combine(start_date, datetime.min.time())
                
            if end_date is not None:
                search_params['end_date'] = datetime.combine(end_date, datetime.max.time())
            
            # Execute search
            if search_params:  # Only search if at least one parameter is set
                results = self.search_sessions(search_params)
                self._display_results(results, search_params)
            else:
                st.warning("Please enter at least one search criterion")
    
    def _display_results(self, results, search_params):
        """Display search results"""
        if results:
            st.success(f"Found {len(results)} matching sessions")
            
            # Sort results by date if available
            results_with_dates = []
            for session in results:
                # Extract date for sorting
                session_date = None
                schedule = session.get('schedule', {})
                if schedule and 'start_time' in schedule:
                    session_date = self._extract_date(schedule['start_time'])
                
                results_with_dates.append((session, session_date))
            
            # Sort by date (most recent first) if dates are available
            results_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
            
            # Display results
            for session, session_date in results_with_dates:
                title = session.get('session_title', 'Untitled Session')
                
                # Format date if available
                date_str = ""
                if session_date:
                    date_str = f" | 📅 {session_date.strftime('%Y-%m-%d %H:%M')}"
                
                # Create expandable card for each session
                with st.expander(f"📌 {title}{date_str}"):
                    # Host information
                    host_users = session.get('host_user', [])
                    if host_users and len(host_users) > 0:
                        host = host_users[0]
                        st.markdown(f"**Host**: {host.get('username', 'Unknown')}")
                    
                    # Duration
                    st.markdown(f"**Duration**: {session.get('duration', 'N/A')}")
                    
                    # Description
                    description = self._extract_text_from_description(session.get('description', ''))
                    if description:
                        st.markdown(f"**Description**: {description[:200]}...")
                    
                    # Session URL
                    if 'external_url' in session and session['external_url']:
                        st.markdown(f"[Join Session]({session['external_url']})")
                    
                    # Session ID and timestamps
                    st.markdown("---")
                    st.caption(f"Session ID: {session.get('session_id', 'N/A')}")
                    
                    # Created/Updated timestamps
                    meta_data = session.get('meta_data', {})
                    if meta_data:
                        if 'created_at' in meta_data:
                            created_date = self._extract_date(meta_data['created_at'])
                            if created_date:
                                st.caption(f"Created: {created_date.strftime('%Y-%m-%d')}")
                        
                        if 'updated_at' in meta_data:
                            updated_date = self._extract_date(meta_data['updated_at'])
                            if updated_date:
                                st.caption(f"Updated: {updated_date.strftime('%Y-%m-%d')}")
        else:
            # No results message
            st.warning("No sessions found matching your search criteria")
            
            # Show search parameters for reference
            st.markdown("**Search criteria used:**")
            search_details = []
            if 'title' in search_params:
                search_details.append(f"Title: '{search_params['title']}'")
            if 'host' in search_params:
                search_details.append(f"Host: '{search_params['host']}'")
            if 'description' in search_params:
                search_details.append(f"Description: '{search_params['description']}'")
            if 'start_date' in search_params:
                search_details.append(f"From: {search_params['start_date'].strftime('%Y-%m-%d')}")
            if 'end_date' in search_params:
                search_details.append(f"To: {search_params['end_date'].strftime('%Y-%m-%d')}")
            
            st.markdown("- " + "\n- ".join(search_details))