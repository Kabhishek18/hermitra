# asha/engines/session_recommender.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vector_store import VectorStore
from utils.db import get_all_sessions
import config

class SessionRecommender:
    def __init__(self):
        # Initialize vector store
        self.vector_store = VectorStore()
        
        # Get all sessions
        self.sessions = get_all_sessions()
        
        # Build index if sessions exist
        if self.sessions:
            self._build_index()
    
    def _build_index(self):
        """Build vector index from sessions data"""
        if not self.sessions:
            print("No sessions available to build index")
            return
        max_sessions = 5000  # Adjust based on your hardware capabilities
        if len(self.sessions) > max_sessions:
            print(f"Limiting to {max_sessions} sessions for performance")
            self.sessions = self.sessions[:max_sessions]
        texts = []
        try:
            for session in self.sessions:
                # Extract relevant text from session
                session_title = session.get('session_title', '')
                description = session.get('description', '')
                if isinstance(description, dict) and 'root' in description:
                    # Handle structured description
                    description = str(description)
                session_text = f"{session_title} {description}"
                texts.append(session_text)
            
            # Create index
            if texts:
                self.vector_store.create_index(texts, self.sessions)
                print(f"Built index with {len(texts)} sessions")
            else:
                print("No session texts available to build index")
        except Exception as e:
            print(f"Error building session index: {e}")
            import traceback
            traceback.print_exc()
    
    def recommend_sessions(self, query, top_k=3):
        """Recommend sessions based on a query"""
        results = self.vector_store.search(query, top_k=top_k)
        
        # Extract recommended sessions
        recommendations = [result['item'] for result in results]
        
        return recommendations