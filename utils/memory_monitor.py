# asha/utils/memory_monitor.py
import os
import psutil
import gc
import logging
import time
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("memory_usage.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("memory_monitor")

class MemoryMonitor:
    def __init__(self, threshold_percent=80, check_interval=30):
        """
        Initialize memory monitor
        
        Args:
            threshold_percent: Memory usage threshold to trigger cleanup (percentage)
            check_interval: How often to check memory usage (seconds)
        """
        self.threshold_percent = threshold_percent
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
    
    def get_memory_usage(self):
        """Get current memory usage as percentage"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # Log detailed memory info
        logger.info(f"Memory usage: {memory_percent:.1f}% ({memory_info.rss / (1024 * 1024):.1f} MB)")
        
        return memory_percent
    
    def cleanup_memory(self):
        """Perform memory cleanup operations"""
        logger.info("Performing memory cleanup")
        
        # Force garbage collection
        collected = gc.collect()
        logger.info(f"Garbage collector: collected {collected} objects")
        
        # Report memory after cleanup
        memory_percent = self.get_memory_usage()
        logger.info(f"Memory after cleanup: {memory_percent:.1f}%")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                memory_percent = self.get_memory_usage()
                
                # Check if we need to clean up
                if memory_percent > self.threshold_percent:
                    logger.warning(f"Memory usage above threshold: {memory_percent:.1f}%")
                    self.cleanup_memory()
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
            
            # Sleep before next check
            time.sleep(self.check_interval)
    
    def start(self):
        """Start the memory monitor"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Memory monitor started")
    
    def stop(self):
        """Stop the memory monitor"""
        if self.running:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1)
            logger.info("Memory monitor stopped")

# Global instance
memory_monitor = MemoryMonitor()

def start_monitoring():
    """Start memory monitoring"""
    memory_monitor.start()

def stop_monitoring():
    """Stop memory monitoring"""
    memory_monitor.stop()

def force_cleanup():
    """Force memory cleanup"""
    memory_monitor.cleanup_memory()