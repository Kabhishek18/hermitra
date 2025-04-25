from pymongo import MongoClient
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

load_dotenv()

class SessionManager:
    def __init__(self):
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client[os.getenv('MONGODB_DB_NAME')]
        self.sessions_collection = self.db.sessions
    
    def get_user_session(self, user_id):
        try:
            user_session = self.sessions_collection.find_one({"userId": user_id})
            
            if not user_session:
                # Initialize new session
                user_session = {
                    "userId": user_id,
                    "conversations": [],
                    "preferences": {},
                    "createdAt": datetime.now(),
                    "lastActive": datetime.now()
                }
                
                self.sessions_collection.insert_one(user_session)
                logger.info(f"New session created for user {user_id}")
            
            return user_session
        except Exception as e:
            logger.error(f"Error getting session for user {user_id}: {str(e)}")
            raise
    
    def update_user_session(self, user_id, query, response):
        try:
            conversation = {
                "timestamp": datetime.now(),
                "query": query,
                "response": response
            }
            
            self.sessions_collection.update_one(
                {"userId": user_id},
                {
                    "$push": {"conversations": conversation},
                    "$set": {"lastActive": datetime.now()}
                }
            )
            
            logger.info(f"Session updated for user {user_id}")
            return conversation
        except Exception as e:
            logger.error(f"Error updating session for user {user_id}: {str(e)}")
            raise
    
    def update_user_preferences(self, user_id, preferences):
        try:
            self.sessions_collection.update_one(
                {"userId": user_id},
                {
                    "$set": {
                        "preferences": preferences,
                        "lastActive": datetime.now()
                    }
                },
                upsert=True
            )
            
            logger.info(f"Preferences updated for user {user_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
            raise