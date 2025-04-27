# asha/utils/improved_nlp_search.py
import re
import logging
from datetime import datetime, timedelta
import calendar
from typing import Dict, List, Any, Optional, Tuple, Set, Union
import traceback
import numpy as np
from utils.enhanced_vector_store import enhanced_vector_store
from utils.mcp_handler import mcp_session_manager
from utils.db import get_all_sessions

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("improved_nlp_search")

class ImprovedNLPSearch:
    """
    Advanced NLP-based search for session discovery in natural language conversations.
    
    Features:
    - Semantic understanding of natural language queries
    - Time expression parsing (next week, this month, etc.)
    - Improved entity extraction (people, topics, etc.)
    - Hybrid search combining semantic and keyword matching
    - Support for conversational context
    """
    
    def __init__(self):
        self.sessions = get_all_sessions()
        self.host_names = self._extract_host_names()
        self._initialize_vector_store()
        
        # Time-related patterns
        self.time_patterns = {
            'day': [
                r'(today|tomorrow|yesterday)',
                r'(this|next|last) day',
                r'in (\d+) days?'
            ],
            'week': [
                r'(this|next|last) week',
                r'in (\d+) weeks?',
                r'(\d+) weeks? (ago|from now)'
            ],
            'month': [
                r'(this|next|last) month',
                r'in (\d+) months?',
                r'(\d+) months? (ago|from now)',
                r'(january|february|march|april|may|june|july|august|september|october|november|december)',
                r'(jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\.?'
            ],
            'year': [
                r'(this|next|last) year',
                r'in (\d+) years?',
                r'(\d+) years? (ago|from now)',
                r'(20\d\d)'  # 2000-2099
            ],
            'specific_date': [
                r'(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?',  # MM/DD/YYYY or DD/MM/YYYY
                r'(\d{1,2})(?:st|nd|rd|th)? of (january|february|march|april|may|june|july|august|september|october|november|december)',
                r'(january|february|march|april|may|june|july|august|september|october|november|december) (\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{2,4}))?'
            ]
        }
        
        # Directly referenceable hosts (known host names)
        self.direct_host_refs = set(name.lower() for name in self.host_names)
        
        # Common search query patterns
        self.search_patterns = [
            # Direct session requests
            r'find (sessions?|workshops?|events?)',
            r'search for (sessions?|workshops?|events?)',
            r'looking for (sessions?|workshops?|events?)',
            r'show (me |us )?(sessions?|workshops?|events?)',
            r'(sessions?|workshops?|events?) (about|on|with|by|related to)',
            r'(list|display) (sessions?|workshops?|events?)',
            
            # Topic-based queries
            r'(sessions?|workshops?|events?) (about|on|related to) ([a-z\s]+)',
            r'([a-z\s]+) (sessions?|workshops?|events?)',
            
            # Host-based queries
            r'(sessions?|workshops?|events?) (by|with|from|hosted by) ([a-z\s]+)',
            r'([a-z\s]+)\'s (sessions?|workshops?|events?)',  # Single quote
            r'([a-z\s]+)"s (sessions?|workshops?|events?)',   # Double quote
            
            # Time-based queries
            r'(sessions?|workshops?|events?) (in|during|on|for) ([a-z\s0-9]+)',
            r'upcoming (sessions?|workshops?|events?)',
            r'recent (sessions?|workshops?|events?)',
            r'past (sessions?|workshops?|events?)',
            
            # Special case for simple host queries
            r'^by ([a-z\s]+)$'
        ]
        
        # Patterns for categorizing queries
        self.query_categories = {
            'host': [
                r'(by|with|from|hosted by) ([a-z\s]+)',
                r'sessions? (?:of|by|with|from) ([a-z\s]+)',
                r'([a-z\s]+)\'s sessions?',  # Single quote
                r'([a-z\s]+)"s sessions?'    # Double quote
            ],
            'topic': [
                r'(?:about|on|related to) ([a-z\s]+)',
                r'([a-z\s]+) sessions?',
                r'sessions? (?:about|on|regarding) ([a-z\s]+)'
            ],
            'time': [
                r'(?:in|during|on|for) ([a-z\s0-9]+)',
                r'(?:upcoming|recent|past|future|scheduled|planned)'
            ]
        }
        
        # Month name mappings
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def _extract_host_names(self) -> List[str]:
        """Extract unique host names from all sessions"""
        host_names = set()
        
        for session in self.sessions:
            host_users = session.get('host_user', [])
            for host in host_users:
                if isinstance(host, dict) and 'username' in host:
                    host_names.add(host['username'])
        
        return sorted(list(host_names))
    
    def _initialize_vector_store(self):
        """Initialize the vector store with all sessions if needed"""
        # Check if vector store is already initialized with enough items
        if hasattr(enhanced_vector_store, 'items') and len(enhanced_vector_store.items) >= len(self.sessions):
            logger.info("Vector store already contains sufficient sessions")
            return
            
        # Prepare session texts for indexing
        logger.info(f"Initializing vector store with {len(self.sessions)} sessions")
        texts = []
        
        for session in self.sessions:
            # Combine relevant fields for better search
            title = session.get('session_title', '')
            description = self._extract_description_text(session.get('description', ''))
            
            # Get host information
            host_info = ""
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_info = host_users[0].get('username', '')
            
            # Combine for full-text search
            session_text = f"Title: {title} Description: {description} Host: {host_info}"
            texts.append(session_text)
        
        # Create the index
        enhanced_vector_store.create_index(texts, self.sessions)
        logger.info("Vector store initialized successfully")


    def _extract_host_param(self, query_lower: str, search_params: Dict[str, Any]):
        """Extract host information from query"""
        # Special case for simple "by [name]" queries
        if query_lower.startswith("by ") and len(query_lower.split()) <= 3:
            host_name = query_lower[3:].strip()
            best_match = self._find_best_host_match(host_name)
            if best_match:
                search_params['host'] = best_match
                logger.info(f"Found host (simple by pattern): {best_match}")
                return
            else:
                search_params['host'] = host_name
                logger.info(f"Using exact host name: {host_name}")
                return
                
        # Check for known host names in the query
        for host in self.host_names:
            host_lower = host.lower()
            if host_lower in query_lower:
                # Check that it's not a substring of a larger word
                host_parts = host_lower.split()
                if len(host_parts) > 1 or query_lower.find(host_lower + 's') == -1:
                    search_params['host'] = host
                    logger.info(f"Found host (direct match): {host}")
                    return
                    
        # Check for host patterns
        for pattern in self.query_categories['host']:
            match = re.search(pattern, query_lower)
            if match:
                host_part = match.group(match.lastindex)  # Get the capture group with the host name
                host_part = host_part.strip()
                
                # Find best match from known hosts
                best_match = self._find_best_host_match(host_part)
                if best_match:
                    search_params['host'] = best_match
                    logger.info(f"Found host (pattern match): {best_match}")
                    return
                elif len(host_part) > 2:  # Only use if substantial
                    search_params['host'] = host_part
                    logger.info(f"Using extracted host name: {host_part}")
                    return
    
    def _find_best_host_match(self, partial_name: str) -> Optional[str]:
        """Find the best matching host name for a partial name"""
        if not partial_name or len(partial_name.strip()) < 2:
            return None
            
        partial_name = partial_name.lower()
        
        # First check for exact matches
        for host in self.host_names:
            if host.lower() == partial_name:
                return host
                
        # Check for first name matches
        first_name_matches = []
        for host in self.host_names:
            host_parts = host.lower().split()
            if host_parts and host_parts[0] == partial_name:
                first_name_matches.append(host)
                
        if first_name_matches:
            return first_name_matches[0]
            
        # Check for contains matches
        contains_matches = []
        for host in self.host_names:
            if partial_name in host.lower():
                # Score by how close the length is
                score = 1.0 - (abs(len(host) - len(partial_name)) / max(len(host), len(partial_name)))
                contains_matches.append((host, score))
                
        if contains_matches:
            # Return the highest scoring match
            contains_matches.sort(key=lambda x: x[1], reverse=True)
            return contains_matches[0][0]
            
        return None
    
    def _extract_time_params(self, query_lower: str, search_params: Dict[str, Any]):
        """Extract time-related parameters from query"""
        # Check for common time patterns
        for time_type, patterns in self.time_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    date_range = self._parse_time_expression(match.group(0), time_type)
                    if date_range:
                        start_date, end_date = date_range
                        search_params['start_date'] = start_date
                        search_params['end_date'] = end_date
                        logger.info(f"Found time range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                        return
        
        # Check for "upcoming" / "recent" / "past" keywords
        if 'upcoming' in query_lower or 'future' in query_lower or 'scheduled' in query_lower:
            now = datetime.now()
            end_date = now + timedelta(days=365)  # Up to a year in the future
            search_params['start_date'] = now
            search_params['end_date'] = end_date
            logger.info(f"Using upcoming time range: {now.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
        elif 'recent' in query_lower:
            now = datetime.now()
            start_date = now - timedelta(days=30)  # Past 30 days
            search_params['start_date'] = start_date
            search_params['end_date'] = now
            logger.info(f"Using recent time range: {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
            
        elif 'past' in query_lower:
            now = datetime.now()
            start_date = now - timedelta(days=365)  # Past year
            search_params['start_date'] = start_date
            search_params['end_date'] = now
            logger.info(f"Using past time range: {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    
    def _parse_time_expression(self, time_expr: str, time_type: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse a time expression into a date range
        
        Args:
            time_expr: The time expression string
            time_type: The type of time expression (day, week, month, year, specific_date)
            
        Returns:
            Tuple of (start_date, end_date) or None if parsing fails
        """
        now = datetime.now()
        time_expr = time_expr.lower()
        
        # Handle relative expressions like "this week", "next month", etc.
        if 'this' in time_expr:
            if time_type == 'day':
                # This day = today
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
            elif time_type == 'week':
                # This week = starting from most recent Monday
                days_since_monday = now.weekday()
                start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7) - timedelta(microseconds=1)
            elif time_type == 'month':
                # This month = current month
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if now.month == 12:
                    end_date = now.replace(year=now.year+1, month=1, day=1) - timedelta(microseconds=1)
                else:
                    end_date = now.replace(month=now.month+1, day=1) - timedelta(microseconds=1)
            elif time_type == 'year':
                # This year = current year
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(year=now.year+1, month=1, day=1) - timedelta(microseconds=1)
            else:
                return None
                
            return (start_date, end_date)
            
        elif 'next' in time_expr:
            if time_type == 'day':
                # Next day = tomorrow
                start_date = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
            elif time_type == 'week':
                # Next week = starting from next Monday
                days_to_next_monday = 7 - now.weekday()
                start_date = (now + timedelta(days=days_to_next_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7) - timedelta(microseconds=1)
            elif time_type == 'month':
                # Next month
                if now.month == 12:
                    start_date = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    end_date = now.replace(year=now.year+1, month=2, day=1) - timedelta(microseconds=1)
                else:
                    start_date = now.replace(month=now.month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    if now.month == 11:  # December
                        end_date = now.replace(year=now.year+1, month=1, day=1) - timedelta(microseconds=1)
                    else:
                        end_date = now.replace(month=now.month+2, day=1) - timedelta(microseconds=1)
            elif time_type == 'year':
                # Next year
                start_date = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(year=now.year+2, month=1, day=1) - timedelta(microseconds=1)
            else:
                return None
                
            return (start_date, end_date)
            
        elif 'last' in time_expr:
            if time_type == 'day':
                # Last day = yesterday
                start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
            elif time_type == 'week':
                # Last week = previous Monday to Sunday
                days_since_monday = now.weekday()
                start_date = (now - timedelta(days=days_since_monday+7)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7) - timedelta(microseconds=1)
            elif time_type == 'month':
                # Last month
                if now.month == 1:
                    start_date = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                    end_date = now.replace(year=now.year, month=1, day=1) - timedelta(microseconds=1)
                else:
                    start_date = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    end_date = now.replace(month=now.month, day=1) - timedelta(microseconds=1)
            elif time_type == 'year':
                # Last year
                start_date = now.replace(year=now.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(year=now.year, month=1, day=1) - timedelta(microseconds=1)
            else:
                return None
                
            return (start_date, end_date)
            
        # Handle specific month names
        for month_name, month_num in self.month_names.items():
            if month_name in time_expr:
                # Default to current year if not specified
                year = now.year
                
                # Check if year is specified
                year_match = re.search(r'20\d\d', time_expr)
                if year_match:
                    year = int(year_match.group(0))
                
                # Create date range for the month
                start_date = datetime(year, month_num, 1, 0, 0, 0)
                
                # End date is start of next month
                if month_num == 12:
                    end_date = datetime(year+1, 1, 1) - timedelta(microseconds=1)
                else:
                    end_date = datetime(year, month_num+1, 1) - timedelta(microseconds=1)
                    
                return (start_date, end_date)
                
        # Handle numeric dates
        if time_type == 'specific_date':
            # Try to parse MM/DD/YYYY or DD/MM/YYYY format
            date_match = re.search(r'(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?', time_expr)
            if date_match:
                first_num = int(date_match.group(1))
                second_num = int(date_match.group(2))
                year = now.year
                
                if date_match.group(3):  # Year specified
                    year_str = date_match.group(3)
                    if len(year_str) == 2:
                        year = 2000 + int(year_str)
                    else:
                        year = int(year_str)
                
                # Determine if MM/DD or DD/MM format - assume MM/DD if first num <= 12
                if first_num <= 12:
                    month, day = first_num, second_num
                else:
                    day, month = first_num, second_num
                    
                try:
                    start_date = datetime(year, month, day, 0, 0, 0)
                    end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
                    return (start_date, end_date)
                except ValueError:
                    # Invalid date
                    pass
        
        # Handle "in X days/weeks/months" format
        in_match = re.search(r'in (\d+) (day|days|week|weeks|month|months|year|years)', time_expr)
        if in_match:
            amount = int(in_match.group(1))
            unit = in_match.group(2)
            
            if 'day' in unit:
                start_date = (now + timedelta(days=amount)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(microseconds=1)
            elif 'week' in unit:
                start_date = (now + timedelta(days=amount*7)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7) - timedelta(microseconds=1)
            elif 'month' in unit:
                # Approximate month as 30 days
                start_date = (now + timedelta(days=amount*30)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=30) - timedelta(microseconds=1)
            elif 'year' in unit:
                # Add years
                start_date = now.replace(year=now.year+amount, hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date.replace(year=start_date.year+1) - timedelta(microseconds=1)
            else:
                return None
                
            return (start_date, end_date)
            
        # Handle "X days/weeks/months ago" format
        ago_match = re.search(r'(\d+) (day|days|week|weeks|month|months|year|years) ago', time_expr)
        if ago_match:
            amount = int(ago_match.group(1))
            unit = ago_match.group(2)
            
            if 'day' in unit:
                end_date = now
                start_date = (now - timedelta(days=amount)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif 'week' in unit:
                end_date = now
                start_date = (now - timedelta(days=amount*7)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif 'month' in unit:
                # Approximate month as 30 days
                end_date = now
                start_date = (now - timedelta(days=amount*30)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif 'year' in unit:
                # Subtract years
                end_date = now
                start_date = now.replace(year=now.year-amount, hour=0, minute=0, second=0, microsecond=0)
            else:
                return None
                
            return (start_date, end_date)
            
        # No match found
        return None
    
    def _extract_description_text(self, description) -> str:
        """Extract plain text from structured description"""
        if not description:
            return ""
            
        # Handle strings that look like JSON
        if isinstance(description, str) and description.strip().startswith('{'):
            try:
                import json
                desc_obj = json.loads(description)
                
                # Try to extract text from Lexical JSON structure
                if 'root' in desc_obj and 'children' in desc_obj['root']:
                    text_parts = []
                    self._extract_text_from_lexical(desc_obj['root'], text_parts)
                    return ' '.join(text_parts)
            except:
                # If parsing fails, return the original string
                return description
        
        # Return as string
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
    
    def is_search_query(self, query: str) -> bool:
        """
        Determine if a query is a session search request
        
        Args:
            query: The query text
            
        Returns:
            True if this is a session search query, False otherwise
        """
        query_lower = query.lower()
        
        # Quick keyword check first
        if 'session' in query_lower or 'workshop' in query_lower or 'event' in query_lower:
            return True
            
        # Check for special pattern "by [name]"
        if query_lower.startswith("by ") and len(query_lower.split()) <= 3:
            return True
            
        # Check for direct host mentions from our known hosts
        for host in self.direct_host_refs:
            if host in query_lower and len(host) > 3:  # Only match substantial host names
                return True
                
        # Check more complex search patterns
        for pattern in self.search_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False
    
    def extract_search_params(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract search parameters from a natural language query
        
        Args:
            query: The natural language query
            user_id: Optional user ID for context-aware search
            
        Returns:
            Dictionary of search parameters
        """
        search_params = {}
        
        # Normalize the query
        query_lower = query.lower().strip()
        logger.info