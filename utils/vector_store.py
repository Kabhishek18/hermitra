# asha/utils/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle
import config
import hashlib
import time

class VectorStore:
    def __init__(self, model_name=config.VECTOR_MODEL):
        self.model_name = model_name
        self.model = None  # Lazy loading
        self.index = None
        self.items = []
        self.index_file = os.path.join(config.DATA_DIR, "vector_index.pkl")
        
        # Try to load existing index
        self._load_or_create_model()
        self.load(self.index_file)
    
    def _load_or_create_model(self):
        """Lazy load the model only when needed"""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
    
    def create_index(self, texts, items=None):
        """Create a FAISS index from texts with optimizations"""
        self._load_or_create_model()
        
        # Calculate a hash of the input texts to detect changes
        hash_val = hashlib.md5(str(texts).encode()).hexdigest()
        hash_file = os.path.join(config.DATA_DIR, "vector_index.hash")
        
        # Check if we already have an index with this hash
        if os.path.exists(hash_file) and os.path.exists(self.index_file):
            with open(hash_file, 'r') as f:
                if f.read() == hash_val:
                    print("Skipping index creation - no changes detected")
                    return
        
        print(f"Creating new index with {len(texts)} items")
        
        # Process in batches to reduce memory usage
        batch_size = 128
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(
                batch_texts, 
                show_progress_bar=True,
                convert_to_numpy=True
            )
            all_embeddings.append(batch_embeddings)
            # Optional: Allow CPU to cool down between batches
            time.sleep(0.1)
        
        embeddings = np.vstack(all_embeddings)
        
        # Create a more efficient index for faster search
        dimension = embeddings.shape[1]
        
        # Use IVF index for faster search with small accuracy trade-off
        if len(texts) > 1000:
            # Number of clusters - rule of thumb: sqrt(n) where n is dataset size
            n_clusters = min(int(np.sqrt(len(texts))), 256)
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            self.index.train(embeddings)
        else:
            # For smaller datasets, use flat index
            self.index = faiss.IndexFlatL2(dimension)
        
        self.index.add(embeddings.astype('float32'))
        
        # Store original items
        self.items = items if items else texts
        
        # Save the index hash
        os.makedirs(os.path.dirname(hash_file), exist_ok=True)
        with open(hash_file, 'w') as f:
            f.write(hash_val)
        
        # Save the index
        self.save(self.index_file)
    
    def search(self, query, top_k=5):
        """Search the index for similar items"""
        if not self.index:
            return []
        
        self._load_or_create_model()
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Search for similar items
        if isinstance(self.index, faiss.IndexIVFFlat):
            # Set number of probes to search (more probes = more accurate but slower)
            self.index.nprobe = 4
        
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            k=min(top_k, len(self.items))
        )
        
        # Get results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx >= 0 and idx < len(self.items):  # Check for valid index
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
        
        try:
            with open(path, 'wb') as f:
                pickle.dump({
                    'index': faiss.serialize_index(self.index),
                    'items': self.items
                }, f)
            return True
        except Exception as e:
            print(f"Error saving vector store: {e}")
            return False
    
    def load(self, path):
        """Load the vector store from disk"""
        if not os.path.exists(path):
            return False
        
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.index = faiss.deserialize_index(data['index'])
                self.items = data['items']
            print(f"Loaded vector index with {len(self.items)} items")
            return True
        except Exception as e:
            print(f"Error loading vector store: {e}")
            return False

# Initialize a global vector store
vector_store = VectorStore()