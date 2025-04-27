# asha/components/enhanced_session_search.py
import streamlit as st
from utils.db import get_all_sessions
import json
import re
from datetime import datetime, timedelta

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
    
    def get_recent_sessions(self, limit=10):
        """Get the most recent sessions"""
        if not self.sessions:
            return []
            
        # Sort sessions by creation date if available
        sessions_with_dates = []
        for session in self.sessions:
            # Try to extract creation date
            session_date = None
            meta_data = session.get('meta_data', {})
            if meta_data and 'created_at' in meta_data:
                session_date = self._extract_date(meta_data['created_at'])
            
            # If no creation date, try schedule date
            if not session_date:
                schedule = session.get('schedule', {})
                if schedule and 'start_time' in schedule:
                    session_date = self._extract_date(schedule['start_time'])
            
            sessions_with_dates.append((session, session_date))
        
        # Sort by date (most recent first)
        sessions_with_dates.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
        
        # Return sessions only (not dates)
        return [session for session, _ in sessions_with_dates[:limit]]
    
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
              - all_sessions: if True, return all sessions (sorted by date)
        """
        if not self.sessions:
            return []
            
        # Special case for "all sessions" request
        if search_params.get('all_sessions'):
            return self.get_recent_sessions(limit=10)
            
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
        # Create tabs for search and dashboard views
        search_tab, dashboard_tab, calendar_tab = st.tabs(["Search", "Dashboard", "Calendar"])
        
        with search_tab:
            st.subheader("Session Search")
            
            # Quick search buttons - OUTSIDE the form
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
            
            st.markdown("### Advanced Search")
            with st.form(key="search_form"):
                # Title search
                title_search = st.text_input("Title contains:", "")
                
                # Host search
                host_search = st.text_input("Host name contains:", "")
                
                # Host dropdown for easier selection
                hosts = self.get_session_hosts()
                if hosts:
                    selected_host = st.selectbox("Or select a host:", [""] + hosts)
                    if selected_host and not host_search:
                        host_search = selected_host
                
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
        
        with dashboard_tab:
            self.display_session_dashboard()
            
        with calendar_tab:
            self.render_calendar_view()
            
        # Process search when form is submitted or quick search is triggered
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
                
                # Add export option if results are found
                if results:
                    csv_data = self.export_sessions_to_csv(results)
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name="session_results.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("Please enter at least one search criterion")
        
        # Handle quick searches
        elif hasattr(st.session_state, 'show_all_sessions') and st.session_state.show_all_sessions:
            # Reset the flag
            st.session_state.show_all_sessions = False
            # Show all recent sessions
            results = self.get_recent_sessions(limit=10)
            self._display_results(results, {"all_sessions": True})
            
            # Add export option
            if results:
                csv_data = self.export_sessions_to_csv(results)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="recent_sessions.csv",
                    mime="text/csv"
                )
        
        elif hasattr(st.session_state, 'quick_title_search') and st.session_state.quick_title_search:
            # Get the search term and reset
            title_search = st.session_state.quick_title_search
            st.session_state.quick_title_search = None
            # Search by title
            results = self.search_sessions({"title": title_search})
            self._display_results(results, {"title": title_search})
            
            # Add export option
            if results:
                csv_data = self.export_sessions_to_csv(results)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{title_search}_sessions.csv",
                    mime="text/csv"
                )
        
        elif hasattr(st.session_state, 'quick_host_search') and st.session_state.quick_host_search:
            # Get the search term and reset
            host_search = st.session_state.quick_host_search
            st.session_state.quick_host_search = None
            # Search by host
            results = self.search_sessions({"host": host_search})
            self._display_results(results, {"host": host_search})
            
            # Add export option
            if results:
                csv_data = self.export_sessions_to_csv(results)
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{host_search}_sessions.csv",
                    mime="text/csv"
                )
    
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
            if 'all_sessions' in search_params:
                search_details.append("All recent sessions")
            
            st.markdown("- " + "\n- ".join(search_details))
    
    def get_session_categories(self):
        """Extract and return unique categories from all sessions"""
        categories = set()
        
        for session in self.sessions:
            # Extract categories if available
            session_categories = session.get('categories', [])
            if isinstance(session_categories, list):
                for category in session_categories:
                    if isinstance(category, str) and category:
                        categories.add(category)
                    elif isinstance(category, dict) and 'name' in category:
                        categories.add(category['name'])
        
        return sorted(list(categories))
    
    def get_session_hosts(self):
        """Extract and return unique host names from all sessions"""
        hosts = set()
        
        for session in self.sessions:
            host_users = session.get('host_user', [])
            for host in host_users:
                if isinstance(host, dict) and 'username' in host:
                    hosts.add(host['username'])
        
        return sorted(list(hosts))
    
    def get_session_by_id(self, session_id):
        """Retrieve a session by its ID"""
        if not session_id:
            return None
            
        for session in self.sessions:
            if session.get('session_id') == session_id:
                return session
                
        return None
    
    def filter_sessions_by_status(self, status="upcoming"):
        """Filter sessions by their status (upcoming, completed, all)"""
        if not self.sessions:
            return []
            
        filtered_sessions = []
        current_time = datetime.now()
        
        for session in self.sessions:
            # Check if session has a schedule
            schedule = session.get('schedule', {})
            if not schedule or 'start_time' not in schedule:
                continue
                
            # Parse the start time
            start_time = self._extract_date(schedule['start_time'])
            if not start_time:
                continue
                
            # Check status
            if status == "upcoming" and start_time > current_time:
                filtered_sessions.append(session)
            elif status == "completed" and start_time < current_time:
                filtered_sessions.append(session)
            elif status == "all":
                filtered_sessions.append(session)
        
        return filtered_sessions
    
    def export_sessions_to_csv(self, sessions):
        """Convert sessions to CSV format for export"""
        if not sessions:
            return ""
            
        # Define CSV headers
        headers = ["Title", "Host", "Date", "Duration", "Description", "URL"]
        
        # Start with headers
        csv_content = ",".join(headers) + "\n"
        
        # Add each session as a row
        for session in sessions:
            title = session.get('session_title', 'Untitled').replace('"', '""')
            
            # Extract host
            host_name = "Unknown"
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_name = host_users[0].get('username', 'Unknown').replace('"', '""')
            
            # Extract date
            date_str = "N/A"
            schedule = session.get('schedule', {})
            if schedule and 'start_time' in schedule:
                date = self._extract_date(schedule['start_time'])
                if date:
                    date_str = date.strftime('%Y-%m-%d %H:%M')
            
            # Get duration
            duration = session.get('duration', 'N/A').replace('"', '""')
            
            # Get description
            description = self._extract_text_from_description(
                session.get('description', '')
            ).replace('"', '""').replace('\n', ' ')
            
            # Get URL
            url = session.get('external_url', 'N/A').replace('"', '""')
            
            # Create CSV row
            row = [
                f'"{title}"',
                f'"{host_name}"',
                f'"{date_str}"',
                f'"{duration}"',
                f'"{description}"',
                f'"{url}"'
            ]
            
            # Add row to CSV content
            csv_content += ",".join(row) + "\n"
        
        return csv_content
    
    def display_session_dashboard(self):
        """Display a dashboard view of sessions with metrics"""
        if not self.sessions:
            st.warning("No sessions available to display.")
            return
        
        # Calculate metrics
        total_sessions = len(self.sessions)
        upcoming_sessions = len(self.filter_sessions_by_status("upcoming"))
        completed_sessions = len(self.filter_sessions_by_status("completed"))
        unique_hosts = len(self.get_session_hosts())
        
        # Display metrics in a dashboard
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sessions", total_sessions)
        with col2:
            st.metric("Upcoming Sessions", upcoming_sessions)
        with col3:
            st.metric("Completed Sessions", completed_sessions)
        with col4:
            st.metric("Unique Hosts", unique_hosts)
        
        # Add a session calendar view
        st.subheader("Upcoming Sessions")
        upcoming = self.filter_sessions_by_status("upcoming")
        
        if upcoming:
            # Sort by date
            upcoming_with_dates = []
            for session in upcoming:
                # Extract date for sorting
                session_date = None
                schedule = session.get('schedule', {})
                if schedule and 'start_time' in schedule:
                    session_date = self._extract_date(schedule['start_time'])
                
                if session_date:
                    upcoming_with_dates.append((session, session_date))
            
            # Sort by date (earliest first)
            upcoming_with_dates.sort(key=lambda x: x[1])
            
            # Group by month/year
            sessions_by_month = {}
            for session, date in upcoming_with_dates:
                month_year = date.strftime('%B %Y')
                if month_year not in sessions_by_month:
                    sessions_by_month[month_year] = []
                sessions_by_month[month_year].append((session, date))
            
            # Display calendar view
            for month_year, month_sessions in sessions_by_month.items():
                with st.expander(f"📅 {month_year} ({len(month_sessions)} sessions)", expanded=True):
                    for session, date in month_sessions:
                        title = session.get('session_title', 'Untitled Session')
                        date_str = date.strftime('%a, %d %b - %H:%M')
                        
                        # Extract host
                        host_name = "Unknown Host"
                        host_users = session.get('host_user', [])
                        if host_users and len(host_users) > 0:
                            host_name = host_users[0].get('username', 'Unknown Host')
                        
                        st.markdown(f"**{date_str}**: {title} (Host: {host_name})")
        else:
            st.info("No upcoming sessions scheduled at this time.")
            
        # Top hosts section
        st.subheader("Top Session Hosts")
        host_counts = {}
        for session in self.sessions:
            host_users = session.get('host_user', [])
            for host in host_users:
                if isinstance(host, dict) and 'username' in host:
                    username = host['username']
                    if username in host_counts:
                        host_counts[username] += 1
                    else:
                        host_counts[username] = 1
                        
        # Display top 5 hosts
        if host_counts:
            top_hosts = sorted(host_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Create columns for host cards
            cols = st.columns(len(top_hosts))
            for i, (host_name, count) in enumerate(top_hosts):
                with cols[i]:
                    st.markdown(f"### {host_name}")
                    st.markdown(f"**{count}** sessions")
                    # Use button outside of form
                    if st.button(f"View {host_name}'s Sessions", key=f"host_{i}"):
                        st.session_state.quick_host_search = host_name
                        st.rerun()
        else:
            st.info("No host information available.")
    
    def render_calendar_view(self):
        """Render a visual calendar view of sessions"""
        st.subheader("Session Calendar")
        
        # Get all sessions with dates
        sessions_with_dates = []
        for session in self.sessions:
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
        
        # Create the calendar header (days of week)
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for i, day in enumerate(weekdays):
            with cols[i]:
                st.markdown(f"**{day}**", unsafe_allow_html=True)
        
        # Get first day of month and number of days
        first_day = datetime(selected_year, month_num, 1)
        if month_num == 12:
            last_day = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(selected_year, month_num + 1, 1) - timedelta(days=1)
        
        num_days = last_day.day
        
        # Adjust first_weekday (0=Monday, 6=Sunday)
        first_weekday = first_day.weekday()  # 0 = Monday, 6 = Sunday
        
        # Generate calendar cells
        day = 1
        for week in range(6):  # Max 6 weeks in a month
            if day > num_days:
                break
                
            row_cols = st.columns(7)
            
            for weekday in range(7):
                with row_cols[weekday]:
                    # Skip cells before the 1st of the month
                    if week == 0 and weekday < first_weekday:
                        st.markdown("&nbsp;", unsafe_allow_html=True)
                    elif day <= num_days:
                        # Get sessions for this day
                        day_sessions = [
                            session for session, date in month_sessions
                            if date.day == day
                        ]
                        
                        # Highlight today's date
                        is_today = (today.year == selected_year and 
                                  today.month == month_num and 
                                  today.day == day)
                        
                        if is_today:
                            st.markdown(f"<div style='background-color:#e6f3ff; padding:5px; border-radius:5px;'><b>{day}</b></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='padding:5px;'>{day}</div>", unsafe_allow_html=True)
                        
                        # Display sessions for this day
                        if day_sessions:
                            for session in day_sessions:
                                title = session.get('session_title', '')
                                if len(title) > 20:
                                    title = title[:18] + "..."
                                
                                # Get scheduled time
                                time_str = ""
                                schedule = session.get('schedule', {})
                                if schedule and 'start_time' in schedule:
                                    session_date = self._extract_date(schedule['start_time'])
                                    if session_date:
                                        time_str = session_date.strftime('%H:%M')
                                
                                # Display session with expander
                                with st.expander(f"{time_str} {title}", expanded=False):
                                    # Host information
                                    host_users = session.get('host_user', [])
                                    if host_users and len(host_users) > 0:
                                        host = host_users[0]
                                        st.markdown(f"**Host**: {host.get('username', 'Unknown')}")
                                    
                                    # Duration
                                    st.markdown(f"**Duration**: {session.get('duration', 'N/A')}")
                                    
                                    # Session URL
                                    if 'external_url' in session and session['external_url']:
                                        st.markdown(f"[Join Session]({session['external_url']})")
                        
                        day += 1
        
        # Display legend
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if month_sessions:
                st.success(f"Found {len(month_sessions)} sessions in {selected_month} {selected_year}")
            else:
                st.info(f"No sessions scheduled for {selected_month} {selected_year}")
        
        with col2:
            # Quick navigation to next/previous month
            prev_month = month_num - 1 if month_num > 1 else 12
            prev_year = selected_year if month_num > 1 else selected_year - 1
            
            next_month = month_num + 1 if month_num < 12 else 1
            next_year = selected_year if month_num < 12 else selected_year + 1
            
            # Use buttons for navigation - NOT in a form
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(f"← {months[prev_month-1]}", key="prev_month"):
                    st.session_state.calendar_month = months[prev_month-1]
                    st.session_state.calendar_year = prev_year
                    st.rerun()
            with col_b:
                if st.button(f"{months[next_month-1]} →", key="next_month"):
                    st.session_state.calendar_month = months[next_month-1]
                    st.session_state.calendar_year = next_year
                    st.rerun()