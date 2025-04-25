import json
import os
from pathlib import Path
from src.utils.logger import logger

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        raise

def load_session_data():
    file_path = Path('data/raw/herkey.sessions.json')
    return load_json_file(file_path)

def load_embedding_data():
    file_path = Path('data/raw/herkey.sessions.embedding.json')
    return load_json_file(file_path)