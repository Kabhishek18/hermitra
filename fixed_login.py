
import streamlit as st
import base64
from core import verify_password, generate_session_token, ObjectId

def enhanced_login_form(db):
    """Display enhanced login form with better UI"""
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Login to ASHA")
        
        with st.form(key="login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            # Simple submit button
            submit = st.form_submit_button("Sign In")
        
        # Handle form submission
        if submit:
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
    
    with col2:
        st.image("https://img.icons8.com/color/240/null/login-rounded-right--v1.png", width=100)
    
    st.markdown('</div>', unsafe_allow_html=True)
