# asha/engines/enhanced_career_guidance.py
import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ollama import generate_text
from utils.improved_chat_search import ImprovedChatSearchHandler
from components.enhanced_session_search import EnhancedSessionSearch
import config
import traceback

class EnhancedCareerGuidanceEngine:
    def __init__(self):
        # Define the system prompt with guidance guardrails
        self.system_prompt = """
        You are ASHA, a career guidance assistant specialized in helping women professionals.
        Your responses should:
        - Focus exclusively on career-related topics
        - Avoid gender stereotypes and biases
        - Provide practical, actionable advice
        - Reference best practices in professional development
        - Acknowledge when a question is outside your expertise
        - Keep responses concise and to the point (100-150 words maximum)
        
        When unsure, ask clarifying questions rather than making assumptions.
        """
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Track mentioned sessions for follow-up questions
        self.mentioned_sessions = []
        
        # Define off-topic patterns for quick classification
        self.off_topic_patterns = [
            r'\b(weather|temperature|forecast)\b',
            r'\b(sports|game|match|score)\b',
            r'\b(recipe|cook|food|meal)\b',
            r'\b(movie|film|show|watch)\b',
            r'\b(music|song|band|artist)\b',
        ]
        
        # Initialize session search handler
        self.session_search = EnhancedSessionSearch()
        self.chat_search_handler = ImprovedChatSearchHandler(self.session_search)
        print("Enhanced career guidance engine initialized with integrated session search")
        
        # Patterns for follow-up questions about sessions
        self.session_followup_patterns = [
            r'tell me (more|about) (that|the|this) session',
            r'more (details|info|information) (on|about) (that|the|this) session',
            r'what.*?(about|details of) (that|the|this) session',
            r'can i join (that|the|this) session',
            r'who.*?host.*(that|the|this) session',
            r'when.*?(that|the|this) session',
        ]
    
    def is_off_topic(self, query):
        """Quickly check if query is off-topic to avoid LLM call"""
        query_lower = query.lower()
        for pattern in self.off_topic_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
    def is_session_search_query(self, query):
        """Determine if a query is looking for sessions"""
        # Common session search keywords and patterns
        session_keywords = [
            'session', 'sessions', 'workshop', 'workshops', 
            'host', 'hosted', 'find', 'search', 'looking for'
        ]
        
        query_lower = query.lower()
        
        # Check for explicit session keywords
        for keyword in session_keywords:
            if keyword in query_lower:
                print(f"Detected session search query: '{query}' (matched: '{keyword}')")
                return True
                
        # If no direct match, use the more sophisticated handler
        if self.chat_search_handler.is_search_query(query):
            print(f"Detected session search query via pattern matching: '{query}'")
            return True
            
        return False
    
    def is_session_followup_query(self, query):
        """Check if this is a follow-up question about previously mentioned sessions"""
        if not self.mentioned_sessions:
            return False
            
        query_lower = query.lower()
        
        # Check if any follow-up patterns match
        for pattern in self.session_followup_patterns:
            if re.search(pattern, query_lower):
                print(f"Detected session follow-up query: '{query}'")
                return True
                
        # Check for session-specific references
        for session in self.mentioned_sessions:
            # Extract title for matching
            title = session.get('session_title', '').lower()
            if title and len(title) > 5:  # Only match on substantial titles
                # Create a regex that matches key parts of the title
                title_words = [word for word in title.split() if len(word) > 3]
                if title_words:
                    title_pattern = '|'.join(title_words)
                    if re.search(r'\b(' + title_pattern + r')\b', query_lower):
                        print(f"Detected reference to session '{title}' in query: '{query}'")
                        return True
        
        return False
    
    def handle_session_followup(self, query):
        """Handle follow-up questions about previously mentioned sessions"""
        if not self.mentioned_sessions:
            return None
            
        # For simplicity, assume the question is about the most recently mentioned session
        session = self.mentioned_sessions[-1]
        
        # Generate a response based on the specific question
        query_lower = query.lower()
        
        response = f"Regarding the '{session.get('session_title', 'session')}', "
        
        # Check what kind of information is being requested
        if 'join' in query_lower or 'attend' in query_lower or 'register' in query_lower:
            if 'external_url' in session and session['external_url']:
                response += f"you can join using this link: {session['external_url']}"
            else:
                response += "I don't have direct registration information. Please check the platform for registration details."
        
        elif 'host' in query_lower or 'presenter' in query_lower or 'speaker' in query_lower:
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host = host_users[0]
                response += f"it's hosted by {host.get('username', 'an unspecified host')}."
                if 'profile_url' in host and host['profile_url']:
                    response += f" You can view their profile at {host['profile_url']}."
            else:
                response += "I don't have information about the host."
        
        elif 'when' in query_lower or 'time' in query_lower or 'date' in query_lower:
            schedule = session.get('schedule', {})
            if schedule and 'start_time' in schedule:
                start_time = schedule['start_time']
                # Format might vary, so provide as is
                response += f"it's scheduled for {start_time}."
                if 'duration' in session:
                    response += f" The duration is {session.get('duration')}."
            else:
                response += "I don't have specific timing information for this session."
        
        else:
            # General information about the session
            response += "here's what I know:\n\n"
            
            # Title
            response += f"**Title**: {session.get('session_title', 'Untitled Session')}\n"
            
            # Host information
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host = host_users[0]
                response += f"**Host**: {host.get('username', 'Unknown')}\n"
            
            # Duration
            response += f"**Duration**: {session.get('duration', 'N/A')}\n"
            
            # Add description if available
            description = self.session_search._extract_text_from_description(session.get('description', ''))
            if description:
                response += f"**Description**: {description[:150]}...\n"
            
            # Add URL if available
            if 'external_url' in session and session['external_url']:
                response += f"\nYou can join this session at: {session['external_url']}"
        
        return response
    
    def process_query(self, query):
        """Process a user query and return a response."""
        try:
            # Add user query to conversation history
            self.conversation_history.append({"role": "user", "content": query})
            
            # Check if this is a follow-up question about sessions
            if self.is_session_followup_query(query):
                response = self.handle_session_followup(query)
                if response:
                    self.conversation_history.append({"role": "assistant", "content": response})
                    return response
            
            # Check if this is a session search query
            if self.is_session_search_query(query):
                print(f"Processing as session search: '{query}'")
                # Handle as a session search
                response = self.chat_search_handler.search_and_format_results(query)
                
                # Store referenced sessions for potential follow-up questions
                search_params = self.chat_search_handler.extract_search_params(query)
                if search_params:
                    results = self.session_search.search_sessions(search_params)
                    if results:
                        # Update mentioned sessions with search results (most recent first)
                        self.mentioned_sessions = results[:5] + self.mentioned_sessions
                        # Limit to prevent excessive growth
                        self.mentioned_sessions = self.mentioned_sessions[:10]
                
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            
            # Quick check if query is off-topic
            if self.is_off_topic(query):
                response = ("I'm focused on helping with career guidance for women professionals. "
                           "Could we discuss your professional development goals or challenges instead?")
                self.conversation_history.append({"role": "assistant", "content": response})
                return response
            
            # Limit history to recent messages to reduce context size
            recent_history = self.conversation_history[-6:]  # Only use last 3 exchanges
            
            # Construct the prompt with optimized history format
            conversation_text = ""
            for message in recent_history:
                role = "Human" if message["role"] == "user" else "ASHA"
                # Truncate very long messages to reduce context size
                content = message["content"]
                if len(content) > 500:
                    content = content[:500] + "..."
                conversation_text += f"{role}: {content}\n"
            
            # Generate response with reduced max_tokens
            prompt = conversation_text + "ASHA:"
            response = generate_text(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=800,  # Reduced from default
                temperature=0.6  # Slightly reduced for more deterministic responses
            )
            
            # Check if the response should include session recommendations
            # For career-related queries that don't explicitly ask for sessions but could benefit
            # from session recommendations
            should_recommend = False
            career_keywords = ['career', 'job', 'professional', 'skill', 'leadership', 'development',
                              'interview', 'resume', 'networking', 'mentor', 'transition']
            
            for keyword in career_keywords:
                if keyword in query.lower():
                    should_recommend = True
                    break
            
            if should_recommend:
                # Get related sessions
                recommendations = self.session_search.search_sessions({'description': query})[:2]
                
                if recommendations:
                    # Update mentioned sessions
                    self.mentioned_sessions = recommendations + self.mentioned_sessions
                    self.mentioned_sessions = self.mentioned_sessions[:10]
                    
                    # Add session recommendation
                    response += "\n\n**You might also be interested in these sessions:**\n\n"
                    for session in recommendations:
                        title = session.get('session_title', 'Untitled Session')
                        host_name = "Unknown Host"
                        host_users = session.get('host_user', [])
                        if host_users and len(host_users) > 0:
                            host_name = host_users[0].get('username', 'Unknown Host')
                        
                        response += f"- **{title}** (Host: {host_name})\n"
                    
                    response += "\nYou can ask me for more details about any of these sessions."
            
            # Add response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            print(f"Error processing query: {e}")
            traceback.print_exc()
            return "I'm having trouble processing your request. Could you please try asking a simpler question?"