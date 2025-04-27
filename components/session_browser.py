# components/session_browser.py (consolidated version)

import streamlit as st
from datetime import datetime, timedelta
import time
import re
import json
import calendar

class SessionBrowser:
    def __init__(self, session_recommender):
        self.session_recommender = session_recommender
        # Keep track of last query to avoid redundant searches
        self.last_query = None
        self.last_results = []
        self.last_query_time = 0
        
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
    
    def _extract_description_text(self, description):
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
    
    def get_recent_sessions(self, limit=10):
        """Get the most recent sessions"""
        sessions = self.session_recommender.get_recent_sessions(limit)
        return sessions
    
    def search_sessions(self, search_params, max_results=5):
        """Search sessions with specific criteria"""
        # Check if we can use cached results
        current_time = time.time()
        cache_valid = (
            self.last_query == str(search_params) and
            current_time - self.last_query_time < 300  # Cache valid for 5 minutes
        )
        
        if cache_valid:
            return self.last_results
            
        # Perform actual search
        results = self.session_recommender.search_sessions(search_params, max_results)
        
        # Update cache
        self.last_query = str(search_params)
        self.last_results = results
        self.last_query_time = current_time
        
        return results
    
    def render(self):
        """Render session recommendations with performance optimizations"""
        # Create tabs for search and calendar views
        search_tab, calendar_tab = st.tabs(["Search", "Calendar"])
        
        # Add search interface to first tab
        with search_tab:
            st.subheader("Session Search")
            
            # Quick search buttons
            st.markdown("### Quick Searches")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("All Recent Sessions", use_container_width=True):
                    st.session_state.show_all_sessions = True
                    st.rerun()
            with col_b:
                if st.button("Leadership Sessions", use_container_width=True):
                    st.session_state.quick_title_search = "leadership"
                    st.rerun()
            with col_c:
                if st.button("Marissa's Sessions", use_container_width=True):
                    st.session_state.quick_host_search = "marissa"
                    st.rerun()
            
            # Advanced search form
            st.markdown("### Advanced Search")
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
                submit_button = st.form_submit_button("Search Sessions", use_container_width=True)
            
            # Handle form submission
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
                if search_params:
                    results = self.search_sessions(search_params)
                    self._display_results(results, search_params)
                else:
                    st.warning("Please enter at least one search criterion")
            
            # Handle quick searches
            elif hasattr(st.session_state, 'show_all_sessions') and st.session_state.show_all_sessions:
                # Reset the flag
                st.session_state.show_all_sessions = False
                # Show all recent sessions
                results = self.get_recent_sessions(limit=10)
                self._display_results(results, {"all_sessions": True})
            
            elif hasattr(st.session_state, 'quick_title_search') and st.session_state.quick_title_search:
                # Get the search term and reset
                title_search = st.session_state.quick_title_search
                st.session_state.quick_title_search = None
                # Search by title
                results = self.search_sessions({"title": title_search})
                self._display_results(results, {"title": title_search})
            
            elif hasattr(st.session_state, 'quick_host_search') and st.session_state.quick_host_search:
                # Get the search term and reset
                host_search = st.session_state.quick_host_search
                st.session_state.quick_host_search = None
                # Search by host
                results = self.search_sessions({"host": host_search})
                self._display_results(results, {"host": host_search})
        
        # Add calendar view to second tab
        with calendar_tab:
            self.render_calendar_view()
    
    def _display_results(self, results, search_params):
        """Display search results"""
        if results:
            if 'all_sessions' in search_params:
                st.success(f"Showing {len(results)} recent sessions")
            else:
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
                    description = self._extract_description_text(session.get('description', ''))
                    if description:
                        st.markdown(f"**Description**: {description[:200]}...")
                    
                    # Session URL
                    if 'external_url' in session and session['external_url']:
                        st.markdown(f"[Join Session]({session['external_url']})")
        else:
            # No results message
            st.warning("No sessions found matching your search criteria")
    
    def render_calendar_view(self):
        """Render a visual calendar view of sessions"""
        st.subheader("Session Calendar")
        
        # Get all sessions with dates
        sessions = self.session_recommender.get_all_sessions()
        if not sessions:
            st.info("No sessions available.")
            return
            
        sessions_with_dates = []
        for session in sessions:
            session_date = None
            schedule = session.get('schedule', {})
            if schedule and 'start_time' in schedule:
                session_date = self._extract_date(schedule['start_time'])
                
            if session_date:
                sessions_with_dates.append((session, session_date))
        
        if not sessions_with_dates:
            st.info("No sessions with scheduled dates available.")
            return
        
        # Get current year and month
        today = datetime.now()
        
        # Create month selection
        months = ["January", "February", "March", "April", "May", "June", 
                 "July", "August", "September", "October", "November", "December"]
        years = sorted(set([date.year for _, date in sessions_with_dates]))
        if not years:
            years = [today.year]
        
        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox("Month:", months, index=today.month-1)
        with col2:
            selected_year = st.selectbox("Year:", years, index=years.index(today.year) if today.year in years else 0)
        
        # Convert month name to number
        month_num = months.index(selected_month) + 1
        
        # Filter sessions for selected month/year
        month_sessions = [
            (session, date) for session, date in sessions_with_dates
            if date.month == month_num and date.year == selected_year
        ]
        
        # Create calendar grid
        st.markdown(f"### {selected_month} {selected_year}")
        
        # Display sessions for the month
        if month_sessions:
            # Group by day
            sessions_by_day = {}
            for session, date in month_sessions:
                day = date.day
                if day not in sessions_by_day:
                    sessions_by_day[day] = []
                sessions_by_day[day].append((session, date))
            
            # Create a calendar grid
            first_day = datetime(selected_year, month_num, 1)
            first_weekday = first_day.weekday()  # 0 = Monday
            
            # Display weekday headers
            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            cols = st.columns(7)
            for i, day in enumerate(weekdays):
                with cols[i]:
                    st.markdown(f"**{day}**")
            
            # Calculate days in month
            if month_num == 12:
                last_day = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(selected_year, month_num + 1, 1) - timedelta(days=1)
            
            days_in_month = last_day.day
            
            # Create calendar grid
            day = 1
            for week in range(6):  # Max 6 weeks in a month
                if day > days_in_month:
                    break
                    
                cols = st.columns(7)
                for weekday in range(7):
                    with cols[weekday]:
                        # Skip days before the 1st of the month
                        if week == 0 and weekday < first_weekday:
                            st.write("")
                        elif day <= days_in_month:
                            # Highlight today
                            if (day == today.day and month_num == today.month and 
                                selected_year == today.year):
                                st.markdown(f"**{day}** 📌")
                            else:
                                st.write(day)
                            
                            # Display sessions for this day
                            if day in sessions_by_day:
                                for session, date in sessions_by_day[day]:
                                    title = session.get('session_title', '')
                                    if len(title) > 15:
                                        title = title[:12] + "..."
                                    
                                    # Format time
                                    time_str = date.strftime("%H:%M")
                                    st.markdown(f"- {time_str} {title}")
                            
                            day += 1
        else:
            st.info(f"No sessions scheduled for {selected_month} {selected_year}")