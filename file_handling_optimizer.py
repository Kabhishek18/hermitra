"""
Optimized file handling utilities for ASHA chatbot
Provides efficient file reading, processing and caching
"""

import os
import io
import json
import mimetypes
import hashlib
import pickle
import time
import threading
import csv
from functools import lru_cache
from typing import Dict, Any, Optional, BinaryIO, Union, List, Tuple, Generator

# Global file cache with expiration
_FILE_CACHE = {}
_FILE_CACHE_LOCK = threading.RLock()
_FILE_CACHE_MAX_SIZE = 50  # Maximum number of files to cache
_FILE_CACHE_EXPIRATION = 3600  # Cache expiration in seconds (1 hour)
_FILE_CACHE_LAST_CLEANUP = 0  # Last cleanup timestamp

class FileChunkReader:
    """
    Read files in chunks to avoid loading entire file into memory
    """
    
    def __init__(self, file_path: str, chunk_size: int = 1024 * 1024):
        """
        Initialize a chunk reader for large files
        
        Args:
            file_path: Path to the file
            chunk_size: Size of each chunk in bytes (default: 1MB)
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.file = None
    
    def __enter__(self):
        """Context manager enter"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        self.file = open(self.file_path, 'rb')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.file:
            self.file.close()
    
    def read_chunks(self):
        """
        Generator that yields chunks of the file
        
        Yields:
            bytes: Chunks of the file
        """
        if not self.file:
            raise ValueError("File is not open. Use with context manager.")
        
        while True:
            chunk = self.file.read(self.chunk_size)
            if not chunk:
                break
            
            yield chunk

def file_hash(file_path: str) -> str:
    """
    Calculate the hash of a file for caching purposes
    
    Args:
        file_path: Path to the file
    
    Returns:
        str: File hash
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # For small files, hash the entire file
    if os.path.getsize(file_path) < 10 * 1024 * 1024:  # 10MB
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    # For large files, hash selected portions to save time
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read the first 1MB
        hasher.update(f.read(1024 * 1024))
        
        # Position to the middle
        f.seek(os.path.getsize(file_path) // 2)
        hasher.update(f.read(1024 * 1024))
        
        # Read the last 1MB
        f.seek(-1024 * 1024, os.SEEK_END)
        hasher.update(f.read(1024 * 1024))
    
    return hasher.hexdigest()

def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get metadata about a file without reading its contents
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File metadata
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat = os.stat(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    
    return {
        "path": file_path,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "mime_type": mime_type or "application/octet-stream",
        "extension": os.path.splitext(file_path)[1],
        "filename": os.path.basename(file_path)
    }

def read_file_cached(file_path: str, force_reload: bool = False) -> bytes:
    """
    Read a file with caching to improve performance
    
    Args:
        file_path: Path to the file
        force_reload: Whether to force a reload from disk
        
    Returns:
        bytes: File contents
    """
    global _FILE_CACHE, _FILE_CACHE_LAST_CLEANUP
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check if cleanup is needed
    current_time = time.time()
    if current_time - _FILE_CACHE_LAST_CLEANUP > 3600:  # Once per hour
        cleanup_file_cache()
    
    # Use file metadata for cache key (path + modification time)
    metadata = get_file_metadata(file_path)
    cache_key = f"{file_path}:{metadata['modified']}"
    
    with _FILE_CACHE_LOCK:
        if not force_reload and cache_key in _FILE_CACHE:
            # Update access time
            _FILE_CACHE[cache_key]["last_access"] = current_time
            return _FILE_CACHE[cache_key]["data"]
    
    # Read the file
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Cache the data
    with _FILE_CACHE_LOCK:
        _FILE_CACHE[cache_key] = {
            "data": data,
            "size": len(data),
            "created": current_time,
            "last_access": current_time
        }
        
        # If cache is too large, remove oldest entries
        if len(_FILE_CACHE) > _FILE_CACHE_MAX_SIZE:
            # Sort by last access time
            items = list(_FILE_CACHE.items())
            items.sort(key=lambda x: x[1]["last_access"])
            
            # Remove oldest items
            for key, _ in items[:len(items) - _FILE_CACHE_MAX_SIZE]:
                del _FILE_CACHE[key]
    
    return data

def cleanup_file_cache():
    """Clean up expired file cache entries"""
    global _FILE_CACHE, _FILE_CACHE_LAST_CLEANUP
    
    current_time = time.time()
    _FILE_CACHE_LAST_CLEANUP = current_time
    
    with _FILE_CACHE_LOCK:
        # Find expired entries
        expired_keys = [
            key for key, value in _FILE_CACHE.items()
            if current_time - value["last_access"] > _FILE_CACHE_EXPIRATION
        ]
        
        # Remove expired entries
        for key in expired_keys:
            del _FILE_CACHE[key]

def process_csv_file(file_path: str, callback=None, chunk_size: int = 10000) -> List[Dict[str, Any]]:
    """
    Process a CSV file in chunks to avoid memory issues
    
    Args:
        file_path: Path to the CSV file
        callback: Optional callback function to process each chunk
        chunk_size: Number of rows per chunk
        
    Returns:
        list: List of dictionaries representing rows
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check file size
    file_size = os.path.getsize(file_path)
    
    # For small files, process normally
    if file_size < 50 * 1024 * 1024:  # 50MB
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if callback:
                for chunk in _chunked_iterable(reader, chunk_size):
                    callback(chunk)
                return []
            else:
                return list(reader)
    
    # For large files, process in chunks
    results = []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Process in chunks to avoid memory issues
        chunk = []
        for i, row in enumerate(reader):
            chunk.append(row)
            
            if len(chunk) >= chunk_size:
                if callback:
                    callback(chunk)
                else:
                    results.extend(chunk)
                chunk = []
        
        # Process the last chunk
        if chunk:
            if callback:
                callback(chunk)
            else:
                results.extend(chunk)
    
    return results if not callback else []

def _chunked_iterable(iterable, size):
    """
    Split an iterable into chunks of specified size
    
    Args:
        iterable: The iterable to split
        size: Maximum size of each chunk
        
    Yields:
        list: Chunks of the iterable
    """
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    
    if chunk:
        yield chunk

def process_json_file(file_path: str) -> Any:
    """
    Process a JSON file with optimized memory usage
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Any: Parsed JSON data
    """
    # For JSON files, use the cached file reader
    try:
        data = read_file_cached(file_path)
        return json.loads(data.decode('utf-8'))
    except json.JSONDecodeError as e:
        # Try to repair common JSON issues
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for trailing commas
        content = _fix_trailing_commas(content)
        
        # Try parsing again
        return json.loads(content)

def _fix_trailing_commas(json_str: str) -> str:
    """
    Fix trailing commas in JSON strings
    
    Args:
        json_str: JSON string that might have trailing commas
        
    Returns:
        str: Fixed JSON string
    """
    # Replace trailing commas in arrays
    json_str = _replace_pattern(json_str, r',\s*]', ']')
    
    # Replace trailing commas in objects
    json_str = _replace_pattern(json_str, r',\s*}', '}')
    
    return json_str

def _replace_pattern(text: str, pattern: str, replacement: str) -> str:
    """
    Replace regex pattern in text
    
    Args:
        text: Input text
        pattern: Regex pattern to replace
        replacement: Replacement string
        
    Returns:
        str: Text with replacements
    """
    import re
    return re.sub(pattern, replacement, text)

# Optimized file system interface for ASHA
class FileSystem:
    """
    Optimized file system interface for ASHA chatbot
    """
    
    @staticmethod
    def read_file(file_path: str, encoding: Optional[str] = None) -> Union[bytes, str]:
        """
        Read a file with optimized memory usage
        
        Args:
            file_path: Path to the file
            encoding: Optional encoding for text files
            
        Returns:
            bytes or str: File contents
        """
        data = read_file_cached(file_path)
        
        if encoding:
            return data.decode(encoding)
        return data
    
    @staticmethod
    def write_file(file_path: str, data: Union[bytes, str], encoding: Optional[str] = None) -> None:
        """
        Write data to a file
        
        Args:
            file_path: Path to the file
            data: Data to write
            encoding: Optional encoding for text data
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Write the file
        mode = 'wb' if isinstance(data, bytes) else 'w'
        with open(file_path, mode, encoding=encoding) as f:
            f.write(data)
        
        # Invalidate cache
        with _FILE_CACHE_LOCK:
            for key in list(_FILE_CACHE.keys()):
                if key.startswith(file_path + ":"):
                    del _FILE_CACHE[key]
    
    @staticmethod
    def process_csv(file_path: str, callback=None) -> List[Dict[str, Any]]:
        """
        Process a CSV file with optimized memory usage
        
        Args:
            file_path: Path to the CSV file
            callback: Optional callback function to process each chunk
            
        Returns:
            list: List of dictionaries representing rows
        """
        return process_csv_file(file_path, callback)
    
    @staticmethod
    def process_json(file_path: str) -> Any:
        """
        Process a JSON file with optimized memory usage
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Any: Parsed JSON data
        """
        return process_json_file(file_path)
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        Get information about a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict: File information
        """
        return get_file_metadata(file_path)
    
    @staticmethod
    def list_directory(directory: str, pattern: Optional[str] = None) -> List[str]:
        """
        List files in a directory with optional pattern matching
        
        Args:
            directory: Path to the directory
            pattern: Optional file pattern to match
            
        Returns:
            list: List of file paths
        """
        import glob
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        if pattern:
            return glob.glob(os.path.join(directory, pattern))
        else:
            return [os.path.join(directory, f) for f in os.listdir(directory)]