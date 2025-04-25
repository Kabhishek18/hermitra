from pymongo import MongoClient, ASCENDING
import os
from dotenv import load_dotenv

load_dotenv()

def initialize_database():
    try:
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client[os.getenv('MONGODB_DB_NAME')]
        
        # Create collections
        db.create_collection('sessions')
        db.create_collection('embeddings')
        db.create_collection('interaction_logs')
        db.create_collection('error_logs')
        
        print('Collections created')
        
        # Create indexes
        db.sessions.create_index([('userId', ASCENDING)], unique=True)
        db.embeddings.create_index([('userId', ASCENDING)])
        db.interaction_logs.create_index([('timestamp', ASCENDING)])
        db.error_logs.create_index([('timestamp', ASCENDING)])
        
        # Create vector index (this requires MongoDB Atlas)
        try:
            db.command({
                'createIndexes': 'embeddings',
                'indexes': [
                    {
                        'key': {'embedding': 'vector'},
                        'name': 'vector_index',
                        'vectorOptions': {
                            'dimensions': 1536,  # Titan embedding dimensions
                            'similarity': 'cosine'
                        }
                    }
                ]
            })
            print('Vector index created')
        except Exception as e:
            print(f'Could not create vector index: {str(e)}')
            print('If you are using a local MongoDB instance, you may need to use MongoDB Atlas with Atlas Vector Search for this feature')
        
        print('Database initialization completed successfully')
    except Exception as e:
        print(f'Database initialization failed: {str(e)}')
    finally:
        if 'client' in locals():
            client.close()

if __name__ == '__main__':
    initialize_database()