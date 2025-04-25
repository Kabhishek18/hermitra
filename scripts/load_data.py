from pymongo import MongoClient
import json
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.services.aws_client import AWSBedrockClient

load_dotenv()

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        raise

def load_data():
    try:
        # Connect to MongoDB
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DB_NAME')]
        print('Connected to MongoDB')
        
        # Load session data
        sessions_file_path = Path('data/raw/herkey.sessions.json')
        sessions_data = load_json_file(sessions_file_path)
        
        # Format and insert sessions
        formatted_sessions = []
        for session in sessions_data:
            formatted_sessions.append({
                'userId': session.get('userId', f"user_{os.urandom(4).hex()}"),
                'conversations': session.get('conversations', []),
                'preferences': session.get('preferences', {}),
                'createdAt': datetime.fromisoformat(session.get('createdAt')) if session.get('createdAt') else datetime.now(),
                'lastActive': datetime.fromisoformat(session.get('lastActive')) if session.get('lastActive') else datetime.now()
            })
        
        if formatted_sessions:
            db.sessions.insert_many(formatted_sessions)
            print(f"Inserted {len(formatted_sessions)} sessions")
        
        # Load embedding data
        embeddings_file_path = Path('data/raw/herkey.sessions.embedding.json')
        embeddings_data = load_json_file(embeddings_file_path)
        
        # Format and insert embeddings
        formatted_embeddings = []
        for item in embeddings_data:
            formatted_embeddings.append({
                'userId': item.get('userId', f"user_{os.urandom(4).hex()}"),
                'content': item.get('content', ''),
                'embedding': item.get('embedding', []),
                'metadata': {
                    'timestamp': datetime.fromisoformat(item.get('metadata', {}).get('timestamp')) if item.get('metadata', {}).get('timestamp') else datetime.now(),
                    'type': item.get('metadata', {}).get('type', 'conversation'),
                    **item.get('metadata', {})
                }
            })
        
        if formatted_embeddings:
            db.embeddings.insert_many(formatted_embeddings)
            print(f"Inserted {len(formatted_embeddings)} embeddings")
        
        print('Data loading completed successfully')
    except Exception as e:
        print(f'Data loading failed: {str(e)}')
    finally:
        if 'client' in locals():
            client.close()

if __name__ == '__main__':
    load_data()