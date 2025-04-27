# asha/utils/vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import sys
import pickle
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class VectorStore:
    def __init__(self, model_name=config.VECTOR_MODEL):
        self.model_name = model_name
        self.model = None  # Lazy loading
        self.index = None
        self.items = []
        self.index_file = config.VECTOR_INDEX_PATH
        
        # Try to load existing index
        self.load(self.index_file)
    
    def _load_model(self):
        """Lazy load the model only when needed"""
        if self.model is None:
            print(f"Loading sentence transformer model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
                print(f"Successfully loaded model: {self.model_name}")
            except Exception as e:
                print(f"Error loading model: {e}")
                # Fallback to a simpler model if available
                try:
                    fallback_model = "paraphrase-MiniLM-L3-v2"  # Smaller model as fallback
                    print(f"Trying fallback model: {fallback_model}")
                    self.model = SentenceTransformer(fallback_model)
                    print(f"Successfully loaded fallback model")
                except Exception as e2:
                    print(f"Failed to load fallback model: {e2}")
                    raise
    
    def create_index(self, texts, items=None):
        """Create a FAISS index from texts"""
        # Load model if not already loaded
        self._load_model()
        
        print(f"Creating index with {len(texts)} items")
        start_time = time.time()
        
        # Process in batches to reduce memory usage
        batch_size = config.BATCH_SIZE
        all_embeddings = []
        
        total_batches = (len(texts) + batch_size - 1) // batch_size
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{total_batches}")
            
            batch_embeddings = self.model.encode(
                batch_texts, 
                show_progress_bar=False,
                convert_to_numpy=True
            )
            all_embeddings.append(batch_embeddings)
        
        embeddings = np.vstack(all_embeddings)
        dimension = embeddings.shape[1]
        
        # Create appropriate index based on dataset size
        if len(texts) > 1000:
            # For larger datasets, use IVF index
            n_clusters = min(int(4 * np.sqrt(len(texts))), 256)
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            
            # Train the index
            print(f"Training IVF index with {n_clusters} clusters")
            self.index.train(embeddings)
            self.index.nprobe = min(16, n_clusters // 4)  # Balance performance vs accuracy
        else:
            # For smaller datasets, use flat index
            print("Using flat index for small dataset")
            self.index = faiss.IndexFlatL2(dimension)
        
        # Add vectors to index
        print("Adding vectors to index")
        self.index.add(embeddings.astype('float32'))
        
        # Store original items
        self.items = items if items else texts
        
        # Save the index
        self.save(self.index_file)
        
        elapsed_time = time.time() - start_time
        print(f"Index creation completed in {elapsed_time:.2f} seconds")
    
    def search(self, query, top_k=5):
        """Search the index for similar items"""
        if not self.index or not self.items:
            return []
        
        # Load model if not already loaded
        self._load_model()
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Configure search parameters
        if isinstance(self.index, faiss.IndexIVFFlat):
            # For IVF, set number of clusters to search
            self.index.nprobe = min(16, self.index.nlist // 4)
        
        # Search for similar items
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            k=min(top_k, len(self.items))
        )
        
        # Get results
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            distance = distances[0][i]
            
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
            print(f"Saved vector store to {path}")
            return True
        except Exception as e:
            print(f"Error saving vector store: {e}")
            return False
    
    def load(self, path):
        """Load the vector store from disk"""
        if not os.path.exists(path):
            print(f"No existing index found at {path}")
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