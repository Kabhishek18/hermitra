#!/usr/bin/env python3
"""
ASHA Application Launcher
Initializes and runs the ASHA career guidance chatbot with performance optimizations
"""

import os
import sys
import subprocess
import time
import argparse
import shutil
import signal
import threading
import psutil

# Define global variables for process management
streamlit_process = None
mongodb_process = None
ollama_process = None

def init_directories():
    """Initialize required directories for data storage"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/db", exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs(".streamlit", exist_ok=True)

def setup_streamlit_config():
    """Create optimized Streamlit configuration"""
    config_path = os.path.join(".streamlit", "config.toml")
    config_content = """
[server]
enableStaticServing = true
enableCORS = false
maxUploadSize = 20
maxMessageSize = 50

[browser]
gatherUsageStats = false

[runner]
# Disable file watching for torch to prevent segmentation fault
moduleExcludedFromWatching = ["torch", "tensorflow", "transformers", "langchain"]
fastReruns = true

[theme]
primaryColor = "#FF1493"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[logger]
level = "warning"
"""
    with open(config_path, "w") as f:
        f.write(config_content)
    print("Created Streamlit configuration for better performance")

def check_mongodb():
    """Check if MongoDB is installed and running"""
    try:
        # Check if MongoDB is in PATH
        mongodb_path = shutil.which("mongod")
        if not mongodb_path:
            print("MongoDB not found in PATH. Please install MongoDB.")
            return False
        
        # Try connecting to MongoDB
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print("MongoDB is running")
        return True
    except Exception:
        print("MongoDB is not running")
        return False

def start_mongodb():
    """Start MongoDB if not running"""
    global mongodb_process
    
    if check_mongodb():
        return True
    
    try:
        print("Starting MongoDB...")
        db_path = os.path.abspath("data/db")
        log_path = os.path.abspath("logs/mongodb.log")
        
        # Start MongoDB with reduced memory usage
        mongodb_process = subprocess.Popen(
            [
                "mongod",
                "--dbpath", db_path,
                "--logpath", log_path,
                "--wiredTigerCacheSizeGB", "0.5"  # Limit cache to 500MB
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for MongoDB to start
        time.sleep(3)
        
        # Verify MongoDB is running
        if check_mongodb():
            print("MongoDB started successfully")
            return True
        else:
            print("Failed to start MongoDB")
            return False
    except Exception as e:
        print(f"Error starting MongoDB: {e}")
        return False

def check_ollama():
    """Check if Ollama is installed and running"""
    try:
        # Check if Ollama is in PATH
        ollama_path = shutil.which("ollama")
        if not ollama_path:
            print("Ollama not found in PATH. Some AI features may be limited.")
            return False
        
        # Check if Ollama is running
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            # Check if the required model is available
            models = response.json().get("models", [])
            mistral_available = any(model.get("name", "").startswith("mistral") for model in models)
            
            if mistral_available:
                print("Ollama is running with Mistral model")
                return True
            else:
                print("Ollama is running but Mistral model is not available")
                # Pull the model if needed
                return False
        else:
            print("Ollama API returned unexpected response")
            return False
    except Exception:
        print("Ollama is not running")
        return False

def start_ollama():
    """Start Ollama if not running"""
    global ollama_process
    
    if check_ollama():
        return True
    
    try:
        print("Starting Ollama...")
        ollama_log_path = os.path.abspath("logs/ollama.log")
        
        with open(ollama_log_path, "w") as log_file:
            ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=log_file,
                stderr=log_file
            )
        
        # Wait for Ollama to start
        time.sleep(5)
        
        # Check if Ollama started successfully
        if check_ollama():
            print("Ollama started successfully")
            
            # Pull required model if needed
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    mistral_available = any(model.get("name", "").startswith("mistral") for model in models)
                    
                    if not mistral_available:
                        print("Pulling Mistral model (this may take a while)...")
                        subprocess.run(["ollama", "pull", "mistral:latest"], check=False)
            except Exception as e:
                print(f"Error checking/pulling models: {e}")
                
            return True
        else:
            print("Failed to start Ollama")
            return False
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def initialize_database():
    """Initialize database collections and sample data"""
    try:
        print("Initializing database...")
        subprocess.run([sys.executable, "initialize_db.py"], check=False)
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def start_streamlit():
    """Start Streamlit application"""
    global streamlit_process
    
    try:
        print("Starting ASHA application...")
        
        # Set environment variables to prevent PyTorch-Streamlit conflicts
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        env["STREAMLIT_THEME"] = "light"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"
        env["TORCH_JIT_DISABLE"] = "1"
        
        # Additional environment variables to optimize memory usage
        env["MALLOC_TRIM_THRESHOLD_"] = "65536"
        env["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings
        
        # Launch Streamlit
        streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "asha_app.py", "--server.maxUploadSize=20"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Start a thread to handle Streamlit output
        def handle_output():
            while streamlit_process and streamlit_process.poll() is None:
                output = streamlit_process.stdout.readline()
                if output:
                    print(f"[Streamlit] {output.strip()}")
        
        threading.Thread(target=handle_output, daemon=True).start()
        
        # Wait for Streamlit to start
        time.sleep(3)
        
        print("ASHA application is running at http://localhost:8501")
        return True
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        return False

def monitor_resources(interval=300):
    """Monitor system resources periodically"""
    while True:
        try:
            # Get current process
            process = psutil.Process(os.getpid())
            children = process.children(recursive=True)
            
            # Calculate total memory usage
            total_memory = process.memory_info().rss
            for child in children:
                try:
                    total_memory += child.memory_info().rss
                except:
                    pass
            
            total_memory_mb = total_memory / (1024 * 1024)
            
            print(f"Current memory usage: {total_memory_mb:.2f} MB")
            
            # Check if memory usage is too high
            if total_memory_mb > 1500:  # If using more than 1.5GB
                print("High memory usage detected. Consider restarting the application if performance degrades.")
        except Exception as e:
            print(f"Error monitoring resources: {e}")
        
        # Sleep for the specified interval
        time.sleep(interval)

def cleanup():
    """Clean up processes when exiting"""
    print("\nShutting down ASHA application...")
    
    if streamlit_process:
        print("Stopping Streamlit...")
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=5)
        except:
            streamlit_process.kill()
    
    # We don't automatically shut down MongoDB or Ollama
    # as they may be used by other applications
    print("Shutdown complete. MongoDB and Ollama remain running.")
    print("To stop them manually, use:")
    print("- MongoDB: Use Ctrl+C in the MongoDB terminal or 'mongod --shutdown'")
    print("- Ollama: Use Ctrl+C in the Ollama terminal or kill the process")

def handle_signal(sig, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal")
    cleanup()
    sys.exit(0)

def main():
    """Main function to run the ASHA application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ASHA Career Guidance Chatbot Launcher")
    parser.add_argument("--init-only", action="store_true", help="Initialize only without starting")
    parser.add_argument("--skip-db", action="store_true", help="Skip MongoDB initialization")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama initialization")
    parser.add_argument("--monitor", action="store_true", help="Enable resource monitoring")
    args = parser.parse_args()
    
    print("ASHA Career Guidance Chatbot Launcher")
    print("====================================")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Initialize directories
    init_directories()
    
    # Setup Streamlit configuration
    setup_streamlit_config()
    
    # Start MongoDB if needed
    if not args.skip_db:
        if not start_mongodb():
            print("Warning: MongoDB initialization failed. Continuing with limited functionality.")
    
    # Initialize database
    if not args.skip_db:
        initialize_database()
    
    # Start Ollama if needed
    if not args.skip_ollama:
        if not start_ollama():
            print("Warning: Ollama initialization failed. Chatbot will use fallback responses.")
    
    # Exit if init-only mode
    if args.init_only:
        print("Initialization complete. Exiting without starting the application.")
        return 0
    
    # Start the application
    if not start_streamlit():
        print("Error: Failed to start the application.")
        cleanup()
        return 1
    
    # Start resource monitoring if enabled
    if args.monitor:
        print("Starting resource monitor...")
        monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
    
    # Keep the script running while Streamlit is active
    try:
        while streamlit_process and streamlit_process.poll() is None:
            time.sleep(1)
        
        # If we get here, Streamlit has exited
        print("Streamlit process exited with code:", streamlit_process.returncode)
        cleanup()
        return streamlit_process.returncode
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
        cleanup()
        return 0

if __name__ == "__main__":
    sys.exit(main())