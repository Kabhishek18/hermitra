# asha/utils/chat_search.py
import re
from datetime import datetime, timedelta
import streamlit as st

class ChatSearchHandler:
    """Process natural language search queries from chat and extract search parameters"""
    
    def __init__(self, session_search):
        self.session_search = session_search
        
        # Define patterns for different search aspects
        self.host_patterns = [
            r'host(?:ed)?\s+by\s+([a-zA-Z\s]+)',
            r'host\s+is\s+([a-zA-Z\s]+)',
            r'host\s+name\s+(?:is\s+)?([a-zA-Z\s]+)',
            r'sessions?\s+(?:by|from)\s+([a-zA-Z\s]+)'
        ]
        
        self.title_patterns = [
            r'title\s+(?:contains|has|with)\s+([a-zA-Z\s]+)',
            r'(?:about|on|regarding)\s+([a-zA-Z\s]+)\s+sessions?',
            r'sessions?\s+(?:about|on|regarding)\s+([a-zA-Z\s]+)'
        ]
        
        self.description_patterns = [
            r'description\s+(?:contains|has|with)\s+([a-zA-Z\s]+)',
            r'content\s+(?:contains|has|with)\s+([a-zA-Z\s]+)',
            r'(?:containing|discussing)\s+([a-zA-Z\s]+)'
        ]
        
        self.date_patterns = [
            r'(?:on|at|in|during)\s+(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:\s+\d{4})?)',
            r'(?:on|at|in|during)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?)',
            r'(?:on|at|in|during)\s+(\d{4}-\d{1,2}-\d{1,2})',
            r'(?:on|at|in|during)\s+(\d{1,2}/\d{1,2}/\d{4})',
            r'(?:on|at|in|during)\s+(\d{1,2}/\d{1,2}/\d{2})'
        ]
        
        self.recent_patterns = [
            r'recent(?:ly)?',
            r'latest',
            r'new(?:est)?',
            r'last\s+(\d+)\s+(?:days?|weeks?|months?)'
        ]
        
        self.upcoming_patterns = [
            r'upcoming',
            r'future',
            r'next\s+(\d+)\s+(?:days?|weeks?|months?)',
            r'(?:today|tomorrow|this\s+week)'
        ]
    
    def extract_search_params(self, query):
        """Extract search parameters from a natural language query"""
        search_params = {}
        
        # Normalize the query
        query = query.lower().strip()
        
        # Extract host name
        for pattern in self.host_patterns:
            match = re.search(pattern, query)
            if match:
                host = match.group(1).strip()
                # Clean up the host name
                host = re.sub(r'\s+', ' ', host)
                host = host.strip('.,?! ')
                search_params['host'] = host
                break
        
        # Extract title keywords
        for pattern in self.title_patterns:
            match = re.search(pattern, query)
            if match:
                title = match.group(1).strip()
                # Clean up the title
                title = re.sub(r'\s+', ' ', title)
                title = title.strip('.,?! ')
                search_params['title'] = title
                break
        
        # Extract description keywords
        for pattern in self.description_patterns:
            match = re.search(pattern, query)
            if match:
                description = match.group(1).strip()
                # Clean up the description
                description = re.sub(r'\s+', ' ', description)
                description = description.strip('.,?! ')
                search_params['description'] = description
                break
        
        # Extract date information
        for pattern in self.date_patterns:
            match = re.search(pattern, query)
            if match:
                date_str = match.group(1).strip()
                # Process the date string
                try:
                    # Try different date formats
                    date = None
                    for fmt in [
                        "%d %B %Y", "%d %B", "%B %d %Y", "%B %d", 
                        "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"
                    ]:
                        try:
                            date = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue
                    
                    if date:
                        # If no year specified, use current year
                        if date.year == 1900:
                            current_year = datetime.now().year
                            date = date.replace(year=current_year)
                        
                        # Set date range (entire day)
                        search_params['start_date'] = datetime.combine(date.date(), datetime.min.time())
                        search_params['end_date'] = datetime.combine(date.date(), datetime.max.time())
                except:
                    # If date parsing fails, ignore it
                    pass
                break
        
        # Handle "recent" sessions
        for pattern in self.recent_patterns:
            match = re.search(pattern, query)
            if match:
                # Default to last 30 days
                days_back = 30
                
                # Check if a specific time period was mentioned
                if "last" in pattern:
                    # Try to extract the number of days/weeks/months
                    try:
                        number = int(match.group(1))
                        if "week" in match.group(0):
                            days_back = number * 7
                        elif "month" in match.group(0):
                            days_back = number * 30
                        else:  # days
                            days_back = number
                    except:
                        days_back = 30
                
                # Calculate the date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                search_params['start_date'] = start_date
                search_params['end_date'] = end_date
                break
        
        # Handle "upcoming" sessions
        for pattern in self.upcoming_patterns:
            match = re.search(pattern, query)
            if match:
                # Default to next 30 days
                days_ahead = 30
                
                # Check if a specific time period was mentioned
                if "next" in pattern:
                    # Try to extract the number of days/weeks/months
                    try:
                        number = int(match.group(1))
                        if "week" in match.group(0):
                            days_ahead = number * 7
                        elif "month" in match.group(0):
                            days_ahead = number * 30
                        else:  # days
                            days_ahead = number
                    except:
                        days_ahead = 30
                elif "today" in match.group(0):
                    days_ahead = 1
                elif "tomorrow" in match.group(0):
                    days_ahead = 2
                elif "this week" in match.group(0):
                    days_ahead = 7
                
                # Calculate the date range
                start_date = datetime.now()
                end_date = start_date + timedelta(days=days_ahead)
                
                search_params['start_date'] = start_date
                search_params['end_date'] = end_date
                break
        
        # If we have no specific parameters but query contains session-related terms,
        # attempt to extract generic search terms
        if not search_params and re.search(r'sessions?|workshops?|events?|training', query):
            # Extract potential search terms (excluding common words)
            words = query.split()
            stop_words = {'find', 'search', 'looking', 'session', 'sessions', 'workshop', 
                          'workshops', 'event', 'events', 'training', 'for', 'about', 'on', 
                          'the', 'a', 'an', 'by', 'with', 'in', 'i', 'me', 'my', 'can', 
                          'you', 'please', 'help', 'need', 'want', 'show'}
            
            potential_terms = [word for word in words if word not in stop_words and len(word) > 2]
            
            if potential_terms:
                search_term = ' '.join(potential_terms)
                # For generic searches, look in both title and description
                search_params['title'] = search_term
                search_params['description'] = search_term
        
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
            r'sessions?\s+(?:about|on|by|with)',
            r'are\s+there\s+(?:any\s+)?sessions?',
            r'host(?:ed)?\s+by',
            r'sessions?\s+(?:in|during|on)\s+\w+'
        ]
        
        for indicator in search_indicators:
            if re.search(indicator, query_lower):
                return True
        
        # If query contains multiple session-related patterns, it's likely a search
        pattern_count = 0
        
        for pattern_list in [self.host_patterns, self.title_patterns, 
                             self.description_patterns, self.date_patterns, 
                             self.recent_patterns, self.upcoming_patterns]:
            for pattern in pattern_list:
                if re.search(pattern, query_lower):
                    pattern_count += 1
                    break  # Count each category only once
        
        # If we match patterns from at least 2 categories, consider it a search query
        if pattern_count >= 2:
            return True
        
        return False
    
    def search_and_format_results(self, query):
        """Process a chat query, search for sessions, and format results as a response"""
        # Extract search parameters
        search_params = self.extract_search_params(query)
        
        if not search_params:
            return "I couldn't identify any specific search criteria in your question. Could you please specify what kind of sessions you're looking for? You can mention details like host name, topic, or date."
        
        # Perform the search
        results = self.session_search.search_sessions(search_params)
        
        # Format the response
        if not results:
            response = "I couldn't find any sessions matching your criteria. "
            
            # Explain what we searched for
            search_criteria = []
            if 'host' in search_params:
                search_criteria.append(f"host containing '{search_params['host']}'")
            if 'title' in search_params:
                search_criteria.append(f"title containing '{search_params['title']}'")
            if 'description' in search_params:
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
            response += f"**{i+1}. {title}**\n"
            
            # Add date if available
            if session_date:
                response += f"📅 Date: {session_date.strftime('%Y-%m-%d %H:%M')}\n"
            
            # Add host information
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host = host_users[0]
                response += f"👤 Host: {host.get('username', 'Unknown')}\n"
            
            # Add duration
            response += f"⏱️ Duration: {session.get('duration', 'N/A')}\n"
            
            # Add URL if available
            if 'external_url' in session and session['external_url']:
                response += f"🔗 [Join Session]({session['external_url']})\n"
            
            # Add separator between sessions
            if i < display_count - 1:
                response += "\n---\n\n"
        
        # Add note if we're not showing all results
        if len(results) > display_count:
            remaining = len(results) - display_count
            response += f"\n\nThere are {remaining} more sessions matching your criteria. You can view all results in the Search Sessions tab."
        
        return response