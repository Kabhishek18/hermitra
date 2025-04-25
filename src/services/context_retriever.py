import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

class ContextRetriever:
    def __init__(self, db, aws_client):
        self.db = db
        self.aws_client = aws_client
        self.embeddings_collection = db.embeddings
        self.top_k = 5  # Number of similar contexts to retrieve
    
    def retrieve_context(self, query, user_id=None):
        try:
            # Generate embedding for the query
            query_embedding = self.aws_client.create_embedding(query)
            
            # MongoDB Atlas vector search query
            pipeline = [
                {
                    "$search": {
                        "knnBeta": {
                            "vector": query_embedding,
                            "path": "embedding",
                            "k": self.top_k
                        }
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "content": 1,
                        "metadata": 1,
                        "score": {"$meta": "searchScore"}
                    }
                }
            ]
            
            try:
                relevant_documents = list(self.embeddings_collection.aggregate(pipeline))
            except Exception as e:
                logger.warning(f"Vector search failed: {str(e)}. Falling back to basic search.")
                # Fallback to basic search if vector search isn't supported
                relevant_documents = list(self.embeddings_collection.find(
                    {"userId": user_id} if user_id else {},
                    {"_id": 0, "content": 1, "metadata": 1}
                ).limit(self.top_k))
            
            # Format context for use in prompt
            return [
                {
                    'content': doc.get('content', ''),
                    'relevance': doc.get('score', 0),
                    'timestamp': doc.get('metadata', {}).get('timestamp')
                }
                for doc in relevant_documents
            ]
        except Exception as e:
            logger.error(f"Context retrieval error: {str(e)}")
            return []  # Return empty context in case of error
    
    def store_embedding(self, user_id, content, embedding, metadata=None):
        try:
            metadata = metadata or {}
            self.embeddings_collection.insert_one({
                'userId': user_id,
                'content': content,
                'embedding': embedding,
                'metadata': {
                    'timestamp': datetime.now(),
                    'type': 'conversation',
                    **metadata
                }
            })
            
            logger.info(f"Embedding stored for user {user_id}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error storing embedding for user {user_id}: {str(e)}")
            raise
    
    def assemble_context(self, user_session, retrieved_context, query):
        # Get recent conversation history (last 5 exchanges)
        recent_conversations = user_session.get('conversations', [])[-5:]
        recent_history = []
        
        for conv in recent_conversations:
            recent_history.append({
                'role': 'user',
                'content': conv.get('query', '')
            })
            
            recent_history.append({
                'role': 'assistant',
                'content': conv.get('response', '')
            })
        
        # Format user preferences if available
        user_preferences = user_session.get('preferences', {})
        formatted_preferences = 'No user preferences available.'
        
        if user_preferences:
            career_interests = user_preferences.get('career_interests', [])
            career_interests_str = ', '.join(career_interests) if career_interests else 'Not specified'
            
            formatted_preferences = f"""User Preferences:
- Career Interests: {career_interests_str}
- Experience Level: {user_preferences.get('experience_level', 'Not specified')}
- Industry: {user_preferences.get('industry', 'Not specified')}"""
        
        # Format retrieved context
        formatted_context = '\n\n'.join([
            f"Related Information:\n{ctx.get('content', '')}"
            for ctx in retrieved_context
        ])
        
        return {
            'history': recent_history,
            'current_query': query,
            'user_preferences': formatted_preferences,
            'retrieved_context': formatted_context
        }