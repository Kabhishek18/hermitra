# asha/config.py
import os
import multiprocessing

# Application settings
APP_NAME = "ASHA - Career Guidance Assistant"
APP_ICON = "👩‍💼"

# Ollama settings
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral:latest"
MAX_CONTEXT_SIZE = 2048
MAX_RESPONSE_TOKENS = 800

# MongoDB settings
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "asha_db"
MONGO_SESSIONS_COLLECTION = "sessions"
MONGO_USER_HISTORY_COLLECTION = "user_history"
MONGO_MAX_POOL_SIZE = 10
MONGO_MIN_POOL_SIZE = 1

# Vector database settings
VECTOR_MODEL = "all-MiniLM-L6-v2"  # Fast and lightweight model

# Performance settings
CPU_COUNT = max(1, multiprocessing.cpu_count() - 1)
BATCH_SIZE = 32  # For vector operations

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
VECTOR_INDEX_PATH = os.path.join(DATA_DIR, "vector_index.pkl")

# Cache settings
CACHE_TTL = 3600  # Cache lifetime in seconds
MAX_CACHE_ITEMS = 100