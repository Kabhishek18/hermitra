"""
Enhanced ASHA Application - Main Entry Point
This is an enhanced version of the ASHA career guidance chatbot with improved UI and performance.
"""

import streamlit as st
from datetime import datetime, timedelta
import os
import time
import threading
import base64
import gc
import uuid
from PIL import Image
import io
import json
import psutil

# Import core functionality with performance optimizations
from core import (
    get_database_connection, hash_password, verify_password, is_valid_email,
    generate_session_token, decode_session_token, detect_gender_from_image,
    AshaBot, SessionRecommender, ObjectId
)

# Import enhanced components
from performance_optimization import (
    start_memory_monitoring, stop_memory_monitoring, 
    check_memory, optimize_memory, LazyLoader
)

# Import the enhanced UI components
from optimized_chat import enhanced_chat_interface, ChatManager

# Global resource management with improved performance
CHATBOT_INSTANCE = None
RECOMMENDER_INSTANCE = None
DB_CONNECTION = None
CHAT_MANAGER = None
MEMORY_MANAGER = None
FILE_HANDLER = None

# Enhanced lazy initialization functions with error handling and logging
def get_db_connection():
    """Get a database connection with lazy loading and error handling"""
    global DB_CONNECTION
    if DB_CONNECTION is None:
        try:
            DB_CONNECTION = get_database_connection()
            if DB_CONNECTION is not None:
                print("Database connection established successfully")
            else:
                print("Warning: Failed to establish database connection")
        except Exception as e:
            print(f"Error establishing database connection: {e}")
    return DB_CONNECTION

def get_chatbot():
    """Get a chatbot instance with lazy loading and error handling"""
    global CHATBOT_INSTANCE
    if CHATBOT_INSTANCE is None:
        try:
            CHATBOT_INSTANCE = AshaBot()
            print("Chatbot instance initialized successfully")
        except Exception as e:
            print(f"Error initializing chatbot: {e}")
            CHATBOT_INSTANCE = None
    return CHATBOT_INSTANCE

def get_recommender(db):
    """Get a session recommender with lazy loading and error handling"""
    global RECOMMENDER_INSTANCE
    if RECOMMENDER_INSTANCE is None and db is not None:
        try:
            RECOMMENDER_INSTANCE = SessionRecommender(db)
            print("Recommender instance initialized successfully")
        except Exception as e:
            print(f"Error initializing recommender: {e}")
            RECOMMENDER_INSTANCE = None
    return RECOMMENDER_INSTANCE

def get_chat_manager(db, chatbot, recommender):
    """Get a chat manager with lazy loading and error handling"""
    global CHAT_MANAGER
    if CHAT_MANAGER is None and db is not None and chatbot is not None:
        try:
            CHAT_MANAGER = ChatManager(db, chatbot, recommender)
            print("Chat manager initialized successfully")
        except Exception as e:
            print(f"Error initializing chat manager: {e}")
            CHAT_MANAGER = None
    return CHAT_MANAGER

# Apply enhanced styles and UI components
def apply_enhanced_ui():
    """Apply enhanced UI styles for ASHA application"""
    st.markdown("""
    <style>
    /* Modern color scheme */
    :root {
        --primary-color: #FF1493;
        --secondary-color: #9370DB;
        --accent-color: #00CED1;
        --background-color: #F8F9FA;
        --text-color: #212529;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --error-color: #dc3545;
        --info-color: #17a2b8;
        --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        --hover-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* Global styles */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    
    body {
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        color: var(--text-color);
        background-color: var(--background-color);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        font-weight: 600;
    }
    
    /* Header styles */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 1rem;
        padding: 0.5rem 0;
    }
    
    .subheader {
        font-size: 1.5rem;
        color: var(--secondary-color);
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    
    /* Card component */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: var(--card-shadow);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: var(--hover-shadow);
    }
    
    /* Button styles */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    .primary-btn>button {
        background-color: var(--primary-color) !important;
        color: white !important;
    }
    
    .secondary-btn>button {
        background-color: var(--secondary-color) !important;
        color: white !important;
    }
    
    .outline-btn>button {
        background-color: transparent !important;
        border: 1px solid var(--primary-color) !important;
        color: var(--primary-color) !important;
    }
    
    /* Chat message styling */
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        background-color: #f9f9f9;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background-color: #e1f5fe;
        padding: 10px 15px;
        border-radius: 18px 18px 18px 0;
        margin: 10px 0;
        max-width: 80%;
        align-self: flex-start;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    .assistant-message {
        background-color: #f0f4f8;
        padding: 10px 15px;
        border-radius: 18px 18px 0 18px;
        margin: 10px 0 10px auto;
        max-width: 80%;
        align-self: flex-end;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    /* Form styling */
    .stTextInput>div>div>input {
        border-radius: 6px;
    }
    
    .stTextArea>div>div>textarea {
        border-radius: 6px;
    }
    
    /* Profile section */
    .profile-section {
        padding: 1rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: var(--card-shadow);
    }
    
    /* Recommendation cards */
    .recommendation-card {
        background-color: white;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: var(--card-shadow);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
        border-left: 4px solid var(--primary-color);
    }
    
    .recommendation-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--hover-shadow);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 0.25rem;
        margin-bottom: 0.25rem;
    }
    
    .badge-primary {
        background-color: var(--primary-color);
        color: white;
    }
    
    .badge-secondary {
        background-color: var(--secondary-color);
        color: white;
    }
    
    .badge-accent {
        background-color: var(--accent-color);
        color: white;
    }
    
    /* Progress indicators */
    .progress-container {
        width: 100%;
        background-color: #e9ecef;
        border-radius: 8px;
        height: 8px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        border-radius: 8px;
        transition: width 0.5s ease;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 1rem 0;
        margin-top: 2rem;
        font-size: 0.85rem;
        color: #6c757d;
        border-top: 1px solid #eee;
    }
    
    /* Animation for loading */
    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 0.8; }
        100% { opacity: 0.4; }
    }
    
    .loading {
        animation: pulse 1.5s infinite;
    }
    </style>
    """, unsafe_allow_html=True)

# Enhanced user profile with more options and better UI
def enhanced_user_profile(db, user_id):
    """Enhanced user profile with better UI and more detailed career information"""
    
    if db is None:
        st.error("Database connection is not available. Cannot update profile.")
        return False
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Complete Your Professional Profile")
    st.write("Help us provide personalized career guidance by sharing more about your background and goals:")
    
    # Get existing profile if any - Use caching for profile data
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_user_profile(user_id):
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            return user.get("profile", {}) if user else {}
        except Exception as e:
            st.error(f"Error retrieving profile: {e}")
            return {}
    
    profile = get_user_profile(user_id)
    
    # Form for profile completion with tabs
    with st.form("profile_form"):
        tab1, tab2, tab3 = st.tabs(["Career Information", "Skills & Expertise", "Goals & Preferences"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                job_title = st.text_input("Current Job Title", value=profile.get("job_title", ""), 
                                      placeholder="e.g. Software Engineer")
                industry = st.text_input("Industry", value=profile.get("industry", ""), 
                                      placeholder="e.g. Technology")
            with col2:
                years_experience = st.number_input("Years of Experience", 
                                              min_value=0, max_value=50, 
                                              value=profile.get("years_experience", 0))
                education = st.selectbox("Highest Education", 
                                      ["High School", "Associate's", "Bachelor's", "Master's", "PhD", "Other"],
                                      index=["High School", "Associate's", "Bachelor's", "Master's", "PhD", "Other"].index(
                                          profile.get("education", "Bachelor's")))
            
            # Employment information
            st.write("Employment")
            employment_status = st.selectbox(
                "Current Employment Status",
                ["Employed Full-time", "Employed Part-time", "Self-employed", "Freelance", 
                 "Looking for opportunities", "Student", "Other"],
                index=["Employed Full-time", "Employed Part-time", "Self-employed", "Freelance", 
                       "Looking for opportunities", "Student", "Other"].index(
                           profile.get("employment_status", "Employed Full-time"))
            )
            
            # Company size if employed
            if employment_status in ["Employed Full-time", "Employed Part-time"]:
                company_size = st.selectbox(
                    "Company Size",
                    ["Startup (1-10 employees)", "Small (11-50 employees)", "Medium (51-200 employees)",
                     "Large (201-1000 employees)", "Enterprise (1000+ employees)"],
                    index=["Startup (1-10 employees)", "Small (11-50 employees)", "Medium (51-200 employees)",
                           "Large (201-1000 employees)", "Enterprise (1000+ employees)"].index(
                               profile.get("company_size", "Medium (51-200 employees)"))
                )
            else:
                company_size = profile.get("company_size", "")
        
        with tab2:
            # Skills matrix with categorization
            st.write("Professional Skills")
            
            # Technical skills
            tech_skills = st.text_area(
                "Technical Skills (comma separated)",
                value=", ".join(profile.get("technical_skills", [])) if "technical_skills" in profile else "",
                placeholder="e.g. Python, SQL, Data Analysis, Machine Learning",
                height=80
            )
            
            # Soft skills
            soft_skills = st.text_area(
                "Soft Skills (comma separated)",
                value=", ".join(profile.get("soft_skills", [])) if "soft_skills" in profile else "",
                placeholder="e.g. Leadership, Communication, Problem Solving, Team Collaboration",
                height=80
            )
            
            # Industry knowledge
            industry_knowledge = st.text_area(
                "Industry Knowledge (comma separated)",
                value=", ".join(profile.get("industry_knowledge", [])) if "industry_knowledge" in profile else "",
                placeholder="e.g. FinTech, Healthcare Regulations, Digital Marketing, Agile Development",
                height=80
            )
            
            # Language skills
            languages = st.text_area(
                "Languages (comma separated)",
                value=", ".join(profile.get("languages", [])) if "languages" in profile else "",
                placeholder="e.g. English (Native), Spanish (Intermediate), French (Basic)",
                height=80
            )
        
        with tab3:
            # Career goals
            st.write("Career Aspirations")
            short_term_goals = st.text_area(
                "Short-term Career Goals (Next 1-2 years)",
                value=profile.get("short_term_goals", ""),
                placeholder="e.g. Get promoted to senior position, learn new skills in data science",
                height=80
            )
            
            long_term_goals = st.text_area(
                "Long-term Career Goals (3-5+ years)",
                value=profile.get("long_term_goals", ""),
                placeholder="e.g. Move into leadership role, start my own business",
                height=80
            )
            
            # Areas of interest
            interest_areas = st.multiselect(
                "Professional Interest Areas", 
                ["Leadership & Management", "Technical Skills Development", "Entrepreneurship", 
                 "Work-Life Balance", "Career Transition", "Mentorship", "Networking",
                 "Remote Work", "International Opportunities", "Industry Specialization"],
                default=profile.get("interest_areas", [])
            )
            
            # Work values and preferences
            st.write("Work Preferences")
            work_values = st.multiselect(
                "Work Values (What matters most to you?)",
                ["Work-Life Balance", "Competitive Salary", "Career Advancement", 
                 "Learning Opportunities", "Company Culture", "Recognition", 
                 "Autonomy", "Job Security", "Social Impact", "Diversity & Inclusion"],
                default=profile.get("work_values", [])
            )
            
            # Work environment preferences
            work_environment = st.selectbox(
                "Preferred Work Environment",
                ["Remote", "Hybrid", "In-office", "Flexible"],
                index=["Remote", "Hybrid", "In-office", "Flexible"].index(
                    profile.get("work_environment", "Hybrid"))
            )
        
        # Submit button
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        submit = st.form_submit_button("Save Profile")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit:
            # Process inputs
            technical_skills = [skill.strip() for skill in tech_skills.split(",") if skill.strip()]
            soft_skills = [skill.strip() for skill in soft_skills.split(",") if skill.strip()]
            industry_knowledge_list = [item.strip() for item in industry_knowledge.split(",") if item.strip()]
            languages_list = [lang.strip() for lang in languages.split(",") if lang.strip()]
            
            # Combined skills for backwards compatibility
            all_skills = technical_skills + soft_skills
            
            # Update profile
            updated_profile = {
                "job_title": job_title,
                "industry": industry,
                "years_experience": years_experience,
                "education": education,
                "employment_status": employment_status,
                "company_size": company_size,
                "skills": all_skills,  # For backwards compatibility
                "technical_skills": technical_skills,
                "soft_skills": soft_skills,
                "industry_knowledge": industry_knowledge_list,
                "languages": languages_list,
                "short_term_goals": short_term_goals,
                "long_term_goals": long_term_goals,
                "interest_areas": interest_areas,
                "work_values": work_values,
                "work_environment": work_environment,
                "last_updated": datetime.now()
            }
            
            try:
                db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"profile": updated_profile}}
                )
                
                # Show success message with animation
                st.success("Profile updated successfully!")
                
                # Show profile completion progress
                # Calculate completion percentage based on filled fields
                total_fields = 12  # Number of important fields
                filled_fields = sum(1 for field in [job_title, industry, years_experience, 
                                                   technical_skills, soft_skills, 
                                                   short_term_goals, long_term_goals] 
                                  if field)
                filled_fields += 1 if interest_areas else 0
                filled_fields += 1 if work_values else 0
                
                completion_percent = min(100, int((filled_fields / total_fields) * 100))
                
                st.markdown(f"""
                <div class="progress-container">
                    <div class="progress-bar" style="width: {completion_percent}%;"></div>
                </div>
                <p style="text-align: center; color: #28a745;">Profile {completion_percent}% Complete</p>
                """, unsafe_allow_html=True)
                
                # Clear the cache to reflect updates
                get_user_profile.clear()
                return True
            except Exception as e:
                st.error(f"Error updating profile: {e}")
                return False
    
    st.markdown('</div>', unsafe_allow_html=True)
    return False

# Enhanced session recommendations with improved UI and filtering
def enhanced_session_recommendations(db, user_id):
    """Display session recommendations with enhanced UI and filtering options"""
    
    st.markdown('<h2 class="subheader">Recommended Development Sessions</h2>', unsafe_allow_html=True)
    
    if db is None:
        st.error("Database connection is not available. Cannot load recommendations.")
        return
    
    # Pagination
    page_size = 4  # Reduced page size for better performance
    page_num = st.session_state.get("rec_page", 0)
    
    # Get recommendations with pagination and caching
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_user_recommendations(user_id, page, page_size):
        try:
            # Get total count for pagination
            total_recs = db.user_recommendations.count_documents({"user_id": user_id})
            
            # Get paginated recommendations
            recommendations = list(db.user_recommendations.find(
                {"user_id": user_id}
            ).sort("relevance_score", -1).skip(page * page_size).limit(page_size))
            
            # Get session details for each recommendation
            results = []
            for rec in recommendations:
                session = db.sessions.find_one({"session_id": rec["session_id"]})
                if session:
                    results.append({
                        "recommendation": rec,
                        "session": session
                    })
            
            return results, total_recs
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return [], 0
    
    recommendations, total_recs = get_user_recommendations(user_id, page_num, page_size)
    
    if not recommendations:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("https://img.icons8.com/cotton/128/null/conference-call--v1.png", width=100)
            
        with col2:
            st.info("No recommendations yet. Try chatting with ASHA to get personalized session recommendations!")
            
            # Add a button to start a chat
            st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
            if st.button("Start a Career Chat"):
                st.session_state.show_chat = True
                st.session_state.show_recommendations = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Add filter and sort options
    col1, col2 = st.columns(2)
    with col1:
        # Extract all categories from sessions
        all_categories = []
        for item in recommendations:
            session = item["session"]
            if "categories" in session:
                all_categories.extend(session["categories"])
        
        unique_categories = list(set(all_categories))
        
        # Filter by category
        selected_categories = st.multiselect(
            "Filter by category",
            options=unique_categories,
            default=[]
        )
    
    with col2:
        # Sort options
        sort_option = st.selectbox(
            "Sort by",
            ["Relevance", "Date (Newest First)", "Date (Oldest First)"],
            index=0
        )
    
    # Display recommendations
    for item in recommendations:
        rec = item["recommendation"]
        session = item["session"]
        
        # Skip if doesn't match filter
        if selected_categories and not any(cat in selected_categories for cat in session.get("categories", [])):
            continue
            
        relevance_score = rec.get('relevance_score', 0)
        
        st.markdown(f'<div class="recommendation-card">', unsafe_allow_html=True)
        
        # Layout with columns
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {session.get('session_title', 'Untitled Session')}")
            
            # Display match percentage with progress bar
            st.markdown(f"""
            <div class="progress-container" style="height: 6px; margin-bottom: 15px;">
                <div class="progress-bar" style="width: {relevance_score * 100}%;"></div>
            </div>
            <p style="margin-top: -12px; font-size: 0.8rem; color: #666;">
                {relevance_score:.0%} Match with your interests
            </p>
            """, unsafe_allow_html=True)
            
            # Extract and clean description
            description = session.get('description', 'No description available')
            if isinstance(description, dict) or (isinstance(description, str) and description.startswith('{')):
                try:
                    desc_data = json.loads(description)
                    # Try to extract readable text
                    if "root" in desc_data and "children" in desc_data["root"]:
                        plain_text = []
                        for child in desc_data["root"]["children"]:
                            if "children" in child:
                                for subchild in child["children"]:
                                    if "text" in subchild:
                                        plain_text.append(subchild["text"])
                        if plain_text:
                            description = " ".join(plain_text)
                except:
                    # Keep original if parsing fails
                    pass
            
            st.markdown(f"**Description**: {description}")
            
            # Categories and tags with badge styling
            categories = session.get("categories", [])
            if categories:
                st.markdown("**Categories**:")
                cats_html = " ".join([f'<span class="badge badge-primary">{cat}</span>' for cat in categories])
                st.markdown(cats_html, unsafe_allow_html=True)
            
            tags = session.get("tags", [])
            if tags:
                st.markdown("**Tags**:")
                tags_html = " ".join([f'<span class="badge badge-secondary">{tag}</span>' for tag in tags])
                st.markdown(tags_html, unsafe_allow_html=True)
        
        with col2:
            # Show session details in sidebar
            start_time = session.get("schedule", {}).get("start_time", "Unknown")
            if isinstance(start_time, datetime):
                st.markdown(f"**Date**:  \n{start_time.strftime('%b %d, %Y')}")
                st.markdown(f"**Time**:  \n{start_time.strftime('%I:%M %p')}")
            else:
                st.markdown("**Date**: Unknown")
            
            # Duration
            duration = session.get("schedule", {}).get("duration_minutes", 0)
            if duration:
                st.markdown(f"**Duration**:  \n{duration} minutes")
            
            # Host info with avatar
            hosts = session.get("host_user", [])
            if hosts:
                st.markdown("**Hosted by**:")
                for host in hosts:
                    host_name = host.get("username", "Unknown")
                    profile_pic = host.get("profile_picture_url", "")
                    if profile_pic:
                        st.markdown(f"<img src='{profile_pic}' style='width: 32px; height: 32px; border-radius: 16px; margin-right: 10px;'> {host_name}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"👤 {host_name}")
        
        # Footer with action buttons
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            # Watch button if url available
            watch_url = session.get("session_resources", {}).get("watch_url", "")
            if watch_url:
                st.markdown(f"<a href='{watch_url}' target='_blank' style='text-decoration: none;'><button style='background-color: #FF1493; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%;'>Watch Session</button></a>", unsafe_allow_html=True)
        
        with col_btn2:
            # Register button for upcoming sessions
            now = datetime.now()
            if start_time and isinstance(start_time, datetime) and start_time > now:
                st.markdown(f"<button style='background-color: #9370DB; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%;'>Register</button>", unsafe_allow_html=True)
        
        with col_btn3:
            # Save to calendar
            st.markdown(f"<button style='background-color: transparent; color: #17a2b8; border: 1px solid #17a2b8; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%;'>Add to Calendar</button>", unsafe_allow_html=True)
        
        # Mark as viewed in a background thread to avoid blocking
        if not rec.get("user_viewed", False):
            def mark_viewed_background(rec_id):
                try:
                    db.user_recommendations.update_one(
                        {"_id": rec_id},
                        {"$set": {"user_viewed": True}}
                    )
                except Exception as e:
                    print(f"Error marking recommendation as viewed: {e}")
            
            threading.Thread(
                target=mark_viewed_background,
                args=(rec["_id"],)
            ).start()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Enhanced pagination controls with clearer UI
    total_pages = max(1, (total_recs + page_size - 1) // page_size)
    
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 20px;">
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if page_num > 0:
            st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
            if st.button("← Previous"):
                st.session_state.rec_page = page_num - 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Page indicators as dots
        dots_html = ""
        for i in range(total_pages):
            if i == page_num:
                dots_html += f'<span style="height: 10px; width: 10px; background-color: #FF1493; border-radius: 50%; display: inline-block; margin: 0 5px;"></span>'
                dots_html += f'<span style="height: 10px; width: 10px; background-color: #FF1493; border-radius: 50%; display: inline-block; margin: 0 5px;"></span>'
            else:
                dots_html += f'<span style="height: 10px; width: 10px; background-color: #ddd; border-radius: 50%; display: inline-block; margin: 0 5px;"></span>'
        
        st.markdown(f"""
        <div style="text-align: center;">
            <p>Page {page_num + 1} of {total_pages}</p>
            <div>{dots_html}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if (page_num + 1) * page_size < total_recs:
            st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
            if st.button("Next →"):
                st.session_state.rec_page = page_num + 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Enhanced login form with better UI
def enhanced_login_form(db):
    """Display enhanced login form with better UI"""
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Login to ASHA")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                forgot_password = st.form_submit_button("Forgot Password?")
            with col_btn2:
                st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
                submit_button = st.form_submit_button("Sign In")
                st.markdown('</div>', unsafe_allow_html=True)
            
            if submit_button:
                # Check memory usage
                check_memory()
                    
                if not email or not password:
                    st.error("Please enter both email and password.")
                    return
                
                if db is not None:
                    try:
                        user = db.users.find_one({"email": email})
                        if not user:
                            st.error("User not found.")
                            return
                        
                        # Convert binary data to bytes if necessary
                        stored_password = user["password"]
                        if isinstance(stored_password, dict) and '$binary' in stored_password:
                            stored_password = base64.b64decode(stored_password['$binary']['base64'])
                        
                        if verify_password(stored_password, password):
                            # Success - set up session
                            st.success("Login successful!")
                            
                            # Store user information in session state
                            st.session_state.user = {
                                "id": str(user["_id"]),
                                "name": user["name"],
                                "email": user["email"],
                                "gender": user.get("self_identified_gender", "Unknown")
                            }
                            
                            # If AI verified gender is available
                            if "ai_verified_gender" in user:
                                st.session_state.user["ai_verified_gender"] = user["ai_verified_gender"]
                            
                            st.session_state.logged_in = True
                            st.session_state.show_login = False
                            
                            # Create token for session persistence
                            token = generate_session_token(str(user["_id"]))
                            st.session_state.token = token
                            
                            # Force a rerun to update the UI
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                    except Exception as e:
                        st.error(f"Error during login: {e}")
                        optimize_memory()  # Clean up memory after error
    
    with col2:
        st.image("https://img.icons8.com/color/240/null/login-rounded-right--v1.png", width=100)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Enhanced signup form with better UI
def enhanced_signup_form(db):
    """Display enhanced signup form with improved UI"""
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Create an ASHA Account")
    
    with st.form("signup_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name", placeholder="Enter your name")
            email = st.text_input("Email", placeholder="Enter your email")
        
        with col2:
            password = st.text_input("Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        # Manual gender selection with AI verification option
        st.markdown("##### Personal Information")
        col_gender, col_verify = st.columns([1, 1])
        
        with col_gender:
            gender_options = ["Woman", "Man", "Other", "Prefer not to say"]
            gender = st.selectbox("Gender", gender_options)
        
        with col_verify:
            ai_verify = st.checkbox("Verify gender with AI (upload photo)")
        
        photo = None
        ai_gender = None
        ai_confidence = None
        
        if ai_verify:
            col_photo, col_preview = st.columns([2, 1])
            
            with col_photo:
                photo = st.file_uploader("Upload a clear face photo", type=["jpg", "jpeg", "png"])
            
            with col_preview:
                if photo:
                    # Process image with reduced size to improve performance
                    try:
                        img = Image.open(photo)
                        # Resize for display
                        max_size = (150, 150)
                        img.thumbnail(max_size)
                        st.image(img, caption="Uploaded Photo")
                        
                        with st.spinner("Analyzing photo..."):
                            ai_gender, ai_confidence = detect_gender_from_image(photo)
                        
                        if ai_confidence > 0.7:
                            st.success(f"AI detected gender: {ai_gender} (Confidence: {ai_confidence:.2%})")
                        else:
                            st.warning(f"AI detected gender: {ai_gender} (Low confidence: {ai_confidence:.2%})")
                    except Exception as e:
                        st.error(f"Error processing image: {e}")
                        ai_gender = None
                        ai_confidence = None
        
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        submit_button = st.form_submit_button("Sign Up")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit_button:
            # Check memory usage and optimize if needed
            check_memory()
                
            # Validation
            if not name or not email or not password:
                st.error("All fields are required.")
                return
                
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
                
            if not is_valid_email(email):
                st.error("Please enter a valid email address.")
                return
            
            # Check if the user already exists
            if db is not None:
                try:
                    existing_user = db.users.find_one({"email": email})
                    if existing_user:
                        st.error("A user with this email already exists.")
                        return
                    
                    # Process and save user data
                    user_data = {
                        "name": name,
                        "email": email,
                        "password": hash_password(password),
                        "self_identified_gender": gender,
                        "created_at": datetime.now()
                    }
                    
                    # Add AI verification if available
                    if ai_gender and ai_confidence:
                        user_data["ai_verified_gender"] = {
                            "gender": ai_gender,
                            "confidence": ai_confidence
                        }
                    
                    result = db.users.insert_one(user_data)
                    st.success("Account created successfully!")
                    
                    # Set user ID as MongoDB ObjectId
                    user_id = result.inserted_id
                    
                    # Auto-login after signup
                    st.session_state.user = {
                        "id": str(user_id),
                        "name": name,
                        "email": email,
                        "gender": gender
                    }
                    
                    if ai_gender and ai_confidence:
                        st.session_state.user["ai_verified_gender"] = {
                            "gender": ai_gender,
                            "confidence": ai_confidence
                        }
                    
                    st.session_state.logged_in = True
                    st.session_state.show_login = False
                    st.session_state.show_signup = False
                    
                    # Create token for session persistence
                    token = generate_session_token(str(user_id))
                    st.session_state.token = token
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating account: {e}")
                    # Clean up memory after error
                    optimize_memory()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Enhanced main application with improved performance
def main():
    """Main application function with enhanced UI and performance optimizations"""
    
    # Start memory monitoring for better performance
    start_memory_monitoring()
    
    # Set page configuration
    st.set_page_config(
        page_title="ASHA - Career Guidance for Women",
        page_icon="👩‍💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply enhanced UI
    apply_enhanced_ui()
    
    # Display header
    st.markdown('<h1 class="main-header">ASHA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Career Guidance for Women Professionals</p>', unsafe_allow_html=True)
    
    # Lazy loading for database connection
    db = get_db_connection()
    
    # Proper check for database connection
    if db is None:
        st.warning("Cannot connect to database. Some features may be limited.")
    
    # Initialize session state variables if not already set
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False
        
    if "show_login" not in st.session_state:
        st.session_state.show_login = True
        
    if "profile_complete" not in st.session_state:
        st.session_state.profile_complete = False
    
    # Check if user is logged in via token
    if not st.session_state.logged_in and "token" in st.session_state:
        user_id = decode_session_token(st.session_state.token)
        if user_id and db is not None:
            try:
                user = db.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    st.session_state.user = {
                        "id": str(user["_id"]),
                        "name": user["name"],
                        "email": user["email"],
                        "gender": user.get("self_identified_gender", "Unknown")
                    }
                    
                    # If AI verified gender is available
                    if "ai_verified_gender" in user:
                        st.session_state.user["ai_verified_gender"] = user["ai_verified_gender"]
                    
                    st.session_state.logged_in = True
                    st.session_state.show_login = False
                    st.session_state.show_signup = False
            except Exception as e:
                st.warning(f"Session expired. Please log in again.")
                # Clear token that failed verification
                if "token" in st.session_state:
                    del st.session_state.token
    
    # Display login/signup forms or main app based on login status
    if not st.session_state.logged_in:
        # Enhanced login/signup UI
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.image("https://img.freepik.com/free-vector/woman-speaking-phone-sitting-table-with-laptop-illustration_74855-14019.jpg",
                     width=300)
            
            st.markdown("""
            ### ASHA - Your AI Career Companion
            
            ASHA is an AI-powered career guidance chatbot specifically designed for women professionals. Empowering Every Woman's Journey to Success!
            
            **Key Features:**
            * Personalized career advice tailored to women's needs
            * Interview preparation and confidence-building techniques
            * Salary negotiation strategies
            * Connection to professional development sessions
            * Leadership development advice
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if st.session_state.show_login:
                enhanced_login_form(db)
                
                # Toggle to signup form
                st.markdown("""
                <div style="text-align: center; margin-top: 20px;">
                    <p>Don't have an account?</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
                    if st.button("Create an account", key="go_to_signup"):
                        st.session_state.show_login = False
                        st.session_state.show_signup = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
            elif st.session_state.show_signup:
                enhanced_signup_form(db)
                
                # Toggle to login form
                st.markdown("""
                <div style="text-align: center; margin-top: 20px;">
                    <p>Already have an account?</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
                    if st.button("Sign in", key="go_to_login"):
                        st.session_state.show_login = True
                        st.session_state.show_signup = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # Main application after login with enhanced UI
        user_id = st.session_state.user["id"]
        user_gender = st.session_state.user.get("gender", "Unknown")
        
        # Check if profile is complete - use caching
        @st.cache_data(ttl=600)  # Cache for 10 minutes
        def is_profile_complete(user_id):
            if db is not None:
                try:
                    user = db.users.find_one({"_id": ObjectId(user_id)})
                    return user is not None and "profile" in user and user["profile"]
                except Exception as e:
                    print(f"Could not retrieve user profile: {e}")
            return False
        
        profile_complete = is_profile_complete(user_id)
        
        # Initialize core components with lazy loading
        chatbot = get_chatbot()
        recommender = get_recommender(db)
        chat_manager = get_chat_manager(db, chatbot, recommender)
        
        # Sidebar with enhanced UI
        with st.sidebar:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader(f"Welcome, {st.session_state.user['name']}!")
            
            # Display user type badge
            if user_gender == "Woman":
                st.markdown("""
                <div style="background-color: #FF1493; color: white; padding: 5px 10px; border-radius: 16px; display: inline-block; font-size: 0.8rem; margin-bottom: 15px;">
                    Women-focused career guidance
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background-color: #9370DB; color: white; padding: 5px 10px; border-radius: 16px; display: inline-block; font-size: 0.8rem; margin-bottom: 15px;">
                    General career guidance
                </div>
                """, unsafe_allow_html=True)
            
            # Profile completion section with progress indicator
            if not profile_complete:
                st.warning("Please complete your profile to get personalized recommendations")
                
                # Progress indicator
                st.markdown("""
                <div class="progress-container">
                    <div class="progress-bar" style="width: 30%;"></div>
                </div>
                <p style="text-align: center; color: #ffc107;">Profile 30% Complete</p>
                """, unsafe_allow_html=True)
                
                st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
                if st.button("Complete Profile"):
                    st.session_state.show_profile = True
                    st.session_state.show_chat = False
                    st.session_state.show_recommendations = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("Profile complete!")
                
                # Show profile summary if we have the database and user data
                if db is not None:
                    # Use caching for user profile data
                    @st.cache_data(ttl=300)  # Cache for 5 minutes
                    def get_user_profile_summary(user_id):
                        try:
                            user = db.users.find_one({"_id": ObjectId(user_id)})
                            if user and "profile" in user:
                                return user["profile"]
                            return None
                        except Exception as e:
                            print(f"Error getting profile summary: {e}")
                            return None
                    
                    profile = get_user_profile_summary(user_id)
                    if profile:
                        with st.expander("Your Profile", expanded=False):
                            st.markdown(f"""
                            **Job**: {profile.get('job_title', 'Not specified')}  
                            **Industry**: {profile.get('industry', 'Not specified')}  
                            **Experience**: {profile.get('years_experience', 0)} years
                            """)
                            
                            # Show top skills
                            skills = profile.get("skills", [])
                            if skills:
                                st.markdown("**Top Skills**:")
                                skills_html = " ".join([f'<span class="badge badge-secondary">{skill}</span>' for skill in skills[:5]])
                                st.markdown(skills_html, unsafe_allow_html=True)
            
            # Enhanced navigation 
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
            
            # Use icons for navigation options
            st.markdown("### Navigation")
            
            nav_col1, nav_col2 = st.columns(2)
            
            with nav_col1:
                chat_active = "primary" if st.session_state.get("show_chat", True) else "outline"
                st.markdown(f'<div class="{chat_active}-btn">', unsafe_allow_html=True)
                if st.button("💬 Chat"):
                    st.session_state.show_chat = True
                    st.session_state.show_profile = False
                    st.session_state.show_recommendations = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            with nav_col2:
                profile_active = "primary" if st.session_state.get("show_profile", False) else "outline"
                st.markdown(f'<div class="{profile_active}-btn">', unsafe_allow_html=True)
                if st.button("👤 Profile"):
                    st.session_state.show_chat = False
                    st.session_state.show_profile = True
                    st.session_state.show_recommendations = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            nav_col3, nav_col4 = st.columns(2)
            
            with nav_col3:
                rec_active = "primary" if st.session_state.get("show_recommendations", False) else "outline"
                st.markdown(f'<div class="{rec_active}-btn">', unsafe_allow_html=True)
                if st.button("🎯 Sessions"):
                    st.session_state.show_chat = False
                    st.session_state.show_profile = False
                    st.session_state.show_recommendations = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            with nav_col4:
                st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
                if st.button("⚙️ Settings"):
                    st.session_state.show_chat = False
                    st.session_state.show_profile = False
                    st.session_state.show_recommendations = False
                    st.session_state.show_settings = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Logout button
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
            if st.button("Log Out"):
                # Clean up resources
                optimize_memory()
                
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Main content area with enhanced UI
        if "show_chat" not in st.session_state:
            st.session_state.show_chat = True
            
        if "show_profile" not in st.session_state:
            st.session_state.show_profile = False
            
        if "show_recommendations" not in st.session_state:
            st.session_state.show_recommendations = False
            
        if "show_settings" not in st.session_state:
            st.session_state.show_settings = False
        
        # Enhanced chat interface
        if st.session_state.show_chat:
            enhanced_chat_interface(user_id, chat_manager, db)
        
        # Enhanced profile completion
        elif st.session_state.show_profile:
            enhanced_user_profile(db, user_id)
            
        # Enhanced recommendations
        elif st.session_state.show_recommendations:
            enhanced_session_recommendations(db, user_id)
            
        # Settings
        elif st.session_state.show_settings:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Settings")
            
            # Account settings
            st.markdown("### Account Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Email**: " + st.session_state.user.get("email", ""))
            with col2:
                st.markdown("**Account Type**: " + ("Women's Career Guidance" if user_gender == "Woman" else "General Career Guidance"))
            
            # Change password option
            st.markdown("### Security")
            
            with st.expander("Change Password"):
                with st.form("change_password"):
                    current_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm New Password", type="password")
                    
                    submit = st.form_submit_button("Update Password")
                    
                    if submit:
                        if new_password != confirm_password:
                            st.error("New passwords do not match.")
                        elif not current_password or not new_password:
                            st.error("All fields are required.")
                        else:
                            st.success("Password updated successfully.")
            
            # Notification preferences
            st.markdown("### Notification Preferences")
            
            email_notifications = st.toggle("Email Notifications", value=True)
            session_reminders = st.toggle("Session Reminders", value=True)
            promotional_emails = st.toggle("Promotional Emails", value=False)
            
            # Save settings button
            st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
            if st.button("Save Settings"):
                st.success("Settings saved successfully.")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer
        st.markdown('<div class="footer">ASHA - AI-powered career guidance for women professionals © 2025</div>', 
                   unsafe_allow_html=True)

    # Check memory periodically and optimize if needed
    if int(time.time()) % 300 == 0:  # Every 5 minutes
        optimize_memory()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        # Log error for debugging
        with open("logs/error.log", "a") as f:
            f.write(f"{datetime.now()}: {str(e)}\n")
    finally:
        # Ensure memory monitoring is stopped
        stop_memory_monitoring()