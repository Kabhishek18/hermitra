# asha/utils/db.py
from pymongo import MongoClient
import json
import os
from datetime import datetime
import config

class DatabaseManager:
    def __init__(self):
        # Connect to MongoDB
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.MONGO_DB]
        
        # Initialize collections
        self.sessions_collection = self.db[config.MONGO_SESSIONS_COLLECTION]
        self.user_history_collection = self.db[config.MONGO_USER_HISTORY_COLLECTION]
        
        # Import sessions if collection is empty
        if self.sessions_collection.count_documents({}) == 0:
            self._import_sessions()
    
    def _import_sessions(self):
        """Import sessions from JSON file if available"""
        if os.path.exists(config.SESSIONS_FILE):
            try:
                with open(config.SESSIONS_FILE, 'r') as f:
                    sessions_data = json.load(f)
                
                # Process the data to remove MongoDB specific formats
                processed_data = []
                
                # Handle both list and single object
                if not isinstance(sessions_data, list):
                    sessions_data = [sessions_data]
                
                for session in sessions_data:
                    processed_session = {}
                    
                    # Remove _id with $oid and create a clean version
                    if '_id' in session:
                        # If we want to keep the ID, we could convert it
                        # processed_session['original_id'] = session['_id'].get('$oid', '')
                        # But for simplicity, let's skip the _id field
                        pass
                    
                    # Process all other fields
                    for key, value in session.items():
                        if key != '_id':  # Skip the _id field entirely
                            processed_session[key] = self._clean_mongodb_formats(value)
                    
                    processed_data.append(processed_session)
                
                # Insert into MongoDB
                if processed_data:
                    self.sessions_collection.insert_many(processed_data)
                    print(f"Successfully imported {len(processed_data)} sessions")
            
            except Exception as e:
                print(f"Error importing sessions: {e}")
                import traceback
                traceback.print_exc()
    
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
    
    def get_all_sessions(self):
        """Retrieve all sessions"""
        return list(self.sessions_collection.find({}, {'_id': 0}))
    
    def get_session_by_id(self, session_id):
        """Retrieve a specific session by ID"""
        return self.sessions_collection.find_one({'session_id': session_id}, {'_id': 0})
    
    def save_chat_history(self, user_id, conversation):
        """Save user chat history"""
        self.user_history_collection.update_one(
            {'user_id': user_id},
            {'$push': {'conversations': conversation}},
            upsert=True
        )
    
    def get_user_history(self, user_id):
        """Retrieve user chat history"""
        user_record = self.user_history_collection.find_one({'user_id': user_id})
        return user_record.get('conversations', []) if user_record else []

# Initialize a global instance
db_manager = DatabaseManager()

# Convenience functions
def get_all_sessions():
    return db_manager.get_all_sessions()

def get_session_by_id(session_id):
    return db_manager.get_session_by_id(session_id)

def save_chat_history(user_id, conversation):
    return db_manager.save_chat_history(user_id, conversation)

def get_user_history(user_id):
    return db_manager.get_user_history(user_id)