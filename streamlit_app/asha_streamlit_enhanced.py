import streamlit as st
import requests
import json
import os
import random
from datetime import datetime
import re

# Set page configuration
st.set_page_config(
    page_title="ASHA - Career Guidance Assistant",
    page_icon="👩‍💼",
    layout="wide",  # Changed to wide for better use of space
    initial_sidebar_state="expanded"
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Define color scheme for consistent branding
COLORS = {
    "primary": "#6b46c1",  # Purple for main brand color
    "secondary": "#3182ce",  # Blue for links and accents
    "light_bg": "#f8f9fa",  # Light background
    "dark_text": "#2d3748",  # Dark text
    "success": "#48bb78",  # Green for success
    "info": "#4299e1",  # Light blue for info
    "user_bubble": "#e1f5fe",  # User message bubble
    "bot_bubble": "#f3e8ff"   # Assistant message bubble (light purple)
}

# Load sessions data
@st.cache_data
def load_sessions():
    try:
        with open("data/sessions.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading sessions: {e}")
        # Fallback to a placeholder session if file doesn't exist
        return [{
            "session_id": "1",
            "title": "Online vs in-person group discussion",
            "description": "Pros and cons of online and in-person group discussions",
            "host": "Udhaya C",
            "host_headline": "A Passionate Engineer",
            "date": "2025-04-23",
            "duration": "60 minutes",
            "format": "online",
            "topics": ["professional development", "communication", "networking", "remote work"],
            "skill_level": "all levels"
        }]

sessions = load_sessions()

def log_interaction(user_query, bot_response):
    """Log each interaction for later analysis."""
    log_file = f"logs/asha_interactions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "bot_response": bot_response,
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def compute_relevance_score(query, session):
    """Compute a more sophisticated relevance score between query and session."""
    query = query.lower()
    query_terms = re.findall(r'\b\w+\b', query)  # Extract words
    
    # Initialize scores for different fields
    title_score = 0
    description_score = 0
    topics_score = 0
    host_score = 0
    
    # Check title (higher weight)
    title_lower = session.get("title", "").lower()
    for term in query_terms:
        if term in title_lower:
            # Exact title match gets highest score
            if term == title_lower:
                title_score += 10
            else:
                title_score += 3
    
    # Check description (medium weight)
    description_lower = session.get("description", "").lower()
    for term in query_terms:
        if term in description_lower:
            description_score += 2
    
    # Check topics (medium weight)
    for topic in session.get("topics", []):
        topic_lower = topic.lower()
        for term in query_terms:
            if term in topic_lower:
                topics_score += 2
    
    # Check host (lower weight)
    host_lower = session.get("host", "").lower()
    for term in query_terms:
        if term in host_lower:
            host_score += 1
    
    # Combine scores with weights
    total_score = title_score + description_score + topics_score + host_score
    
    # Bonus for exact phrase matches (to handle multi-word queries better)
    if len(query_terms) > 1:
        phrase = " ".join(query_terms)
        if phrase in title_lower:
            total_score += 5
        if phrase in description_lower:
            total_score += 3
    
    return total_score

def find_relevant_sessions(query, num_sessions=3):
    """Find sessions relevant to the user's query using improved scoring."""
    # Skip relevance calculation for very short queries
    if len(query.strip()) < 3:
        return random.sample(sessions, min(num_sessions, len(sessions)))
    
    # Calculate scores for all sessions
    session_scores = []
    for session in sessions:
        score = compute_relevance_score(query, session)
        if score > 0:
            session_scores.append((session, score))
    
    # If no relevant sessions found, return random ones
    if not session_scores:
        return random.sample(sessions, min(num_sessions, len(sessions)))
    
    # Sort by relevance and return top sessions
    session_scores.sort(key=lambda x: x[1], reverse=True)
    return [session for session, score in session_scores[:num_sessions]]

def format_sessions_for_prompt(relevant_sessions):
    """Format session information for inclusion in the prompt."""
    if not relevant_sessions:
        return ""
        
    sessions_text = "Here are some relevant sessions you can mention:\n\n"
    
    for session in relevant_sessions:
        sessions_text += f"Session: {session['title']}\n"
        sessions_text += f"Description: {session['description']}\n"
        sessions_text += f"Host: {session['host']} ({session.get('host_headline', '')})\n"
        sessions_text += f"Format: {session.get('format', 'online')}\n"
        sessions_text += f"Topics: {', '.join(session.get('topics', []))}\n\n"
    
    return sessions_text

def categorize_query(query):
    """Categorize the user query to determine what kind of advice is needed."""
    query_lower = query.lower()
    
    categories = {
        "leadership": ["leader", "leadership", "manage", "management", "team", "supervise"],
        "networking": ["network", "connect", "relationship", "introduction", "contact"],
        "salary": ["salary", "compensation", "pay", "money", "raise", "negotiate", "promotion"],
        "job_search": ["job", "search", "interview", "resume", "cv", "application", "apply"],
        "workplace_issues": ["bias", "discrimination", "harassment", "toxic", "conflict"],
        "skills": ["skill", "learn", "training", "course", "certificate", "education", "degree"],
        "session_info": ["session", "workshop", "seminar", "event", "meeting", "discussion"]
    }
    
    # Check which categories match the query
    matched_categories = []
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in query_lower:
                matched_categories.append(category)
                break
    
    return matched_categories if matched_categories else ["general"]

def get_asha_response(user_message):
    """Get response from ASHA BOT via Ollama API with improved context."""
    # Categorize the query
    query_categories = categorize_query(user_message)
    
    # Find relevant sessions based on the query
    relevant_sessions = find_relevant_sessions(user_message)
    sessions_text = format_sessions_for_prompt(relevant_sessions)
    
    # Add guidance based on the query category
    category_guidance = ""
    if "leadership" in query_categories:
        category_guidance += "The user seems interested in leadership skills or management. Provide specific advice for women in leadership positions.\n\n"
    if "salary" in query_categories:
        category_guidance += "The user is asking about salary or compensation. Offer concrete negotiation tactics tailored for women professionals.\n\n"
    if "workplace_issues" in query_categories:
        category_guidance += "The user may be dealing with workplace challenges. Provide supportive, actionable strategies with empathy.\n\n"
    if "session_info" in query_categories:
        category_guidance += "The user is specifically asking about sessions. Prioritize the most relevant session recommendations.\n\n"
    
    # Add context to ensure consistent responses
    prompt = f"""You are ASHA, a career guidance assistant for women professionals.

{category_guidance}
{sessions_text}

The user asks: {user_message}

Remember to:
1. Provide specific, actionable advice for career development
2. If the user's question relates to any of the sessions above, recommend the most relevant specific sessions
3. Focus on career guidance for women professionals
4. Keep your responses concise and practical
5. Sign off with "ASHA - Advancing careers, empowering professionals."
"""
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "asha-bot",
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            bot_response = response.json()["response"]
            
            # Ensure response has signature
            if not bot_response.endswith("ASHA - Advancing careers, empowering professionals."):
                bot_response += "\n\nASHA - Advancing careers, empowering professionals."
            
            # Log the interaction
            log_interaction(user_message, bot_response)
            
            return bot_response
        else:
            return f"I'm sorry, I encountered an error (Status code: {response.status_code}). Please try again later. ASHA - Advancing careers, empowering professionals."
    
    except Exception as e:
        return f"I'm sorry, I encountered an error: {str(e)}. Please try again later. ASHA - Advancing careers, empowering professionals."

# Custom CSS for improved UI
st.markdown(f"""
<style>
    /* Main header styling */
    .main-header {{
        font-size: 2.5rem !important;
        color: {COLORS["primary"]};
        font-weight: 600;
        margin-bottom: 5px;
    }}
    .sub-header {{
        font-size: 1.2rem !important;
        color: {COLORS["dark_text"]};
        margin-bottom: 20px;
    }}
    
    /* Input field styling */
    .stTextInput>div>div>input {{
        border-radius: 20px;
        border: 1px solid {COLORS["primary"]};
        padding: 10px 15px;
        font-size: 1rem;
    }}
    
    /* Message bubbles */
    .user-bubble {{
        background-color: {COLORS["user_bubble"]};
        color: {COLORS["dark_text"]};
        padding: 15px;
        border-radius: 20px 20px 5px 20px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 85%;
        margin-left: auto;
        margin-right: 10px;
    }}
    .bot-bubble {{
        background-color: {COLORS["bot_bubble"]};
        color: {COLORS["dark_text"]};
        padding: 15px;
        border-radius: 20px 20px 20px 5px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        max-width: 85%;
        margin-right: auto;
        margin-left: 10px;
    }}
    .signature {{
        font-style: italic;
        font-size: 0.8em;
        opacity: 0.8;
        margin-top: 8px;
        color: {COLORS["primary"]};
    }}
    
    /* Session cards */
    .session-card {{
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #eee;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .session-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}
    .session-title {{
        font-weight: bold;
        color: {COLORS["primary"]};
        font-size: 1.1rem;
        margin-bottom: 5px;
    }}
    .session-host {{
        font-style: italic;
        color: {COLORS["dark_text"]};
        margin-bottom: 8px;
    }}
    .session-description {{
        margin-bottom: 8px;
        font-size: 0.9rem;
    }}
    .topic-tag {{
        background-color: {COLORS["light_bg"]};
        color: {COLORS["primary"]};
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-right: 5px;
        display: inline-block;
        margin-bottom: 5px;
        border: 1px solid {COLORS["primary"]}40;
    }}
    
    /* Suggestion chips */
    .suggestion-chip {{
        background-color: {COLORS["light_bg"]};
        color: {COLORS["primary"]};
        padding: 8px 15px;
        border-radius: 18px;
        margin: 5px;
        font-size: 0.9rem;
        display: inline-block;
        cursor: pointer;
        border: 1px solid {COLORS["primary"]}40;
        transition: background-color 0.2s ease, color 0.2s ease;
    }}
    .suggestion-chip:hover {{
        background-color: {COLORS["primary"]};
        color: white;
    }}
    
    /* Sidebar */
    .sidebar-header {{
        color: {COLORS["primary"]};
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 15px;
    }}
    .sidebar-subheader {{
        color: {COLORS["dark_text"]};
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: 20px;
        margin-bottom: 10px;
    }}
    
    /* Make the chat container scrollable with fixed height */
    .chat-container {{
        height: 500px;
        overflow-y: auto;
        padding: 15px;
        background-color: #f9f9f9;
        border-radius: 10px;
        margin-bottom: 20px;
    }}
    
    /* Custom button styling */
    .stButton>button {{
        border-radius: 20px;
        background-color: {COLORS["primary"]};
        color: white;
        font-weight: 500;
    }}
    .stButton>button:hover {{
        background-color: {COLORS["primary"]}dd;
    }}
</style>
""", unsafe_allow_html=True)

# App layout with improved structure
# Create a more structured layout
col1, col2 = st.columns([2, 1])

with col1:
    # App header
    st.markdown('<p class="main-header">ASHA - Career Guidance Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Advancing careers, empowering professionals</p>', unsafe_allow_html=True)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm ASHA (Advancement Support & Help Assistant), your specialized assistant for career guidance. I can help you with professional development, recommend sessions, and provide career advice tailored for women professionals. How can I assist you today?"}
        ]
    
    # Display chat messages in a scrollable container
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-bubble">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                # Format bot message to separate signature
                content = message["content"]
                if "ASHA - Advancing careers, empowering professionals." in content:
                    main_content = content.replace("ASHA - Advancing careers, empowering professionals.", "").strip()
                    st.markdown(f'<div class="bot-bubble">{main_content}<div class="signature">ASHA - Advancing careers, empowering professionals.</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="bot-bubble">{content}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Dynamic suggestion chips based on conversation context
    if st.session_state.messages[-1]["role"] == "assistant":
        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        # Generate contextual suggestions based on the last assistant message
        last_message = st.session_state.messages[-1]["content"].lower()
        
        if "leadership" in last_message:
            suggestions = [
                "How to improve leadership skills?", 
                "Women leadership challenges", 
                "Leading diverse teams"
            ]
        elif "salary" in last_message or "negotiation" in last_message:
            suggestions = [
                "Salary negotiation tips", 
                "How to ask for a promotion", 
                "Benefits negotiation"
            ]
        elif "session" in last_message:
            suggestions = [
                "Tell me more about this session", 
                "Other recommended sessions", 
                "How to apply these insights"
            ]
        else:
            suggestions = [
                "Career advancement strategies", 
                "Networking for women professionals", 
                "Work-life balance tips"
            ]
        
        # Display suggestion chips
        col1, col2, col3 = st.columns(3)
        if col1.button(suggestions[0], key="suggestion_1"):
            st.session_state.messages.append({"role": "user", "content": suggestions[0]})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestions[0])
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        if col2.button(suggestions[1], key="suggestion_2"):
            st.session_state.messages.append({"role": "user", "content": suggestions[1]})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestions[1])
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        if col3.button(suggestions[2], key="suggestion_3"):
            st.session_state.messages.append({"role": "user", "content": suggestions[2]})
            with st.spinner("ASHA is thinking..."):
                response = get_asha_response(suggestions[2])
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # User input
    user_input = st.text_input("Your question:", key="user_input", placeholder="Type your question here...")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("ASHA is thinking..."):
            response = get_asha_response(user_input)
            st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with col2:
    # Sidebar-like content in the second column
    st.markdown('<div class="sidebar-header">About ASHA</div>', unsafe_allow_html=True)
    st.markdown("""
    ASHA is a specialized AI assistant focused on providing tailored career guidance for women professionals.
    """)
    
    st.markdown('<div class="sidebar-subheader">Key Capabilities</div>', unsafe_allow_html=True)
    st.markdown("""
    • Career guidance specific to women
    • Session recommendations
    • Leadership development advice
    • Networking strategies
    """)
    
    # Featured sessions section with improved cards
    st.markdown('<div class="sidebar-subheader">Featured Sessions</div>', unsafe_allow_html=True)
    if sessions:
        # Display 3 sessions (random or relevant to last query if available)
        if len(st.session_state.messages) > 1:
            last_user_message = next((m["content"] for m in reversed(st.session_state.messages) 
                                     if m["role"] == "user"), "")
            featured_sessions = find_relevant_sessions(last_user_message, 3)
        else:
            # Random sessions for first load
            featured_sessions = random.sample(sessions, min(3, len(sessions)))
        
        for session in featured_sessions:
            st.markdown(f"""
            <div class="session-card">
                <div class="session-title">{session['title']}</div>
                <div class="session-host">Hosted by: {session['host']}</div>
                <div class="session-description">{session['description'][:100]}...</div>
                <div>
                    {"".join(f'<span class="topic-tag">{topic}</span>' for topic in session.get('topics', [])[:3])}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Optional feedback mechanism
    st.markdown('<div class="sidebar-subheader">Feedback</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    if cols[0].button("👍 Helpful"):
        st.success("Thank you for your feedback!")
    
    if cols[1].button("👎 Not Helpful"):
        feedback = st.text_area("What can we improve?", "")
        if st.button("Submit Feedback"):
            log_file = "logs/feedback.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "feedback": feedback,
                    "last_message": st.session_state.messages[-1]["content"] if st.session_state.messages else ""
                }) + "\n")
            st.success("Thank you for your feedback! We'll use it to improve ASHA.")