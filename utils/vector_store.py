# asha/utils/enhanced_vector_store.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import pickle
import config
import hashlib
import time
import logging
from typing import List, Dict, Any, Tuple, Optional, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced_vector_store")

class VectorStore:
    """
    Enhanced vector store with improved search capabilities.
    Features:
    - Full collection indexing
    - Efficient HNSW indexing for large collections
    - Hybrid search (semantic + keyword)
    - Batched processing for memory efficiency
    """
    def __init__(self, model_name=config.VECTOR_MODEL):
        self.model_name = model_name
        self.model = None  # Lazy loading
        self.index = None
        self.items = []
        self.texts = []  # Store original texts for keyword matching
        self.index_file = os.path.join(config.DATA_DIR, "enhanced_vector_index.pkl")
        
        # Try to load existing index
        self._load_or_create_model()
        self.load(self.index_file)
    
    def _load_or_create_model(self):
        """Lazy load the model only when needed"""
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Successfully loaded model: {self.model_name}")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                # Fallback to a simpler model if available
                try:
                    fallback_model = "paraphrase-MiniLM-L3-v2"  # Smaller model as fallback
                    logger.info(f"Trying fallback model: {fallback_model}")
                    self.model = SentenceTransformer(fallback_model)
                    logger.info(f"Successfully loaded fallback model")
                except Exception as e2:
                    logger.error(f"Failed to load fallback model: {e2}")
                    raise
    
    def create_index(self, texts: List[str], items: Optional[List[Any]] = None):
        """
        Create a FAISS index from texts with optimizations for large collections.
        
        Args:
            texts: List of text strings to index
            items: Optional list of corresponding items to return in search results
        """
        self._load_or_create_model()
        
        # Calculate a hash of the input texts to detect changes
        hash_val = hashlib.md5(str(len(texts)).encode()).hexdigest()
        hash_file = os.path.join(config.DATA_DIR, "enhanced_vector_index.hash")
        
        # Check if we already have an index with this hash and it's not forced
        if os.path.exists(hash_file) and os.path.exists(self.index_file):
            try:
                with open(hash_file, 'r') as f:
                    if f.read() == hash_val:
                        logger.info("Skipping index creation - no changes detected")
                        return
            except:
                # If there's any issue reading the hash, proceed with indexing
                pass
                
        logger.info(f"Creating new index with {len(texts)} items")
        start_time = time.time()
        
        # Store original texts for keyword matching
        self.texts = texts
        
        # Process in batches to reduce memory usage
        batch_size = config.BATCH_SIZE
        all_embeddings = []
        
        total_batches = (len(texts) + batch_size - 1) // batch_size
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{total_batches} with {len(batch_texts)} texts")
            
            batch_embeddings = self.model.encode(
                batch_texts, 
                show_progress_bar=False,
                convert_to_numpy=True
            )
            all_embeddings.append(batch_embeddings)
            # Allow CPU to cool down between batches
            time.sleep(0.1)
        
        logger.info("Combining embeddings")
        embeddings = np.vstack(all_embeddings)
        
        # Create a more efficient index based on collection size
        dimension = embeddings.shape[1]
        
        # For larger collections, use HNSW index (Hierarchical Navigable Small World)
        # This provides better recall with faster search compared to IVF
        logger.info(f"Building FAISS index with dimension {dimension}")
        if len(texts) > 5000:
            # HNSW index with optimized parameters for large collections
            self.index = faiss.IndexHNSWFlat(dimension, 32)  # 32 neighbors per node
            self.index.hnsw.efConstruction = 40  # Higher value = better quality but slower build
            self.index.hnsw.efSearch = 16  # Higher value = better recall but slower search
        elif len(texts) > 1000:
            # For medium-sized collections, use IVF index with appropriate cluster count
            n_clusters = min(4 * int(np.sqrt(len(texts))), 256)  # Improved cluster count formula
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            # Train the index
            logger.info(f"Training IVF index with {n_clusters} clusters")
            self.index.train(embeddings)
            self.index.nprobe = min(16, n_clusters // 4)  # Set probes to balance speed vs accuracy
        else:
            # For small collections, use flat index
            logger.info("Using flat index for small collection")
            self.index = faiss.IndexFlatL2(dimension)
        
        # Add vectors to index
        logger.info("Adding vectors to index")
        self.index.add(embeddings.astype('float32'))
        
        # Store original items
        self.items = items if items else texts
        
        # Save the index hash
        os.makedirs(os.path.dirname(hash_file), exist_ok=True)
        with open(hash_file, 'w') as f:
            f.write(hash_val)
        
        # Save the index
        self.save(self.index_file)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Index creation completed in {elapsed_time:.2f} seconds")
    
    def hybrid_search(self, query: str, top_k: int = 5, semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic similarity and keyword matching.
        
        Args:
            query: The search query
            top_k: Number of results to return
            semantic_weight: Weight for semantic search vs keyword matching (0.0-1.0)
            
        Returns:
            List of result dictionaries with item and score
        """
        if not self.index or not self.items:
            return []
            
        # Get semantic search results
        semantic_results = self._semantic_search(query, top_k * 2)  # Get more results for reranking
        
        # Skip keyword matching if semantic weight is 1.0
        if semantic_weight >= 1.0:
            return semantic_results[:top_k]
            
        # Perform keyword matching
        keyword_results = self._keyword_search(query, top_k * 2)
        
        # Combine and rerank results
        combined_results = self._combine_results(
            semantic_results, 
            keyword_results, 
            semantic_weight=semantic_weight
        )
        
        # Return top results
        return combined_results[:top_k]
    
    def _semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search using the vector index"""
        if not self.index:
            return []
        
        self._load_or_create_model()
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Configure search parameters based on index type
        if isinstance(self.index, faiss.IndexIVFFlat):
            # For IVF, set number of clusters to search
            self.index.nprobe = min(32, self.index.nlist // 4)  # Balance between speed and recall
        elif hasattr(self.index, 'hnsw'):
            # For HNSW, set efSearch parameter
            self.index.hnsw.efSearch = 128  # Increased for better recall
        
        # Search for similar items
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            k=min(top_k, len(self.items))
        )
        
        # Get results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx >= 0 and idx < len(self.items):  # Check for valid index
                # Convert distance to similarity score (higher is better)
                similarity = 1.0 / (1.0 + distance)
                results.append({
                    'item': self.items[idx],
                    'score': similarity,
                    'source': 'semantic'
                })
        
        return results
    
    def _keyword_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform keyword-based search on the indexed texts"""
        if not self.texts:
            return []
            
        # Normalize query for matching
        query_terms = query.lower().split()
        
        # Skip very short or common words
        query_terms = [term for term in query_terms if len(term) > 2]
        if not query_terms:
            return []
            
        # Calculate scores for each item
        scores = []
        for i, text in enumerate(self.texts):
            text_lower = text.lower()
            
            # Calculate simple TF score
            score = 0
            for term in query_terms:
                if term in text_lower:
                    # Count occurrences and normalize by text length
                    term_count = text_lower.count(term)
                    score += term_count / max(len(text_lower.split()), 1)
            
            if score > 0:
                scores.append((i, score))
                
        # Sort by score and get top results
        scores.sort(key=lambda x: x[1], reverse=True)
        top_scores = scores[:top_k]
        
        # Format results
        results = []
        for idx, score in top_scores:
            results.append({
                'item': self.items[idx],
                'score': min(score * 3.0, 1.0),  # Scale up but cap at 1.0
                'source': 'keyword'
            })
            
        return results
    
    def _combine_results(
        self, 
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Combine and rerank semantic and keyword search results"""
        # Create a unified scoring system
        combined_scores = {}
        
        # Process semantic results
        for result in semantic_results:
            item_id = self._get_item_id(result['item'])
            if item_id not in combined_scores:
                combined_scores[item_id] = {
                    'item': result['item'],
                    'semantic_score': result['score'],
                    'keyword_score': 0.0
                }
            
        # Process keyword results
        for result in keyword_results:
            item_id = self._get_item_id(result['item'])
            if item_id in combined_scores:
                combined_scores[item_id]['keyword_score'] = result['score']
            else:
                combined_scores[item_id] = {
                    'item': result['item'],
                    'semantic_score': 0.0,
                    'keyword_score': result['score']
                }
        
        # Calculate combined scores
        result_list = []
        for item_id, data in combined_scores.items():
            # Weighted combination of scores
            combined_score = (
                semantic_weight * data['semantic_score'] + 
                (1.0 - semantic_weight) * data['keyword_score']
            )
            
            result_list.append({
                'item': data['item'],
                'score': combined_score,
                'semantic_score': data['semantic_score'],
                'keyword_score': data['keyword_score']
            })
        
        # Sort by combined score
        result_list.sort(key=lambda x: x['score'], reverse=True)
        return result_list
    
    def _get_item_id(self, item: Any) -> str:
        """Generate a unique identifier for an item for deduplication"""
        # If item has a session_id, use that
        if isinstance(item, dict) and 'session_id' in item:
            return str(item['session_id'])
        
        # Otherwise hash the item
        return hashlib.md5(str(item).encode()).hexdigest()
            
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index for similar items using pure semantic search.
        For most use cases, hybrid_search() is recommended instead.
        """
        return self._semantic_search(query, top_k)
    
    def save(self, path: str) -> bool:
        """Save the vector store to disk"""
        if not self.index:
            return False
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            with open(path, 'wb') as f:
                pickle.dump({
                    'index': faiss.serialize_index(self.index),
                    'items': self.items,
                    'texts': self.texts
                }, f)
            logger.info(f"Saved vector store to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Load the vector store from disk"""
        if not os.path.exists(path):
            logger.info(f"No existing index found at {path}")
            return False
        
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.index = faiss.deserialize_index(data['index'])
                self.items = data['items']
                self.texts = data.get('texts', [])  # Support older versions without texts
            logger.info(f"Loaded vector index with {len(self.items)} items")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False
    
    def add_items(self, new_texts: List[str], new_items: List[Any], rebuild: bool = False):
        """
        Add new items to the index.
        
        Args:
            new_texts: List of new text strings to index
            new_items: List of corresponding items to return in search results
            rebuild: Whether to rebuild the entire index (recommended for large additions)
        """
        if not new_texts or not new_items or len(new_texts) != len(new_items):
            logger.error("Invalid new texts or items")
            return False
            
        if not self.index or rebuild:
            # Combine existing and new data
            all_texts = self.texts + new_texts
            all_items = self.items + new_items
            # Rebuild index from scratch
            self.create_index(all_texts, all_items)
            return True
            
        # Add to existing index
        self._load_or_create_model()
        
        # Encode new texts
        logger.info(f"Adding {len(new_texts)} new items to index")
        embeddings = self.model.encode(new_texts, convert_to_numpy=True)
        
        # Add to index
        self.index.add(embeddings.astype('float32'))
        
        # Update items and texts
        self.items.extend(new_items)
        self.texts.extend(new_texts)
        
        # Save updated index
        self.save(self.index_file)
        logger.info(f"Added {len(new_texts)} items to index")
        return True


vector_store = VectorStore()