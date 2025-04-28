import json
import sys
import os
import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, ConnectionFailure
from bson.objectid import ObjectId

def setup_database():
    """
    Initialize the MongoDB database with collections and indexes for the ASHA application.
    """
    # Connect to MongoDB
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Check if connection is alive
        db = client["asha_db"]
        print("Connected to MongoDB successfully")
    except (ConnectionFailure, Exception) as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
    
    # Create collections if they don't exist
    collections = {
        "users": {
            "indexes": [
                ("email", ASCENDING, True),  # Unique index on email
                ("created_at", DESCENDING, False)
            ]
        },
        "sessions": {
            "indexes": [
                ("session_id", ASCENDING, True),  # Unique index on session_id
                ("schedule.start_time", ASCENDING, False),
                ("tags", ASCENDING, False),
                ("categories", ASCENDING, False)
            ]
        },
        "user_recommendations": {
            "indexes": [
                (["user_id", "session_id"], ASCENDING, True),  # Compound unique index
                ("user_id", ASCENDING, False),
                ("recommended_at", DESCENDING, False),
                ("relevance_score", DESCENDING, False)
            ]
        },
        "conversations": {
            "indexes": [
                ("user_id", ASCENDING, False),
                ("created_at", DESCENDING, False)
            ]
        }
    }
    
    # Create collections and indexes
    for collection_name, config in collections.items():
        try:
            # Check if collection exists
            collection_names = db.list_collection_names()
            if collection_name not in collection_names:
                db.create_collection(collection_name)
                print(f"Created collection: {collection_name}")
            
            collection = db[collection_name]
            
            # Create indexes
            for index_config in config["indexes"]:
                if len(index_config) == 3:
                    field, direction, unique = index_config
                    if isinstance(field, list):
                        # Compound index
                        index_fields = [(f, direction) for f in field]
                        collection.create_index(index_fields, unique=unique)
                    else:
                        # Single field index
                        collection.create_index([(field, direction)], unique=unique)
            
            print(f"Set up indexes for: {collection_name}")
        except Exception as e:
            print(f"Error setting up collection {collection_name}: {e}")
    
    print("Database setup complete.")
    return db

def load_herkey_sessions(db, file_path="data/sessions.json"):
    """Load session data from Herkey JSON file"""
    try:
        # Check if database is connected
        if db is None:
            print("Database connection is not available. Cannot load sessions.")
            return False
            
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} not found. Creating sample sessions instead.")
            create_sample_sessions(db)
            return True
            
        with open(file_path, 'r', encoding='utf-8') as f:
            sessions_data = json.load(f)
            
        print(f"Loaded {len(sessions_data)} sessions from file")
        
        # Process each session
        success_count = 0
        for session in sessions_data:
            try:
                # Convert date strings to datetime objects
                if "schedule" in session:
                    if "start_time" in session["schedule"] and isinstance(session["schedule"]["start_time"], dict):
                        if "$date" in session["schedule"]["start_time"]:
                            date_str = session["schedule"]["start_time"]["$date"]
                            session["schedule"]["start_time"] = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    if "end_time" in session["schedule"] and isinstance(session["schedule"]["end_time"], dict):
                        if "$date" in session["schedule"]["end_time"]:
                            date_str = session["schedule"]["end_time"]["$date"]
                            session["schedule"]["end_time"] = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Handle ObjectId
                if "_id" in session and isinstance(session["_id"], dict) and "$oid" in session["_id"]:
                    session["_id"] = session["_id"]["$oid"]
                
                # Fix any other date fields
                if "meta_data" in session:
                    for key in ["created_at", "updated_at"]:
                        if key in session["meta_data"]:
                            if isinstance(session["meta_data"][key], dict) and "$date" in session["meta_data"][key]:
                                date_str = session["meta_data"][key]["$date"]
                                session["meta_data"][key] = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Check if session already exists
                existing = db.sessions.find_one({"session_id": session["session_id"]})
                if existing:
                    print(f"Session {session['session_id']} already exists, skipping.")
                    continue
                    
                # Clean up description to make it plain text
                if "description" in session and isinstance(session["description"], str):
                    try:
                        # Try to parse JSON description
                        desc_data = json.loads(session["description"])
                        
                        # Extract plain text (simplified)
                        if "root" in desc_data and "children" in desc_data["root"]:
                            plain_text = []
                            for child in desc_data["root"]["children"]:
                                if "children" in child:
                                    for subchild in child["children"]:
                                        if "text" in subchild:
                                            plain_text.append(subchild["text"])
                            
                            if plain_text:
                                session["description"] = " ".join(plain_text)
                    except (json.JSONDecodeError, KeyError):
                        # Keep original description if parsing fails
                        pass
                
                # Insert into database
                db.sessions.insert_one(session)
                print(f"Imported session: {session['session_title']}")
                success_count += 1
            except Exception as e:
                print(f"Error importing session {session.get('session_id', 'unknown')}: {e}")
        
        print(f"Session import complete. Successfully imported {success_count} sessions.")
        return success_count > 0
    except Exception as e:
        print(f"Error loading sessions: {e}")
        print("Creating sample sessions as fallback...")
        create_sample_sessions(db)
        return True

def create_sample_sessions(db):
    """Create sample sessions when no JSON file is available"""
    if db is None:
        print("Database connection is not available. Cannot create sample sessions.")
        return False
    
    print("Creating sample sessions...")
    
    sample_sessions = [
        {
            "session_id": "1698287758043969496",
            "session_title": "Online vs in-person group discussion",
            "description": "Pros and cons of online and in-person group discussions",
            "session_resources": {
                "discussion_image_url": "https://herkey-images.s3.ap-south-1.amazonaws.com/discussion/Discussion+Images/Image+9.svg",
                "watch_url": "https://example.com/watch/online-vs-inperson"
            },
            "host_user": [
                {
                    "user_id": 3969496,
                    "username": "Udhaya C",
                    "role": "host"
                }
            ],
            "schedule": {
                "start_time": datetime.datetime.now() + datetime.timedelta(days=7),
                "end_time": datetime.datetime.now() + datetime.timedelta(days=7, hours=1),
                "duration_minutes": 60,
                "timezone": "UTC"
            },
            "categories": ["Professional Development", "Communication Skills"],
            "tags": ["group discussion", "remote work", "professional development"]
        },
        {
            "session_id": "1698287758043969497",
            "session_title": "Salary Negotiation for Women Professionals",
            "description": "Strategies and techniques for effective salary negotiation in male-dominated industries",
            "session_resources": {
                "discussion_image_url": "https://example.com/salary-negotiation.jpg",
                "watch_url": "https://example.com/watch/salary-negotiation"
            },
            "host_user": [
                {
                    "user_id": 3969497,
                    "username": "Priya M",
                    "role": "host"
                }
            ],
            "schedule": {
                "start_time": datetime.datetime.now() + datetime.timedelta(days=14),
                "end_time": datetime.datetime.now() + datetime.timedelta(days=14, hours=1, minutes=30),
                "duration_minutes": 90,
                "timezone": "UTC"
            },
            "categories": ["Career Development", "Leadership"],
            "tags": ["salary negotiation", "women in tech", "career growth"]
        },
        {
            "session_id": "1698287758043969498",
            "session_title": "Breaking the Glass Ceiling: Leadership Strategies",
            "description": "Strategies for women to overcome barriers to leadership positions",
            "session_resources": {
                "discussion_image_url": "https://example.com/leadership.jpg",
                "watch_url": "https://example.com/watch/glass-ceiling"
            },
            "host_user": [
                {
                    "user_id": 3969498,
                    "username": "Anita J",
                    "role": "host"
                }
            ],
            "schedule": {
                "start_time": datetime.datetime.now() + datetime.timedelta(days=21),
                "end_time": datetime.datetime.now() + datetime.timedelta(days=21, hours=1, minutes=30),
                "duration_minutes": 90,
                "timezone": "UTC"
            },
            "categories": ["Leadership", "Professional Development"],
            "tags": ["leadership", "glass ceiling", "women executives"]
        },
        {
            "session_id": "1698287758043969499",
            "session_title": "Resume Building Workshop for Career Transitions",
            "description": "How to craft a resume that highlights transferable skills when changing careers",
            "session_resources": {
                "discussion_image_url": "https://example.com/resume.jpg",
                "watch_url": "https://example.com/watch/resume-workshop"
            },
            "host_user": [
                {
                    "user_id": 3969499,
                    "username": "Meera K",
                    "role": "host"
                }
            ],
            "schedule": {
                "start_time": datetime.datetime.now() + datetime.timedelta(days=28),
                "end_time": datetime.datetime.now() + datetime.timedelta(days=28, hours=1, minutes=30),
                "duration_minutes": 90,
                "timezone": "UTC"
            },
            "categories": ["Career Development", "Job Search"],
            "tags": ["resume building", "career transition", "job application"]
        },
        {
            "session_id": "1698287758043969500",
            "session_title": "Imposter Syndrome: Overcoming Self-Doubt in the Workplace",
            "description": "Understanding imposter syndrome and strategies to overcome feelings of inadequacy and self-doubt",
            "session_resources": {
                "discussion_image_url": "https://example.com/imposter.jpg",
                "watch_url": "https://example.com/watch/imposter-syndrome"
            },
            "host_user": [
                {
                    "user_id": 3969500,
                    "username": "Shreya P",
                    "role": "host"
                }
            ],
            "schedule": {
                "start_time": datetime.datetime.now() + datetime.timedelta(days=35),
                "end_time": datetime.datetime.now() + datetime.timedelta(days=35, hours=1),
                "duration_minutes": 60,
                "timezone": "UTC"
            },
            "categories": ["Professional Development", "Mental Health"],
            "tags": ["imposter syndrome", "self-confidence", "professional growth"]
        }
    ]
    
    # Try to insert sample sessions
    success_count = 0
    for session in sample_sessions:
        try:
            # Check if session already exists
            existing = db.sessions.find_one({"session_id": session["session_id"]})
            if existing:
                print(f"Session {session['session_id']} already exists, skipping.")
                continue
                
            db.sessions.insert_one(session)
            print(f"Created sample session: {session['session_title']}")
            success_count += 1
        except Exception as e:
            print(f"Error creating sample session: {e}")
    
    print(f"Sample sessions created. Successfully added {success_count} sessions.")
    return success_count > 0

def main():
    """Main function to initialize the database"""
    print("Initializing ASHA database...")
    
    # Create directory structure if it doesn't exist
    os.makedirs("data/raw", exist_ok=True)
    
    # Setup database
    db = setup_database()
    
    if db is None:
        print("Error: Database connection failed. Please check that MongoDB is running.")
        print("You can still run the application, but functionality will be limited.")
        return False
    
    # Load sessions
    sessions_loaded = load_herkey_sessions(db)
    
    if sessions_loaded:
        print("Initialization complete.")
        return True
    else:
        print("Initialization completed with warnings.")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("Database initialization completed with errors.")
        sys.exit(1)