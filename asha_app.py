"""
ASHA - Optimized AI-powered career guidance chatbot for women professionals.
This enhanced version features multi-threading, improved file handling, and memory optimization.
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

# Import core functionality with performance optimizations
from core import (
    get_database_connection, hash_password, verify_password, is_valid_email,
    generate_session_token, decode_session_token, detect_gender_from_image,
    AshaBot, SessionRecommender, ObjectId
)

# Import optimized components
from optimized_chat import chat_interface, ChatManager
from performance_optimization import (
    start_memory_monitoring, stop_memory_monitoring, 
    check_memory, optimize_memory, LazyLoader
)

# Global resource management
CHATBOT_INSTANCE = None
RECOMMENDER_INSTANCE = None
DB_CONNECTION = None
CHAT_MANAGER = None

# Lazy initialization functions
def get_db_connection():
    """Get a database connection with lazy loading"""
    global DB_CONNECTION
    if DB_CONNECTION is None:
        DB_CONNECTION = get_database_connection()
    return DB_CONNECTION

def get_chatbot():
    """Get a chatbot instance with lazy loading"""
    global CHATBOT_INSTANCE
    if CHATBOT_INSTANCE is None:
        CHATBOT_INSTANCE = AshaBot()
    return CHATBOT_INSTANCE

def get_recommender(db):
    """Get a session recommender with lazy loading"""
    global RECOMMENDER_INSTANCE
    if RECOMMENDER_INSTANCE is None and db is not None:
        RECOMMENDER_INSTANCE = SessionRecommender(db)
    return RECOMMENDER_INSTANCE

def get_chat_manager(db, chatbot, recommender):
    """Get a chat manager with lazy loading"""
    global CHAT_MANAGER
    if CHAT_MANAGER is None:
        CHAT_MANAGER = ChatManager(db, chatbot, recommender)
    return CHAT_MANAGER

# User profile functions with performance optimization
def complete_user_profile(db, user_id):
    """Complete user profile with career information"""
    if db is None:
        st.error("Database connection is not available. Cannot update profile.")
        return False
        
    st.subheader("Complete Your Profile")
    st.write("To help us provide personalized career guidance, please tell us more about yourself:")
    
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
    
    # Form for profile completion
    with st.form("profile_form"):
        job_title = st.text_input("Current Job Title", profile.get("job_title", ""))
        industry = st.text_input("Industry", profile.get("industry", ""))
        years_experience = st.number_input("Years of Experience", min_value=0, value=profile.get("years_experience", 0))
        
        # Skills
        skills_input = st.text_area("Your Skills (comma separated)", 
                                    ", ".join(profile.get("skills", [])) if "skills" in profile else "")
        
        # Career goals
        career_goals_input = st.text_area("Career Goals (comma separated)",
                                         ", ".join(profile.get("career_goals", [])) if "career_goals" in profile else "")
        
        # Interests
        interests_input = st.text_area("Professional Interests (comma separated)",
                                      ", ".join(profile.get("interests", [])) if "interests" in profile else "")
        
        submit = st.form_submit_button("Save Profile")
        
        if submit:
            # Process inputs
            skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
            career_goals = [goal.strip() for goal in career_goals_input.split(",") if goal.strip()]
            interests = [interest.strip() for interest in interests_input.split(",") if interest.strip()]
            
            # Update profile
            updated_profile = {
                "job_title": job_title,
                "industry": industry,
                "years_experience": years_experience,
                "skills": skills,
                "career_goals": career_goals,
                "interests": interests
            }
            
            try:
                db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"profile": updated_profile}}
                )
                st.success("Profile updated successfully!")
                # Clear the cache to reflect updates
                get_user_profile.clear()
                return True
            except Exception as e:
                st.error(f"Error updating profile: {e}")
                return False
    
    return False

# User interface components with performance optimization
def signup_form(db):
    """Display signup form for new users"""
    st.header("Signup for ASHA")
    
    with st.form("signup_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        # Manual gender selection with AI verification option
        gender_options = ["Woman", "Man", "Other", "Prefer not to say"]
        gender = st.selectbox("Gender", gender_options)
        
        # Option to verify gender using AI
        ai_verify = st.checkbox("Verify gender with AI (upload photo)")
        
        photo = None
        ai_gender = None
        ai_confidence = None
        
        if ai_verify:
            photo = st.file_uploader("Upload a clear face photo", type=["jpg", "jpeg", "png"])
            
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
                    
                    st.info(f"AI detected gender: {ai_gender} (Confidence: {ai_confidence:.2%})")
                except Exception as e:
                    st.error(f"Error processing image: {e}")
                    ai_gender = None
                    ai_confidence = None
        
        submit_button = st.form_submit_button("Sign Up")
        
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
                
                try:
                    result = db.users.insert_one(user_data)
                    st.success("Account created successfully! Please log in.")
                    
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

def login_form(db):
    """Display login form for existing users"""
    st.header("Login to ASHA")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Log In")
        
        if submit_button:
            # Check memory usage
            check_memory()
                
            if not email or not password:
                st.error("Please enter both email and password.")
                return
            
            if db is not None:
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

def session_recommendations_view(db, user_id):
    """Display session recommendations with pagination and improved performance"""
    st.header("Recommended Sessions For You")
    
    if db is None:
        st.error("Database connection is not available. Cannot load recommendations.")
        return
        
    # Pagination
    page_size = 5
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
        st.info("No recommendations yet. Try chatting with ASHA to get personalized session recommendations!")
        
        # Add a button to start a chat
        if st.button("Start a Career Chat"):
            st.session_state.show_chat = True
            st.session_state.show_recommendations = False
            st.rerun()
            
        return
        
    # Display recommendations
    for item in recommendations:
        rec = item["recommendation"]
        session = item["session"]
        
        with st.expander(f"{session.get('session_title', 'Untitled Session')} ({rec['relevance_score']:.2%} match)"):
            # Extract and clean description
            description = session.get('description', 'No description available')
            if isinstance(description, dict) or (isinstance(description, str) and description.startswith('{')):
                try:
                    import json
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
            
            st.write(f"**Description**: {description}")
            
            # Show session details
            start_time = session.get("schedule", {}).get("start_time", "Unknown")
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime("%Y-%m-%d %H:%M")
            else:
                start_time_str = "Unknown"
                
            st.write(f"**Date**: {start_time_str}")
            
            # Show host if available
            hosts = session.get("host_user", [])
            if hosts:
                host_names = [host.get("username", "Unknown") for host in hosts]
                st.write(f"**Host(s)**: {', '.join(host_names)}")
            
            # Show tags if available
            tags = session.get("tags", [])
            if tags:
                st.write(f"**Tags**: {', '.join(tags)}")
            
            # Watch button if url available
            watch_url = session.get("session_resources", {}).get("watch_url", "")
            if watch_url:
                st.markdown(f"[Watch Session]({watch_url})")
            
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
    
    # Pagination controls
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if page_num > 0:
            if st.button("← Previous"):
                st.session_state.rec_page = page_num - 1
                st.rerun()
    
    with col2:
        total_pages = (total_recs + page_size - 1) // page_size
        st.write(f"Page {page_num + 1} of {max(1, total_pages)}")
    
    with col3:
        if (page_num + 1) * page_size < total_recs:
            if st.button("Next →"):
                st.session_state.rec_page = page_num + 1
                st.rerun()

def main():
    """Main application function with performance optimization"""
    # Start memory monitor
    start_memory_monitoring()
    
    st.set_page_config(
        page_title="ASHA - Career Guidance for Women",
        page_icon="👩‍💼",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #FF1493;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #9370DB;
        margin-bottom: 0.5rem;
    }
    .footer {
        text-align: center;
        color: #888;
        font-size: 0.8rem;
        margin-top: 3rem;
    }
    /* Performance optimization - reduce the layout shifts */
    .stButton button {
        min-height: 2.5rem;
        width: 100%;
    }
    /* Improve form performance */
    .stForm > div {
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">ASHA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subheader">Career Guidance for Women Professionals</p>', unsafe_allow_html=True)
    
    # Lazy loading for database connection
    db = get_db_connection()
    
    # Proper check for database connection
    if db is None:
        st.error("Cannot connect to database. Please check your MongoDB connection.")
        st.info("You can still view the application interface but functionality will be limited.")
    
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
                st.warning(f"Error verifying login token: {e}")
    
    # Display login/signup forms or main app based on login status
    if not st.session_state.logged_in:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image("https://img.freepik.com/free-vector/woman-speaking-phone-sitting-table-with-laptop-illustration_74855-14019.jpg",
                     width=300, caption="ASHA - Your Career Companion")
            
            st.markdown("""
            ASHA is an AI-powered career guidance chatbot specifically designed for women professionals. Empowering Every Woman's Journey to Success!
            
            **Key Features:**
            * Personalized career advice tailored to women's needs
            * Interview preparation and confidence-building techniques
            * Salary negotiation strategies
            * Connection to professional development sessions
            * Leadership development advice
            """)
        
        with col2:
            if st.button("Log In" if st.session_state.show_signup else "Sign Up"):
                st.session_state.show_login = not st.session_state.show_login
                st.session_state.show_signup = not st.session_state.show_signup
                st.rerun()
            
            if st.session_state.show_login:
                login_form(db)
                
                if st.button("Create an account"):
                    st.session_state.show_login = False
                    st.session_state.show_signup = True
                    st.rerun()
                    
            elif st.session_state.show_signup:
                signup_form(db)
                
                if st.button("Already have an account?"):
                    st.session_state.show_login = True
                    st.session_state.show_signup = False
                    st.rerun()
    
    else:
        # Main application after login
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
                    st.warning(f"Could not retrieve user profile: {e}")
            return False
        
        profile_complete = is_profile_complete(user_id)
        
        # Initialize core components with lazy loading
        chatbot = get_chatbot()
        recommender = get_recommender(db)
        chat_manager = get_chat_manager(db, chatbot, recommender)
        
        # Sidebar
        with st.sidebar:
            st.subheader(f"Welcome, {st.session_state.user['name']}!")
            st.write(f"Account type: {'Women-focused' if user_gender == 'Woman' else 'General'} career guidance")
            
            # Profile completion section
            if not profile_complete:
                st.warning("Please complete your profile to get personalized recommendations")
                if st.button("Complete Profile"):
                    st.session_state.show_profile = True
                    st.session_state.show_chat = False
                    st.session_state.show_recommendations = False
                    st.rerun()
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
                        with st.expander("Your Profile"):
                            st.write(f"**Job Title**: {profile.get('job_title', 'Not specified')}")
                            st.write(f"**Industry**: {profile.get('industry', 'Not specified')}")
                            st.write(f"**Experience**: {profile.get('years_experience', 0)} years")
                            
                            skills = profile.get("skills", [])
                            if skills:
                                st.write("**Skills**: " + ", ".join(skills))
            
            # Navigation
            st.divider()
            navigation = st.radio(
                "Navigation",
                ["Chat with ASHA", "My Profile", "Session Recommendations"]
            )
            
            if navigation == "Chat with ASHA":
                st.session_state.show_chat = True
                st.session_state.show_profile = False
                st.session_state.show_recommendations = False
            elif navigation == "My Profile":
                st.session_state.show_chat = False
                st.session_state.show_profile = True
                st.session_state.show_recommendations = False
            elif navigation == "Session Recommendations":
                st.session_state.show_chat = False
                st.session_state.show_profile = False
                st.session_state.show_recommendations = True
            
            # Logout button
            if st.button("Log Out"):
                # Clean up resources
                optimize_memory()
                
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # Main content area
        if "show_chat" not in st.session_state:
            st.session_state.show_chat = True
            
        if "show_profile" not in st.session_state:
            st.session_state.show_profile = False
            
        if "show_recommendations" not in st.session_state:
            st.session_state.show_recommendations = False
        
        # Chat interface with multi-threading and improved performance
        if st.session_state.show_chat:
            chat_interface(user_id, chat_manager, db)
        
        # Profile completion
        elif st.session_state.show_profile:
            if db is not None:
                complete_user_profile(db, user_id)
            else:
                st.error("Database connection required to update profile")
            
        # Recommendations with pagination
        elif st.session_state.show_recommendations:
            session_recommendations_view(db, user_id)
        
        # Footer
        st.markdown('<div class="footer">ASHA - AI-powered career guidance for women professionals © 2025</div>', 
                   unsafe_allow_html=True)

    # Check memory periodically
    if int(time.time()) % 300 == 0:  # Every 5 minutes
        optimize_memory()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        # Ensure memory monitoring is stopped
        stop_memory_monitoring()