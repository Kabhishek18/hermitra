# asha/fix_sessions.py
"""
This script manually imports sessions into MongoDB and rebuilds the vector index.
Run this if you're having issues with session recommendations.
"""
import os
import sys
import json
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
import config
from utils.vector_store import VectorStore
from sentence_transformers import SentenceTransformer

def main():
    print("ASHA Session Fix Tool")
    print("=====================")
    
    # 1. Check MongoDB connection
    print("\nChecking MongoDB connection...")
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✅ MongoDB is running")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("Please start MongoDB before continuing.")
        return
    
    # 2. Connect to database
    db = client[config.MONGO_DB]
    sessions_collection = db[config.MONGO_SESSIONS_COLLECTION]
    
    # 3. Check if sessions file exists
    sessions_file = config.SESSIONS_FILE
    if not os.path.exists(sessions_file):
        print(f"❌ Sessions file not found: {sessions_file}")
        
        # Check data directory structure
        data_dir = config.DATA_DIR
        if not os.path.exists(data_dir):
            print(f"Creating data directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
        
        print("Please place your sessions.json file in the data directory.")
        return
    
    # 4. Clear existing sessions
    print("\nClearing existing sessions...")
    result = sessions_collection.delete_many({})
    print(f"Deleted {result.deleted_count} existing sessions")
    
    # 5. Import sessions
    print("\nImporting sessions from file...")
    try:
        with open(sessions_file, 'r') as f:
            # Check if the file starts with an array
            first_char = f.read(1)
            f.seek(0)  # Reset file position
            
            sessions_data = []
            if first_char == '[':
                # Process as array
                sessions_data = json.load(f)
            else:
                # Process line by line (JSON Lines format)
                for line in f:
                    try:
                        session = json.loads(line.strip())
                        sessions_data.append(session)
                    except json.JSONDecodeError:
                        continue
        
        if not isinstance(sessions_data, list):
            sessions_data = [sessions_data]
        
        print(f"Found {len(sessions_data)} sessions in file")
        
        # Process sessions
        processed_sessions = []
        for session in sessions_data:
            processed_session = {}
            
            # Skip _id with $oid
            if '_id' in session:
                # If we want to keep the ID, we could convert it
                # processed_session['original_id'] = session['_id'].get('$oid', '')
                # But for simplicity, let's skip the _id field
                pass
            
            # Process all other fields
            for key, value in session.items():
                if key != '_id':  # Skip the _id field entirely
                    processed_session[key] = clean_mongodb_formats(value)
            
            processed_sessions.append(processed_session)
        
        # Insert into MongoDB
        if processed_sessions:
            sessions_collection.insert_many(processed_sessions)
            print(f"✅ Successfully imported {len(processed_sessions)} sessions")
        else:
            print("❌ No valid sessions found to import")
    
    except Exception as e:
        print(f"❌ Error importing sessions: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 6. Build vector index
    print("\nBuilding vector index...")
    try:
        # Get all sessions
        all_sessions = list(sessions_collection.find({}, {'_id': 0}))
        print(f"Retrieved {len(all_sessions)} sessions from database")
        
        # Create vector store
        vector_store = VectorStore()
        
        # Prepare session texts
        texts = []
        for session in all_sessions:
            # Extract text fields
            title = session.get('session_title', '')
            description = session.get('description', '')
            
            # Extract host info
            host_info = ""
            host_users = session.get('host_user', [])
            if host_users and len(host_users) > 0:
                host_info = host_users[0].get('username', '')
            
            # Combine text
            session_text = f"Title: {title} Description: {description} Host: {host_info}"
            texts.append(session_text)
        
        # Build index
        print(f"Building index with {len(texts)} texts...")
        vector_store.create_index(texts, all_sessions)
        print(f"✅ Successfully built vector index")
        
        # Save index
        vector_store.save(config.VECTOR_INDEX_PATH)
        print(f"✅ Saved vector index to {config.VECTOR_INDEX_PATH}")
        
        # Test search
        print("\nTesting search...")
        results = vector_store.search("leadership development", top_k=2)
        if results:
            print(f"✅ Search test successful! Found {len(results)} results")
            for i, result in enumerate(results):
                print(f"  Result {i+1}: {result['item'].get('session_title', 'N/A')}")
        else:
            print("❌ Search test failed - no results found")
    
    except Exception as e:
        print(f"❌ Error building vector index: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n✅ Session fix completed successfully!")
    print("You can now restart the ASHA application and session recommendations should work.")

def clean_mongodb_formats(data):
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
            cleaned_dict[key] = clean_mongodb_formats(value)
        return cleaned_dict
        
    elif isinstance(data, list):
        # Process lists recursively
        return [clean_mongodb_formats(item) for item in data]
    
    # Return primitive values as is
    return data

if __name__ == "__main__":
    main()