# asha/utils/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle
import config

class VectorStore:
    def __init__(self, model_name=config.VECTOR_MODEL):
        # Load sentence transformer model
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.items = []
        
    def create_index(self, texts, items=None):
        """Create a FAISS index from texts"""
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
        
        # Store original items
        self.items = items if items else texts
        
    def search(self, query, top_k=5):
        """Search the index for similar items"""
        if not self.index:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Search for similar items
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            k=top_k
        )
        
        # Get results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.items):
                results.append({
                    'item': self.items[idx],
                    'distance': float(distance)
                })
        
        return results
    
    def save(self, path):
        """Save the vector store to disk"""
        if not self.index:
            return False
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'index': faiss.serialize_index(self.index),
                'items': self.items
            }, f)
        
        return True
    
    def load(self, path):
        """Load the vector store from disk"""
        if not os.path.exists(path):
            return False
        
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.index = faiss.deserialize_index(data['index'])
                self.items = data['items']
            return True
        except Exception as e:
            print(f"Error loading vector store: {e}")
            return False

# Initialize a global vector store
vector_store = VectorStore()