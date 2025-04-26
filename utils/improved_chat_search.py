# asha/utils/improved_chat_search.py
import re
from datetime import datetime, timedelta
import traceback

class ImprovedChatSearchHandler:
    """Process natural language search queries from chat and extract search parameters"""
    
    def __init__(self, session_search):
        self.session_search = session_search
        # Keep a cache of host names for partial matching
        self.host_names = None
    
    def _get_all_host_names(self):
        """Get all host names from the session search for partial matching"""
        if self.host_names is None:
            self.host_names = self.session_search.get_session_hosts()
        return self.host_names
    
    def _find_best_host_match(self, partial_name):
        """Find the best matching host name for a partial name"""
        if not partial_name or len(partial_name.strip()) < 2:
            return None
            
        host_names = self._get_all_host_names()
        if not host_names:
            return None
            
        partial_name = partial_name.lower()
        
        # First try exact matches
        for host in host_names:
            if host.lower() == partial_name:
                return host
        
        # Then try starts with matches
        starts_with_matches = []
        for host in host_names:
            if host.lower().startswith(partial_name):
                starts_with_matches.append(host)
                
        if starts_with_matches:
            # Return the shortest match (likely the first name if partial name is a first name)
            return min(starts_with_matches, key=len)
        
        # Then try contains matches
        contains_matches = []
        for host in host_names:
            if partial_name in host.lower():
                contains_matches.append(host)
                
        if contains_matches:
            # Return the shortest match that contains the partial name
            return min(contains_matches, key=len)
            
        return None
    
    def extract_search_params(self, query):
        """Extract search parameters from a natural language query"""
        search_params = {}
        
        # Normalize the query
        query = query.lower().strip()
        
        # Debugging
        print(f"Processing query: {query}")
        
        # Special case for very short queries like "By [name]"
        if query.startswith("by ") and len(query.split()) <= 3:
            # Extract the name after "by "
            host_name = query[3:].strip()
            
            # Try to find the best match among known hosts
            best_match = self._find_best_host_match(host_name)
            if best_match:
                search_params['host'] = best_match
                print(f"Found host using best match: '{best_match}' for query '{host_name}'")
                return search_params
            else:
                search_params['host'] = host_name
                print(f"Using exact host name from query: '{host_name}'")
                return search_params
        
        # Special case for "Session of/by/with [name]" pattern
        simple_host_match = re.search(r'sessions?\s+(of|by|with|from)\s+([a-zA-Z\s]+?)(?:\s*$|\s*[\.,])', query)
        if simple_host_match:
            host = simple_host_match.group(2).strip()
            
            # Try to find the best match among known hosts
            best_match = self._find_best_host_match(host)
            if best_match:
                search_params['host'] = best_match
                print(f"Found host using best match: '{best_match}' for query '{host}'")
            else:
                search_params['host'] = host
                print(f"Found host (simple pattern): {host}")
            return search_params
        
        # Extract host name - more complex patterns
        if 'host' not in search_params:
            host_patterns = [
                r'host(?:ed)?\s+by\s+([a-zA-Z\s]+?)(?:\s+(?:in|from|about|containing|on|during|from)\s+|\s*$|\s+and\s+|\s*[\.,])',
                r'host\s+is\s+([a-zA-Z\s]+?)(?:\s+|\s*$|\s*[\.,])',
                r'by\s+host\s+([a-zA-Z\s]+?)(?:\s+|\s*$|\s*[\.,])',
                r'host\s+name\s+([a-zA-Z\s]+?)(?:\s+|\s*$|\s*[\.,])'
            ]
            
            for pattern in host_patterns:
                match = re.search(pattern, query)
                if match:
                    host = match.group(1).strip()
                    # Clean up the host name
                    host = re.sub(r'\s+', ' ', host)
                    host = host.strip('.,?! ')
                    
                    # Try to find the best match among known hosts
                    best_match = self._find_best_host_match(host)
                    if best_match:
                        search_params['host'] = best_match
                        print(f"Found host using best match: '{best_match}' for query '{host}'")
                    else:
                        search_params['host'] = host
                        print(f"Found host (complex pattern): {host}")
                    break
        
        # Direct name reference (e.g., "Marissa sessions", "sessions Marissa")
        # This is a more aggressive pattern and should be used last
        if 'host' not in search_params:
            # Get all host names for matching
            all_hosts = self._get_all_host_names()
            
            if all_hosts:
                # First try to match full names from the database
                for host in all_hosts:
                    if host.lower() in query:
                        search_params['host'] = host
                        print(f"Found host (full name matching): {host}")
                        break
                
                # If no match found, try matching first names only
                if 'host' not in search_params:
                    for host in all_hosts:
                        # Extract first name (assuming first word is first name)
                        first_name = host.split()[0].lower()
                        if len(first_name) > 2 and first_name in query and 'session' in query:
                            search_params['host'] = host
                            print(f"Found host (first name matching): {host}")
                            break
        
        # Extract date information - special case for January 2023
        date_matches = re.findall(r'(?:in|from|during)\s+(?:january|jan\.?)\s+2023', query, re.IGNORECASE)
        if date_matches:
            search_params['start_date'] = datetime(2023, 1, 1)
            search_params['end_date'] = datetime(2023, 1, 31, 23, 59, 59)
            print(f"Found date range: Jan 2023")
        
        # Extract date ranges - last X days/weeks/months
        time_period_match = re.search(r'(?:in|from|during|past|last)\s+(\d+)\s+(day|days|week|weeks|month|months)', query)
        if time_period_match:
            number = int(time_period_match.group(1))
            unit = time_period_match.group(2)
            
            # Calculate days
            if 'day' in unit:
                days = number
            elif 'week' in unit:
                days = number * 7
            elif 'month' in unit:
                days = number * 30
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            search_params['start_date'] = start_date
            search_params['end_date'] = end_date
            print(f"Found time period: {number} {unit} ({days} days)")
        
        # Extract title/topic keywords - looking for words after "about", "on", or "sessions"
        # but avoid capturing other search parameters already matched
        parts_to_remove = []
        if 'host' in search_params:
            parts_to_remove.append(f"host(?:ed)? by {re.escape(search_params['host'])}")
            parts_to_remove.append(f"host is {re.escape(search_params['host'])}")
            parts_to_remove.append(f"sessions? (?:of|by|with|from) {re.escape(search_params['host'])}")
            # Also remove the direct name mentions
            parts_to_remove.append(r'\b' + re.escape(search_params['host']) + r'\b')
        
        if date_matches:
            parts_to_remove.append(r'(?:in|from|during)\s+(?:january|jan\.?)\s+2023')
        
        if time_period_match:
            parts_to_remove.append(re.escape(time_period_match.group(0)))
        
        # Remove matched parts from the query for further processing
        clean_query = query
        for part in parts_to_remove:
            clean_query = re.sub(part, '', clean_query, flags=re.IGNORECASE)
        
        print(f"Clean query after removing matched parts: {clean_query}")
        
        # Now look for topic/title terms
        topic_match = re.search(r'(?:about|on|regarding|sessions? (?:about|on)|sessions? (?:containing|with)|find|looking for)\s+([a-zA-Z\s]+?)(?:\s*$|\s*[\.,])', clean_query)
        if topic_match:
            topic = topic_match.group(1).strip()
            # Clean up
            topic = re.sub(r'\s+', ' ', topic)
            topic = topic.strip('.,?! ')
            
            # Filter out common words if they appear alone
            stop_words = {'sessions', 'session', 'find', 'me', 'the', 'a', 'an', 'and', 'or', 'for', 'with', 'by'}
            if topic not in stop_words:
                search_params['title'] = topic
                # Also search in description
                search_params['description'] = topic
                print(f"Found topic: {topic}")
        
        # Specific case: "leadership development"
        if 'leadership development' in query:
            search_params['title'] = 'leadership development'
            search_params['description'] = 'leadership development'
            print("Found specific topic: leadership development")
        elif 'leadership' in query and 'title' not in search_params:
            search_params['title'] = 'leadership'
            search_params['description'] = 'leadership'
            print("Found topic: leadership")
        
        # If query is very short and just contains "sessions" or similar, return all sessions
        if len(query.split()) <= 3 and ('session' in query or 'sessions' in query) and not search_params:
            # Return an empty dict with a special flag to indicate "all sessions"
            search_params = {'all_sessions': True}
            print("Query indicates all sessions should be returned")
        
        # If we haven't found any search parameters, try to extract keywords
        if not search_params:
            print("No specific parameters found, extracting keywords...")
            # Extract potential search terms (excluding common words)
            words = query.split()
            stop_words = {'find', 'search', 'looking', 'session', 'sessions', 'workshop', 
                          'workshops', 'event', 'events', 'training', 'for', 'about', 'on', 
                          'the', 'a', 'an', 'by', 'with', 'in', 'i', 'me', 'my', 'can', 
                          'you', 'please', 'help', 'need', 'want', 'show'}
            
            potential_terms = [word for word in words if word not in stop_words and len(word) > 2]
            
            if potential_terms:
                search_term = ' '.join(potential_terms)
                search_params['title'] = search_term
                search_params['description'] = search_term
                print(f"Extracted general search terms: {search_term}")
        
        print(f"Final search parameters: {search_params}")
        return search_params
    
    def is_search_query(self, query):
        """Determine if a query is likely a session search request"""
        query_lower = query.lower()
        
        # Check for explicit search indicators
        search_indicators = [
            r'find\s+(?:a\s+)?sessions?',
            r'search\s+(?:for\s+)?sessions?',
            r'looking\s+for\s+(?:a\s+)?sessions?',
            r'show\s+(?:me\s+)?sessions?',
            r'sessions?\s+(?:about|on|by|with|of|from)',
            r'are\s+there\s+(?:any\s+)?sessions?',
            r'host(?:ed)?\s+by',
            r'sessions?\s+(?:in|during|on)\s+\w+'
        ]
        
        for indicator in search_indicators:
            if re.search(indicator, query_lower):
                return True
        
        # Special case for short "By [name]" queries
        if query_lower.startswith("by ") and len(query_lower.split()) <= 3:
            return True
            
        # If nothing matched but contains "session", still treat as search
        if 'session' in query_lower:
            return True
            
        return False
    
    def search_and_format_results(self, query):
        """Process a chat query, search for sessions, and format results as a response"""
        try:
            # Extract search parameters
            search_params = self.extract_search_params(query)
            
            if not search_params:
                return "I couldn't identify any specific search criteria in your question. Could you please specify what kind of sessions you're looking for? You can mention details like host name, topic, or date."
            
            # Special case for "all sessions" request
            if 'all_sessions' in search_params:
                # Use the session search to get recent sessions
                results = self.session_search.get_recent_sessions(10)
            else:
                # Perform the search with regular parameters
                results = self.session_search.search_sessions(search_params)
            
            # Format the response
            if not results:
                response = ""
                
                # Special case for host search with no results but we have a name
                if 'host' in search_params:
                    host_name = search_params['host']
                    response = f"I couldn't find any sessions with the name '{host_name}'. Here are some upcoming sessions that might be of interest to you:\n\n"
                    
                    # Show some upcoming sessions instead
                    upcoming = self.session_search.filter_sessions_by_status("upcoming")
                    if upcoming and len(upcoming) > 0:
                        # Sort by date and show the nearest ones
                        upcoming_with_dates = []
                        for session in upcoming:
                            session_date = None
                            schedule = session.get('schedule', {})
                            if schedule and 'start_time' in schedule:
                                session_date = self.session_search._extract_date(schedule['start_time'])
                            
                            if session_date:
                                upcoming_with_dates.append((session, session_date))
                        
                        # Sort by date (earliest first)
                        upcoming_with_dates.sort(key=lambda x: x[1])
                        
                        # Show top 3 upcoming
                        for i, (session, date) in enumerate(upcoming_with_dates[:3]):
                            title = session.get('session_title', 'Untitled Session')
                            response += f"**{i+1}. {title}** 📅 Date: {date.strftime('%Y-%m-%d %H:%M')}"
                            
                            # Add host information
                            host_users = session.get('host_user', [])
                            if host_users and len(host_users) > 0:
                                host = host_users[0]
                                response += f" 👤 Host: {host.get('username', 'Unknown')}"
                            
                            # Add duration
                            response += f" ⏱️ Duration: {session.get('duration', 'N/A')}\n"
                            
                        return response
                
                if not response:
                    response = "I couldn't find any sessions matching your criteria. "
                    
                    # Explain what we searched for
                    search_criteria = []
                    if 'host' in search_params:
                        search_criteria.append(f"host containing '{search_params['host']}'")
                    if 'title' in search_params:
                        search_criteria.append(f"title containing '{search_params['title']}'")
                    if 'description' in search_params:
                        # Don't duplicate if same as title
                        if 'title' not in search_params or search_params['description'] != search_params['title']:
                            search_criteria.append(f"description containing '{search_params['description']}'")
                    if 'start_date' in search_params and 'end_date' in search_params:
                        start = search_params['start_date'].strftime('%Y-%m-%d')
                        end = search_params['end_date'].strftime('%Y-%m-%d')
                        search_criteria.append(f"dates between {start} and {end}")
                    
                    if search_criteria:
                        response += "I looked for sessions with " + ", ".join(search_criteria) + "."
                    
                    response += "\n\nYou can try another search with different criteria or use the Search Sessions tab for more detailed search options."
                    
                return response
            
            # Format results
            if 'host' in search_params:
                host_name = search_params['host']
                response = f"Here are the sessions hosted by {host_name} that match your criteria:\n\n"
            elif 'all_sessions' in search_params:
                response = f"Here are {len(results)} recent sessions:\n\n"
            else:
                response = f"I found {len(results)} sessions matching your criteria:\n\n"
            
            # Sort by date if possible
            sorted_results = []
            for session in results:
                # Extract date for sorting
                session_date = None
                schedule = session.get('schedule', {})
                if schedule and 'start_time' in schedule:
                    # Try different date formats
                    if isinstance(schedule['start_time'], str):
                        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
                            try:
                                session_date = datetime.strptime(schedule['start_time'], fmt)
                                break
                            except:
                                pass
                
                sorted_results.append((session, session_date))
            
            # Sort by date (most recent first) if dates are available
            sorted_results.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
            
            # Limit to top 5 results
            display_count = min(5, len(sorted_results))
            sorted_results = sorted_results[:display_count]
            
            # Build response text
            for i, (session, session_date) in enumerate(sorted_results):
                title = session.get('session_title', 'Untitled Session')
                response += f"**{i+1}. {title}**"
                
                # Add date if available
                if session_date:
                    response += f" 📅 Date: {session_date.strftime('%Y-%m-%d %H:%M')}"
                
                # Add host information
                host_users = session.get('host_user', [])
                if host_users and len(host_users) > 0:
                    host = host_users[0]
                    response += f" 👤 Host: {host.get('username', 'Unknown')}"
                
                # Add duration
                response += f" ⏱️ Duration: {session.get('duration', 'N/A')}"
                
                # Add URL if available
                if 'external_url' in session and session['external_url']:
                    response += f"\n🔗 [Join Session]({session['external_url']})"
                
                # Add newline between sessions
                response += "\n"
                if i < display_count - 1:
                    response += "\n"
            
            # Add note if we're not showing all results
            if len(results) > display_count:
                remaining = len(results) - display_count
                response += f"\nThere are {remaining} more sessions matching your criteria. You can view all results in the Search Sessions tab."
            
            return response
        except Exception as e:
            print(f"Error in search_and_format_results: {e}")
            traceback.print_exc()
            return "I apologize, but I encountered an error while searching for sessions. Please try again with a more specific query or check the Search Sessions tab for more options."