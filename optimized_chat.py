"""
ASHA Chat - Optimized chat component for ASHA career guidance chatbot
Handles multiple chat threads with improved performance
"""

import streamlit as st
import time
import threading
import uuid
from datetime import datetime
import queue
from bson.objectid import ObjectId
import gc
import json

# Chat message processing queue for background processing
chat_queue = queue.Queue()

class ChatThread:
    """A chat thread with its own context and history"""
    
    def __init__(self, thread_id, title=None, user_id=None, user_gender="Woman"):
        self.thread_id = thread_id
        self.title = title or f"Chat {thread_id[:8]}"
        self.user_id = user_id
        self.user_gender = user_gender
        self.messages = []
        self.last_activity = datetime.now()
        self.is_archived = False
    
    def add_message(self, role, content):
        """Add a message to the chat thread"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        }
        self.messages.append(message)
        self.last_activity = datetime.now()
        return message
    
    def get_context(self, window_size=5):
        """Get the last N messages for context"""
        return self.messages[-window_size:] if len(self.messages) > window_size else self.messages
    
    def to_dict(self):
        """Convert thread to dictionary for storage"""
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "user_id": self.user_id,
            "user_gender": self.user_gender,
            "messages": self.messages,
            "last_activity": self.last_activity,
            "is_archived": self.is_archived
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a thread from dictionary data"""
        thread = cls(
            thread_id=data["thread_id"],
            title=data["title"],
            user_id=data["user_id"],
            user_gender=data["user_gender"]
        )
        thread.messages = data["messages"]
        thread.last_activity = data["last_activity"]
        thread.is_archived = data["is_archived"]
        return thread


class ChatManager:
    """Manages multiple chat threads with optimized memory usage"""
    
    def __init__(self, db, chatbot, recommender=None):
        self.db = db
        self.chatbot = chatbot
        self.recommender = recommender
        self.active_threads = {}
        self.thread_lock = threading.RLock()
        
        # Start the background processing thread
        self.should_run = True
        self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processor_thread.start()
    
    def create_thread(self, user_id, user_gender="Woman"):
        """Create a new chat thread"""
        thread_id = str(uuid.uuid4())
        
        with self.thread_lock:
            thread = ChatThread(thread_id, user_id=user_id, user_gender=user_gender)
            
            # Add welcome message
            thread.add_message(
                "assistant", 
                "Hi there! I'm ASHA, your career guidance assistant. How can I help you today with your career questions or challenges?"
            )
            
            self.active_threads[thread_id] = thread
            
            # Save to database
            if self.db is not None:
                try:
                    self.db.chat_threads.insert_one({
                        "thread_id": thread_id,
                        "title": thread.title,
                        "user_id": user_id,
                        "user_gender": user_gender,
                        "messages": thread.messages,
                        "created_at": datetime.now(),
                        "last_activity": datetime.now(),
                        "is_archived": False
                    })
                except Exception as e:
                    print(f"Error creating thread: {e}")
            
            return thread_id
    
    def get_thread(self, thread_id, user_id=None):
        """Get a chat thread by ID, loading from DB if necessary"""
        # Check if thread is in memory
        if thread_id in self.active_threads:
            return self.active_threads[thread_id]
        
        # Load from database
        if self.db is not None and user_id:
            try:
                thread_data = self.db.chat_threads.find_one({
                    "thread_id": thread_id,
                    "user_id": user_id
                })
                
                if thread_data:
                    with self.thread_lock:
                        thread = ChatThread.from_dict(thread_data)
                        self.active_threads[thread_id] = thread
                        return thread
            except Exception as e:
                print(f"Error loading thread: {e}")
        
        return None
    
    def get_user_threads(self, user_id, include_archived=False, limit=10):
        """Get all threads for a user with pagination"""
        threads = []
        
        # First, try to get any active threads from memory
        with self.thread_lock:
            for thread_id, thread in self.active_threads.items():
                if thread.user_id == user_id and (include_archived or not thread.is_archived):
                    threads.append(thread)
        
        # Then, get from database if available
        if self.db is not None:
            try:
                # Filter for active or all threads
                query = {"user_id": user_id}
                if not include_archived:
                    query["is_archived"] = False
                
                db_threads = self.db.chat_threads.find(query).sort("last_activity", -1).limit(limit)
                
                # Add threads that aren't already in memory
                thread_ids = {t.thread_id for t in threads}
                for thread_data in db_threads:
                    if thread_data["thread_id"] not in thread_ids:
                        thread = ChatThread.from_dict(thread_data)
                        threads.append(thread)
                        thread_ids.add(thread.thread_id)
                        
                        # Add to active threads if not already there
                        if thread.thread_id not in self.active_threads:
                            self.active_threads[thread.thread_id] = thread
            except Exception as e:
                print(f"Error getting user threads: {e}")
        
        # Sort by last activity
        threads.sort(key=lambda t: t.last_activity, reverse=True)
        
        # Return limited number of threads
        return threads[:limit]
    
    def add_user_message(self, thread_id, content, user_id):
        """Add a user message to a thread and queue response generation"""
        thread = self.get_thread(thread_id, user_id)
        if not thread:
            return None
        
        # Add user message
        message = thread.add_message("user", content)
        
        # Queue for background processing
        chat_queue.put({
            "thread_id": thread_id,
            "user_id": user_id,
            "content": content
        })
        
        # Save to database
        self._save_thread(thread)
        
        return message
    
    def add_assistant_message(self, thread_id, content):
        """Add an assistant message to a thread"""
        with self.thread_lock:
            if thread_id not in self.active_threads:
                return None
            
            thread = self.active_threads[thread_id]
            message = thread.add_message("assistant", content)
            
            # Save to database
            self._save_thread(thread)
            
            return message
    
    def archive_thread(self, thread_id, user_id):
        """Archive a chat thread"""
        thread = self.get_thread(thread_id, user_id)
        if not thread:
            return False
        
        thread.is_archived = True
        self._save_thread(thread)
        
        # Remove from active threads to save memory
        with self.thread_lock:
            if thread_id in self.active_threads:
                del self.active_threads[thread_id]
        
        return True
    
    def rename_thread(self, thread_id, user_id, new_title):
        """Rename a chat thread"""
        thread = self.get_thread(thread_id, user_id)
        if not thread:
            return False
        
        thread.title = new_title
        self._save_thread(thread)
        return True
    
    def _save_thread(self, thread):
        """Save thread to database"""
        if self.db is None:
            return False
        
        try:
            self.db.chat_threads.update_one(
                {"thread_id": thread.thread_id},
                {"$set": {
                    "title": thread.title,
                    "messages": thread.messages,
                    "last_activity": thread.last_activity,
                    "is_archived": thread.is_archived
                }},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving thread: {e}")
            return False
    
    def _process_queue(self):
        """Background process to handle chat responses"""
        while self.should_run:
            try:
                # Get next message from queue with timeout
                item = chat_queue.get(timeout=1)
                thread_id = item["thread_id"]
                user_id = item["user_id"]
                content = item["content"]
                
                # Get thread
                thread = self.get_thread(thread_id, user_id)
                if not thread:
                    chat_queue.task_done()
                    continue
                
                # Generate response
                try:
                    response = self.chatbot.chat(content, thread.user_gender)
                    
                    # Add assistant response to thread
                    self.add_assistant_message(thread_id, response)
                    
                    # Generate recommendations if available
                    if self.recommender is not None and self.db is not None:
                        try:
                            recommendations = self.recommender.recommend_sessions(content, user_id)
                            
                            # Store recommendations separately
                            if recommendations:
                                self.db.thread_recommendations.insert_one({
                                    "thread_id": thread_id,
                                    "user_id": user_id,
                                    "query": content,
                                    "recommendations": [
                                        {
                                            "session_id": rec["session"]["session_id"],
                                            "relevance_score": rec["relevance_score"]
                                        } for rec in recommendations
                                    ],
                                    "created_at": datetime.now()
                                })
                        except Exception as e:
                            print(f"Error generating recommendations: {e}")
                    
                except Exception as e:
                    print(f"Error generating response: {e}")
                    # Add fallback message
                    self.add_assistant_message(
                        thread_id,
                        "I apologize, but I encountered an error processing your request. Please try again or ask a different question."
                    )
                
                # Mark task as done
                chat_queue.task_done()
                
                # Force garbage collection to prevent memory buildup
                if chat_queue.qsize() == 0:
                    gc.collect()
                
            except queue.Empty:
                # Queue is empty, just continue
                pass
            except Exception as e:
                print(f"Error in chat processor: {e}")
    
    def stop(self):
        """Stop the background thread"""
        self.should_run = False
        if self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5)
    
    def clean_inactive_threads(self, max_age_hours=24):
        """Clean up inactive threads from memory"""
        threshold = datetime.now() - datetime.timedelta(hours=max_age_hours)
        
        with self.thread_lock:
            thread_ids = list(self.active_threads.keys())
            for thread_id in thread_ids:
                thread = self.active_threads[thread_id]
                if thread.last_activity < threshold:
                    del self.active_threads[thread_id]


def get_thread_recommendations(db, thread_id, limit=5):
    """Get recommendations for a specific thread"""
    if db is None:
        return []
    
    try:
        # Get the most recent recommendations for this thread
        rec_data = db.thread_recommendations.find_one(
            {"thread_id": thread_id},
            sort=[("created_at", -1)]
        )
        
        if not rec_data:
            return []
        
        # Get the session data for each recommendation
        recommendations = []
        for rec in rec_data["recommendations"][:limit]:
            session = db.sessions.find_one({"session_id": rec["session_id"]})
            if session:
                recommendations.append({
                    "session": session,
                    "relevance_score": rec["relevance_score"]
                })
        
        return recommendations
    except Exception as e:
        print(f"Error getting thread recommendations: {e}")
        return []


# UI Component for Chat Interface
def chat_interface(user_id, chat_manager, db=None):
    """
    Multi-threaded chat interface with optimized performance
    
    Args:
        user_id: The current user's ID
        chat_manager: ChatManager instance
        db: MongoDB database connection (optional)
    """
    st.title("Chat with ASHA")
    
    # Initialize session state for current thread
    if "current_thread_id" not in st.session_state:
        # Create a new thread if needed
        user_gender = st.session_state.get("user", {}).get("gender", "Woman")
        thread_id = chat_manager.create_thread(user_id, user_gender)
        st.session_state.current_thread_id = thread_id
    
    # Sidebar for thread management
    with st.sidebar:
        st.subheader("Your Conversations")
        
        # New chat button
        if st.button("New Chat"):
            user_gender = st.session_state.get("user", {}).get("gender", "Woman")
            thread_id = chat_manager.create_thread(user_id, user_gender)
            st.session_state.current_thread_id = thread_id
            st.rerun()
        
        # List existing threads
        threads = chat_manager.get_user_threads(user_id)
        
        if not threads:
            st.info("No previous conversations found.")
        else:
            st.write("Select a conversation:")
            
            for thread in threads:
                # Create a unique key for each button
                button_key = f"thread_{thread.thread_id}"
                
                # Highlight current thread
                if thread.thread_id == st.session_state.current_thread_id:
                    button_label = f"📌 {thread.title}"
                else:
                    button_label = thread.title
                
                if st.button(button_label, key=button_key):
                    st.session_state.current_thread_id = thread.thread_id
                    st.rerun()
    
    # Main chat area
    current_thread = chat_manager.get_thread(st.session_state.current_thread_id, user_id)
    
    if not current_thread:
        st.error("Could not load the conversation. Please start a new chat.")
        return
    
    # Thread options (rename, archive)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("Rename"):
            st.session_state.show_rename = True
    
    with col2:
        st.markdown(f"### {current_thread.title}")
    
    with col3:
        if st.button("Archive"):
            if chat_manager.archive_thread(current_thread.thread_id, user_id):
                # Create a new thread
                user_gender = st.session_state.get("user", {}).get("gender", "Woman")
                thread_id = chat_manager.create_thread(user_id, user_gender)
                st.session_state.current_thread_id = thread_id
                st.success("Conversation archived successfully.")
                st.rerun()
    
    # Rename dialog
    if st.session_state.get("show_rename", False):
        with st.form("rename_form"):
            new_title = st.text_input("New conversation title:", value=current_thread.title)
            col1, col2 = st.columns(2)
            
            with col1:
                if st.form_submit_button("Save"):
                    if chat_manager.rename_thread(current_thread.thread_id, user_id, new_title):
                        st.session_state.show_rename = False
                        st.success("Conversation renamed successfully.")
                        st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_rename = False
                    st.rerun()
    
    # Display messages with improved performance
    message_container = st.container()
    
    with message_container:
        for message in current_thread.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    # Input for new message
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to UI immediately
        with st.chat_message("user"):
            st.write(prompt)
        
        # Add to chat manager (which will queue for processing)
        chat_manager.add_user_message(
            st.session_state.current_thread_id,
            prompt,
            user_id
        )
        
        # Show "typing" indicator
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Wait for response to be generated (max 30 seconds)
                for _ in range(30):
                    # Check if we have a new message
                    updated_thread = chat_manager.get_thread(st.session_state.current_thread_id, user_id)
                    if updated_thread and len(updated_thread.messages) > len(current_thread.messages) + 1:
                        # New message is available
                        break
                    time.sleep(1)
                
                # Reload the page to show the response
                st.rerun()
    
    # Display recommendations in sidebar
    if db is not None:
        with st.sidebar:
            st.divider()
            st.subheader("Relevant Sessions")
            
            # Get recommendations for this thread
            recommendations = get_thread_recommendations(db, current_thread.thread_id)
            
            if not recommendations:
                st.info("No relevant sessions found yet. Continue the conversation to get recommendations.")
            else:
                for rec in recommendations:
                    session = rec["session"]
                    relevance = rec["relevance_score"]
                    
                    with st.expander(f"{session.get('session_title', 'Session')} ({relevance:.2%} match)"):
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
                        
                        # Show session details
                        st.write(f"**Description**: {description}")
                        
                        # Show schedule if available
                        if "schedule" in session and "start_time" in session["schedule"]:
                            start_time = session["schedule"]["start_time"]
                            if isinstance(start_time, datetime):
                                st.write(f"**Date**: {start_time.strftime('%Y-%m-%d %H:%M')}")
                        
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