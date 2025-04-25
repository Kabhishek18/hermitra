# asha/config.py
import os
import multiprocessing

# Application settings
APP_NAME = "ASHA - Career Guidance Assistant"
APP_ICON = "👩‍💼"

# Ollama settings
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral:latest"
# Smaller context size for faster responses
MAX_CONTEXT_SIZE = 2048
# Smaller response size for faster generation
MAX_RESPONSE_TOKENS = 800

# MongoDB settings
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "asha_db"
MONGO_SESSIONS_COLLECTION = "sessions"
MONGO_USER_HISTORY_COLLECTION = "user_history"
# Add connection pooling limits
MONGO_MAX_POOL_SIZE = 10
MONGO_MIN_POOL_SIZE = 1

# Vector database settings
# Use a smaller, faster model for embeddings
VECTOR_MODEL = "all-MiniLM-L6-v2"  # Fast and lightweight

# Performance settings
# Auto-detect CPU count and use slightly fewer for Streamlit
CPU_COUNT = max(1, multiprocessing.cpu_count() - 1)
BATCH_SIZE = 32  # Smaller batches for vector operations

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
VECTOR_INDEX_PATH = os.path.join(DATA_DIR, "vector_index.pkl")

# Cache settings
CACHE_TTL = 3600  # Cache lifetime in seconds
MAX_CACHE_ITEMS = 100