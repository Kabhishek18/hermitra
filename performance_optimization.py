"""
Performance optimization utilities for ASHA chatbot
Provides memory management, lazy loading, and resource monitoring
"""

import os
import gc
import time
import threading
import psutil
from functools import lru_cache
import weakref

# Global performance settings
MEMORY_CHECK_INTERVAL = 300  # Check memory usage every 5 minutes
MEMORY_THRESHOLD = 70        # Percentage of memory usage that triggers cleanup
INACTIVE_TIMEOUT = 3600      # Time in seconds before resources are considered inactive (1 hour)

# Global resource tracking
_resource_registry = weakref.WeakValueDictionary()
_resource_last_access = {}
_resource_lock = threading.RLock()

class ResourceTracker:
    """Track and manage resource usage"""
    
    @staticmethod
    def register(resource_id, resource):
        """Register a resource for tracking"""
        with _resource_lock:
            _resource_registry[resource_id] = resource
            _resource_last_access[resource_id] = time.time()
    
    @staticmethod
    def access(resource_id):
        """Record access to a resource"""
        with _resource_lock:
            if resource_id in _resource_registry:
                _resource_last_access[resource_id] = time.time()
    
    @staticmethod
    def cleanup_inactive():
        """Clean up inactive resources"""
        now = time.time()
        with _resource_lock:
            # Find inactive resources
            inactive_ids = [
                resource_id for resource_id, last_access in _resource_last_access.items()
                if now - last_access > INACTIVE_TIMEOUT
            ]
            
            # Remove inactive resources
            for resource_id in inactive_ids:
                if resource_id in _resource_registry:
                    # Resource is already removed if the weak reference is gone
                    pass
                
                # Clean up tracking data
                if resource_id in _resource_last_access:
                    del _resource_last_access[resource_id]
            
            # Force garbage collection
            gc.collect()

class MemoryMonitor:
    """Monitor and optimize memory usage"""
    
    def __init__(self, check_interval=MEMORY_CHECK_INTERVAL, threshold=MEMORY_THRESHOLD):
        self.check_interval = check_interval
        self.threshold = threshold
        self.last_check = 0
        self.is_running = False
        self.monitor_thread = None
    
    def start(self):
        """Start the memory monitoring thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """Stop the memory monitoring thread"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Background thread to monitor memory usage"""
        while self.is_running:
            try:
                self.check_memory()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in memory monitor: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def check_memory(self):
        """Check memory usage and optimize if needed"""
        try:
            # Get current memory usage
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            memory_mb = memory_info.rss / (1024 * 1024)
            print(f"Current memory usage: {memory_mb:.2f} MB ({memory_percent:.1f}%)")
            
            # Check if optimization is needed
            if memory_percent > self.threshold:
                print(f"Memory usage above threshold ({self.threshold}%). Running optimization...")
                self.optimize_memory()
            
            # Regularly clean up inactive resources regardless of memory usage
            ResourceTracker.cleanup_inactive()
            
            self.last_check = time.time()
            return memory_mb
        except Exception as e:
            print(f"Error checking memory: {e}")
            return None
    
    def optimize_memory(self):
        """Optimize memory usage"""
        # Clear caches
        lru_cache.cache_clear()
        
        # Clean up inactive resources
        ResourceTracker.cleanup_inactive()
        
        # Run garbage collection
        gc.collect()
        
        # Log after optimization
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            print(f"Memory usage after optimization: {memory_mb:.2f} MB")
        except:
            pass

class LazyLoader:
    """Lazy load modules and resources only when needed"""
    
    def __init__(self, loader_func, resource_id=None):
        self.loader_func = loader_func
        self.resource = None
        self.resource_id = resource_id or id(self)
    
    def get(self):
        """Get the resource, loading it if necessary"""
        if self.resource is None:
            self.resource = self.loader_func()
            ResourceTracker.register(self.resource_id, self.resource)
        else:
            ResourceTracker.access(self.resource_id)
        
        return self.resource
    
    def is_loaded(self):
        """Check if the resource is loaded"""
        return self.resource is not None
    
    def unload(self):
        """Unload the resource to free memory"""
        self.resource = None
        gc.collect()

# File operations with streaming to avoid loading large files into memory
def process_file_in_chunks(file_path, chunk_processor, chunk_size=1024*1024):
    """
    Process a file in chunks to avoid loading it entirely into memory
    
    Args:
        file_path: Path to the file
        chunk_processor: Function that processes each chunk
        chunk_size: Size of each chunk in bytes
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            chunk_processor(chunk)

# Create a global memory monitor instance
memory_monitor = MemoryMonitor()

# Helper functions to use in the main application
def start_memory_monitoring():
    """Start the memory monitoring thread"""
    memory_monitor.start()

def stop_memory_monitoring():
    """Stop the memory monitoring thread"""
    memory_monitor.stop()

def check_memory():
    """Check memory usage and optimize if needed"""
    return memory_monitor.check_memory()

def optimize_memory():
    """Force memory optimization"""
    return memory_monitor.optimize_memory()