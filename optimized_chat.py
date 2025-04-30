"""
Enhanced chat interface module for the ASHA chatbot
Provides improved UI and performance for the chat functionality
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
    
    def rename_thread(self, thread_id, user_id, new_title):
        """Rename a chat thread"""
        thread = self.get_thread(thread_id, user_id)
        if not thread:
            return False
        
        thread.title = new_title
        self._save_thread(thread)
        return True
    
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


# Enhanced Chat Interface with better UI
# In optimized_chat.py
# Find and replace the chat interface function with a fixed version

def enhanced_chat_interface(user_id, chat_manager, db=None):
    """
    Enhanced chat interface with improved UI and performance
    
    Args:
        user_id: The current user's ID
        chat_manager: ChatManager instance
        db: MongoDB database connection (optional)
    """
    st.markdown('<h2 class="subheader">Chat with ASHA</h2>', unsafe_allow_html=True)
    
    # Initialize session state for current thread
    if "current_thread_id" not in st.session_state:
        # Create a new thread if needed
        user_gender = st.session_state.get("user", {}).get("gender", "Woman")
        thread_id = chat_manager.create_thread(user_id, user_gender)
        st.session_state.current_thread_id = thread_id
    
    # Enhanced layout with better visual hierarchy - fixed columns
    main_cols = st.columns([1, 3])
    
    # Thread management sidebar
    with main_cols[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin-bottom: 15px;">Your Conversations</h4>', unsafe_allow_html=True)
        
        # New chat button with icon
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button("+ New Chat"):
            user_gender = st.session_state.get("user", {}).get("gender", "Woman")
            thread_id = chat_manager.create_thread(user_id, user_gender)
            st.session_state.current_thread_id = thread_id
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Separator
        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
        
        # List existing threads with improved styling
        threads = chat_manager.get_user_threads(user_id)
        
        if not threads:
            st.info("No previous conversations found.")
        else:
            for thread in threads:
                # Create a unique key for each button
                button_key = f"thread_{thread.thread_id}"
                
                # Highlight current thread
                if thread.thread_id == st.session_state.current_thread_id:
                    st.markdown(f"""
                    <div style="padding: 8px 12px; background-color: #e9f5fe; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #FF1493;">
                        <p style="margin: 0; font-weight: 500; color: #212529;">📌 {thread.title}</p>
                        <p style="margin: 0; font-size: 0.75rem; color: #6c757d;">
                            {thread.last_activity.strftime('%b %d, %I:%M %p')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(thread.title, key=button_key):
                        st.session_state.current_thread_id = thread.thread_id
                        st.rerun()
        
        # Show archived conversations button
        st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
        if st.button("Show Archived Chats", key="show_archived"):
            st.session_state.show_archived = not st.session_state.get("show_archived", False)
            st.rerun()
        
        # Display archived conversations if requested
        if st.session_state.get("show_archived", False):
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
            st.markdown("<h5>Archived Conversations</h5>", unsafe_allow_html=True)
            
            archived_threads = chat_manager.get_user_threads(user_id, include_archived=True)
            archived_threads = [t for t in archived_threads if t.is_archived]
            
            if not archived_threads:
                st.info("No archived conversations.")
            else:
                for thread in archived_threads:
                    button_key = f"archived_{thread.thread_id}"
                    if st.button(f"🗄️ {thread.title}", key=button_key):
                        st.session_state.current_thread_id = thread.thread_id
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main chat area
    with main_cols[1]:
        current_thread = chat_manager.get_thread(st.session_state.current_thread_id, user_id)
        
        if not current_thread:
            st.error("Could not load the conversation. Please start a new chat.")
            return
        
        # Thread options (rename, archive) with better styling - avoid nested columns
        st.markdown('<div class="card" style="padding: 12px;">', unsafe_allow_html=True)
        
        # Use HTML/CSS layout instead of nested columns
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0;">{current_thread.title}</h3>
            <div style="display: flex; gap: 10px;">
                <div id="rename-btn-container"></div>
                <div id="archive-btn-container"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Place buttons into the containers
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Rename", key="rename_btn"):
                st.session_state.show_rename = True
                
        with button_col2:
            if st.button("Archive", key="archive_btn"):
                if chat_manager.archive_thread(current_thread.thread_id, user_id):
                    # Create a new thread
                    user_gender = st.session_state.get("user", {}).get("gender", "Woman")
                    thread_id = chat_manager.create_thread(user_id, user_gender)
                    st.session_state.current_thread_id = thread_id
                    st.success("Conversation archived successfully.")
                    st.rerun()
        
        # Inject button placement with JavaScript
        st.markdown("""
        <script>
            // Move buttons to containers
            const renameBtn = document.querySelector('button[kind="secondary"][data-testid="baseButton-secondary"]:not([data-testid*="archive"])');
            const archiveBtn = document.querySelector('button[kind="secondary"][data-testid="baseButton-secondary"][data-testid*="archive"]');
            
            if (renameBtn) {
                document.getElementById('rename-btn-container').appendChild(renameBtn.parentElement.parentElement);
            }
            if (archiveBtn) {
                document.getElementById('archive-btn-container').appendChild(archiveBtn.parentElement.parentElement);
            }
        </script>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Rename dialog with improved UI - FIXED VERSION
        if st.session_state.get("show_rename", False):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("<h4>Rename Conversation</h4>", unsafe_allow_html=True)
            
            # Use a form without nested columns
            with st.form("rename_form"):
                new_title = st.text_input("New conversation title:", value=current_thread.title)
                # Single submit button
                submit_button = st.form_submit_button("Save Changes")
            
            # Handle form submission - Note this is outside the form block
            if submit_button:
                if chat_manager.rename_thread(current_thread.thread_id, user_id, new_title):
                    st.session_state.show_rename = False
                    st.success("Conversation renamed successfully.")
                    st.rerun()
                
            # Add a cancel button outside the form
            if st.button("Cancel", key="rename_cancel"):
                st.session_state.show_rename = False
                st.rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Display messages with enhanced styling
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        for message in current_thread.messages:
            role = message["role"]
            content = message["content"]
            
            if "timestamp" in message:
                timestamp = message["timestamp"].strftime("%I:%M %p")
            else:
                timestamp = ""
            
            if role == "user":
                st.markdown(f"""
                <div class="user-message">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="font-weight: 500; color: #1976D2;">You</span>
                        <span style="font-size: 0.7rem; color: #6c757d;">{timestamp}</span>
                    </div>
                    {content}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="assistant-message">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="font-weight: 500; color: #FF1493;">ASHA</span>
                        <span style="font-size: 0.7rem; color: #6c757d;">{timestamp}</span>
                    </div>
                    {content}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Input for new message with better styling
        st.markdown('<div style="margin-top: 16px;">', unsafe_allow_html=True)
        
        placeholder = "Type your career question here..."
        if prompt := st.chat_input(placeholder):
            # Add user message to UI immediately
            st.markdown(f"""
            <div class="user-message">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 500; color: #1976D2;">You</span>
                    <span style="font-size: 0.7rem; color: #6c757d;">{datetime.now().strftime("%I:%M %p")}</span>
                </div>
                {prompt}
            </div>
            """, unsafe_allow_html=True)
            
            # Add to chat manager (which will queue for processing)
            chat_manager.add_user_message(
                st.session_state.current_thread_id,
                prompt,
                user_id
            )
            
            # Show "typing" indicator
            with st.spinner():
                st.markdown(f"""
                <div class="assistant-message loading">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="font-weight: 500; color: #FF1493;">ASHA</span>
                        <span style="font-size: 0.7rem; color: #6c757d;">{datetime.now().strftime("%I:%M %p")}</span>
                    </div>
                    <div style="display: flex;">
                        <div style="height: 8px; width: 8px; background-color: #FF1493; border-radius: 50%; margin-right: 4px; opacity: 0.7;"></div>
                        <div style="height: 8px; width: 8px; background-color: #FF1493; border-radius: 50%; margin-right: 4px; opacity: 0.5;"></div>
                        <div style="height: 8px; width: 8px; background-color: #FF1493; border-radius: 50%; opacity: 0.3;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
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
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick questions with simplified layout
        st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 0.9rem; color: #6c757d; margin-bottom: 8px;">Quick questions:</p>', unsafe_allow_html=True)
        
        # Use HTML layout instead of columns for suggestions
        st.markdown('<div style="display: flex; gap: 10px; flex-wrap: wrap;">', unsafe_allow_html=True)
        
        suggestions = [
            "Help with my resume",
            "Tips for salary negotiation",
            "How to overcome imposter syndrome"
        ]
        
        for i, suggestion in enumerate(suggestions):
            # Add container divs for buttons
            st.markdown(f'<div id="suggestion-{i}-container"></div>', unsafe_allow_html=True)
            
            # Create buttons
            if st.button(suggestion, key=f"suggestion_{i}"):
                chat_manager.add_user_message(
                    st.session_state.current_thread_id,
                    suggestion,
                    user_id
                )
                st.rerun()
        
        # Place buttons with JavaScript
        st.markdown("""
        <script>
            // Move suggestion buttons to containers
            const suggestionBtns = document.querySelectorAll('button[kind="secondary"][data-testid="baseButton-secondary"]');
            for (let i = 0; i < suggestionBtns.length; i++) {
                const container = document.getElementById(`suggestion-${i}-container`);
                if (container && suggestionBtns[i]) {
                    container.appendChild(suggestionBtns[i].parentElement.parentElement);
                }
            }
        </script>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Simplified recommendations sidebar to avoid nested columns
    if db is not None:
        st.sidebar.markdown('<div class="card">', unsafe_allow_html=True)
        st.sidebar.markdown('<h4 style="margin-bottom: 15px;">Related Sessions</h4>', unsafe_allow_html=True)
        
        # Get recommendations for this thread
        recommendations = get_thread_recommendations(db, current_thread.thread_id)
        
        if not recommendations:
            st.sidebar.info("Continue your conversation to get personalized session recommendations.")
        else:
            for i, rec in enumerate(recommendations):
                session = rec["session"]
                relevance = rec["relevance_score"]
                
                # Display simplified recommendation cards
                st.sidebar.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #FF1493;">
                    <h5 style="margin: 0 0 8px 0;">{session.get('session_title', 'Session')}</h5>
                    <div style="height: 4px; background-color: #e9ecef; border-radius: 2px; margin-bottom: 8px;">
                        <div style="height: 100%; width: {relevance * 100}%; background-color: #FF1493; border-radius: 2px;"></div>
                    </div>
                    <p style="font-size: 0.8rem; margin: 0 0 8px 0;">{relevance:.0%} match • {session.get('duration', '1hr')}</p>
                    <a href="#" style="display: inline-block; font-size: 0.8rem; color: #FF1493;">View details →</a>
                </div>
                """, unsafe_allow_html=True)
        
        st.sidebar.markdown('</div>', unsafe_allow_html=True)