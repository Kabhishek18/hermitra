# asha/utils/db.py
from pymongo import MongoClient
import json
import os
from datetime import datetime
import config
import time
from functools import lru_cache

class DatabaseManager:
    def __init__(self):
        # Connect to MongoDB with optimized settings
        self.client = MongoClient(
            config.MONGO_URI,
            maxPoolSize=config.MONGO_MAX_POOL_SIZE,
            minPoolSize=config.MONGO_MIN_POOL_SIZE,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[config.MONGO_DB]
        
        # Initialize collections
        self.sessions_collection = self.db[config.MONGO_SESSIONS_COLLECTION]
        self.user_history_collection = self.db[config.MONGO_USER_HISTORY_COLLECTION]
        
        # Create indexes for better performance
        self._create_indexes()
        
        # Track last refresh time
        self.last_refresh = time.time()
        self.sessions_cache = None
        
        # Import sessions if collection is empty
        if self.sessions_collection.count_documents({}) == 0:
            self._import_sessions()
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Create index on session_id for faster lookups
            self.sessions_collection.create_index("session_id")
            
            # Create index on user_id for faster user history lookups
            self.user_history_collection.create_index("user_id")
            
            # Create compound index on meta_data.created_at for sorted queries
            self.sessions_collection.create_index([
                ("meta_data.created_at", -1)
            ])
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    def _import_sessions(self):
        """Import sessions from JSON file with optimized processing"""
        if os.path.exists(config.SESSIONS_FILE):
            try:
                # Process in chunks to reduce memory usage
                chunk_size = 100
                processed_count = 0
                
                with open(config.SESSIONS_FILE, 'r') as f:
                    # Check if the file starts with an array
                    first_char = f.read(1)
                    f.seek(0)  # Reset file position
                    
                    if first_char == '[':
                        # Process as array
                        sessions_data = json.load(f)
                        
                        if isinstance(sessions_data, list):
                            for i in range(0, len(sessions_data), chunk_size):
                                chunk = sessions_data[i:i+chunk_size]
                                processed_chunk = [self._clean_session(session) for session in chunk]
                                if processed_chunk:
                                    self.sessions_collection.insert_many(processed_chunk)
                                    processed_count += len(processed_chunk)
                                    print(f"Imported {processed_count}/{len(sessions_data)} sessions")
                        else:
                            # Single object
                            processed = self._clean_session(sessions_data)
                            if processed:
                                self.sessions_collection.insert_one(processed)
                                processed_count = 1
                    else:
                        # Process line by line (JSON Lines format)
                        current_chunk = []
                        for line in f:
                            try:
                                session = json.loads(line.strip())
                                processed = self._clean_session(session)
                                if processed:
                                    current_chunk.append(processed)
                                
                                if len(current_chunk) >= chunk_size:
                                    self.sessions_collection.insert_many(current_chunk)
                                    processed_count += len(current_chunk)
                                    current_chunk = []
                                    print(f"Imported {processed_count} sessions so far")
                            except json.JSONDecodeError:
                                continue
                        
                        # Insert any remaining sessions
                        if current_chunk:
                            self.sessions_collection.insert_many(current_chunk)
                            processed_count += len(current_chunk)
                
                print(f"Successfully imported {processed_count} sessions")
            
            except Exception as e:
                print(f"Error importing sessions: {e}")
                import traceback
                traceback.print_exc()
    
    def _clean_session(self, session):
        """Clean a single session object"""
        processed_session = {}
        
        # Skip _id with $oid
        if '_id' in session:
            pass  # Skip this field
        
        # Process all other fields
        for key, value in session.items():
            if key != '_id':  # Skip the _id field entirely
                processed_session[key] = self._clean_mongodb_formats(value)
        
        return processed_session
    
    def _clean_mongodb_formats(self, data):
        """Recursively clean MongoDB specific formats like $date and $oid"""
        if isinstance(data, dict):
            # Handle special MongoDB format cases
            if len(data) == 1 and '$date' in data:
                # Convert $date to string to avoid MongoDB format issues
                return data['$date']
            elif len(data) == 1 and '$oid' in data:
                # Convert $oid to string
                return data['$oid']
            
            # Process regular dictionaries recursively
            cleaned_dict = {}
            for key, value in data.items():
                cleaned_dict[key] = self._clean_mongodb_formats(value)
            return cleaned_dict
            
        elif isinstance(data, list):
            # Process lists recursively
            return [self._clean_mongodb_formats(item) for item in data]
        
        # Return primitive values as is
        return data
    
    def _refresh_cache_if_needed(self):
        """Refresh the sessions cache if it's stale"""
        current_time = time.time()
        if (self.sessions_cache is None or 
            current_time - self.last_refresh > config.CACHE_TTL):
            # Refresh the cache
            self.sessions_cache = list(self.sessions_collection.find(
                {"meta_data.is_deleted": {"$ne": True}},  # Skip deleted sessions
                {'_id': 0}
            ).sort("meta_data.created_at", -1).limit(config.MAX_CACHE_ITEMS))
            self.last_refresh = current_time
    
    @lru_cache(maxsize=1)
    def get_all_sessions(self):
        """Retrieve all sessions with caching"""
        self._refresh_cache_if_needed()
        return self.sessions_cache
    
    def get_session_by_id(self, session_id):
        """Retrieve a specific session by ID with caching"""
        # Check if it's in cache first
        if self.sessions_cache is not None:
            for session in self.sessions_cache:
                if session.get('session_id') == session_id:
                    return session
        
        # If not in cache, query DB
        return self.sessions_collection.find_one(
            {'session_id': session_id},
            {'_id': 0}
        )
    
    def get_recent_sessions(self, limit=10):
        """Get most recent sessions"""
        return list(self.sessions_collection.find(
            {"meta_data.is_deleted": {"$ne": True}},
            {'_id': 0}
        ).sort("meta_data.created_at", -1).limit(limit))
    
    def save_chat_history(self, user_id, conversation):
        """Save user chat history with batching"""
        try:
            # Batch updates to reduce DB operations
            if 'pending_conversations' not in self.__dict__:
                self.pending_conversations = {}
            
            if user_id not in self.pending_conversations:
                self.pending_conversations[user_id] = []
            
            self.pending_conversations[user_id].append(conversation)
            
            # Flush to DB if we have enough items or enough time has passed
            if len(self.pending_conversations[user_id]) >= 5:
                self._flush_conversations(user_id)
                
            return True
        except Exception as e:
            print(f"Error saving chat history: {e}")
            return False
    
    def _flush_conversations(self, user_id):
        """Flush pending conversations to the database"""
        if user_id in self.pending_conversations and self.pending_conversations[user_id]:
            try:
                conversations = self.pending_conversations[user_id]
                self.user_history_collection.update_one(
                    {'user_id': user_id},
                    {'$push': {'conversations': {'$each': conversations}}},
                    upsert=True
                )
                self.pending_conversations[user_id] = []
            except Exception as e:
                print(f"Error flushing conversations: {e}")
    
    def get_user_history(self, user_id, limit=20):
        """Retrieve limited user chat history to reduce memory usage"""
        user_record = self.user_history_collection.find_one({'user_id': user_id})
        if user_record and 'conversations' in user_record:
            # Return only the most recent conversations
            return user_record['conversations'][-limit:]
        return []
    
    def flush_all_pending(self):
        """Flush all pending conversations to DB"""
        if hasattr(self, 'pending_conversations'):
            for user_id in self.pending_conversations:
                self._flush_conversations(user_id)

# Initialize a global instance
db_manager = DatabaseManager()

# Register cleanup handler
import atexit
atexit.register(db_manager.flush_all_pending)

# Convenience functions
def get_all_sessions():
    return db_manager.get_all_sessions()

def get_session_by_id(session_id):
    return db_manager.get_session_by_id(session_id)

def get_recent_sessions(limit=10):
    return db_manager.get_recent_sessions(limit)

def save_chat_history(user_id, conversation):
    return db_manager.save_chat_history(user_id, conversation)

def get_user_history(user_id, limit=20):
    return db_manager.get_user_history(user_id, limit)