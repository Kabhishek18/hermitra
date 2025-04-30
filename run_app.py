
import streamlit as st
import sys
import os

# Add patch code
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the fixed login form
    from fixed_login import enhanced_login_form
    
    # Create a simple patch for asha_app
    import asha_app
    
    # Apply the patch - replace the original function with our fixed version
    asha_app.enhanced_login_form = enhanced_login_form
    
    # Add better styles
    original_apply_ui = asha_app.apply_enhanced_ui
    def enhanced_apply_ui():
        original_apply_ui()
        st.markdown('''
        <style>
        /* Clean up error display */
        div[data-baseweb="notification"] {
            margin: 0.5rem 0 !important;
        }
        
        /* Fix Streamlit form issues */
        section[data-testid="stForm"] {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        </style>
        ''', unsafe_allow_html=True)
    
    # Apply the patched function
    asha_app.apply_enhanced_ui = enhanced_apply_ui
    
    print("ASHA patches applied successfully")
except Exception as e:
    print(f"Error applying patches: {e}")

# Run the main app
import asha_app
