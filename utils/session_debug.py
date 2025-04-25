# asha/utils/session_debug.py
import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_all_sessions, get_recent_sessions
from utils.vector_store import vector_store

def debug_sessions():
    """Debug tool to check session loading and display sample sessions"""
    st.title("ASHA Session Debug Tool")
    
    # Check MongoDB sessions
    st.header("MongoDB Sessions")
    sessions = get_all_sessions()
    
    if not sessions:
        st.error("No sessions found in MongoDB!")
    else:
        st.success(f"Found {len(sessions)} sessions in MongoDB")
        
        # Show a sample
        st.subheader("Sample Sessions")
        sample_size = min(3, len(sessions))
        for i in range(sample_size):
            session = sessions[i]
            st.markdown(f"### {i+1}. {session.get('session_title', 'Untitled Session')}")
            st.write(f"Session ID: {session.get('session_id', 'N/A')}")
            
            # Display host if available
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                st.write(f"Host: {host_users[0].get('username', 'Unknown')}")
            
            # Show other details
            st.write(f"Duration: {session.get('duration', 'N/A')}")
            st.write(f"External URL: {session.get('external_url', 'None')}")
            
            st.markdown("---")
    
    # Check vector store
    st.header("Vector Store Status")
    
    if vector_store.index is None:
        st.error("Vector store index is not initialized!")
    else:
        st.success(f"Vector store index is initialized with {len(vector_store.items)} items")
        
        # Test a search
        st.subheader("Test Vector Search")
        test_query = st.text_input("Enter a test query", value="career development")
        
        if st.button("Search"):
            with st.spinner("Searching..."):
                results = vector_store.search(test_query, top_k=3)
                
                if results:
                    st.success(f"Found {len(results)} results")
                    for i, result in enumerate(results):
                        st.markdown(f"### Result {i+1}")
                        st.write(f"Distance: {result['distance']:.4f}")
                        
                        item = result['item']
                        st.write(f"Title: {item.get('session_title', 'N/A')}")
                        
                        # Show host if available
                        host_users = item.get('host_user', [])
                        if host_users and len(host_users) > 0:
                            st.write(f"Host: {host_users[0].get('username', 'Unknown')}")
                else:
                    st.warning("No search results found")

if __name__ == "__main__":
    debug_sessions()