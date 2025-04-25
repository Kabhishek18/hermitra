# asha/config.py
import os

# Application settings
APP_NAME = "ASHA - Career Guidance Assistant"
APP_ICON = "👩‍💼"

# Ollama settings
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "mistral:latest"

# MongoDB settings
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "asha_db"
MONGO_SESSIONS_COLLECTION = "sessions"
MONGO_USER_HISTORY_COLLECTION = "user_history"

# Vector database settings
VECTOR_MODEL = "all-MiniLM-L6-v2"

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")