#!/usr/bin/env python
# asha/start.py
import os
import sys
import subprocess
import signal
import time

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Start Ollama service"""
    print("Starting Ollama service...")
    try:
        # Start Ollama as a background process
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for Ollama to start
        max_attempts = 10
        for attempt in range(max_attempts):
            print(f"Waiting for Ollama to start... ({attempt+1}/{max_attempts})")
            if check_ollama():
                print("Ollama started successfully!")
                return True
            time.sleep(2)
        
        print("Failed to start Ollama after multiple attempts")
        return False
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def check_mongodb():
    """Check if MongoDB is running"""
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()  # Will throw exception if not connected
        return True
    except:
        return False

def start_mongodb():
    """Start MongoDB service"""
    print("Starting MongoDB service...")
    try:
        # For macOS using brew
        subprocess.run(["brew", "services", "start", "mongodb-community"], check=True)
        
        # Wait for MongoDB to start
        max_attempts = 5
        for attempt in range(max_attempts):
            print(f"Waiting for MongoDB to start... ({attempt+1}/{max_attempts})")
            if check_mongodb():
                print("MongoDB started successfully!")
                return True
            time.sleep(2)
        
        print("Failed to start MongoDB after multiple attempts")
        return False
    except Exception as e:
        print(f"Error starting MongoDB: {e}")
        return False

def start_app():
    """Start the Streamlit app"""
    print("Starting ASHA application...")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Check if sample data exists
    if not has_sample_data():
        print("\nNo sample sessions found. Adding sample data...")
        try:
            from add_sample_sessions import create_sample_sessions
            create_sample_sessions()
        except Exception as e:
            print(f"Error adding sample data: {e}")
    
    # Start Streamlit
    streamlit_cmd = [
        "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false"
    ]
    
    try:
        subprocess.run(streamlit_cmd)
    except KeyboardInterrupt:
        print("\nShutting down ASHA application...")

def has_sample_data():
    """Check if the database has sample data"""
    try:
        from pymongo import MongoClient
        import config
        client = MongoClient(config.MONGO_URI)
        db = client[config.MONGO_DB]
        sessions_collection = db[config.MONGO_SESSIONS_COLLECTION]
        return sessions_collection.count_documents({}) > 0
    except:
        return False

if __name__ == "__main__":
    # Check and start required services
    services_ok = True
    
    if not check_ollama():
        if not start_ollama():
            services_ok = False
            print("WARNING: Ollama service not available. ASHA will use simplified responses.")
    
    if not check_mongodb():
        if not start_mongodb():
            services_ok = False
            print("WARNING: MongoDB service not available. Some features may not work properly.")
    
    # Start the app
    if services_ok:
        print("All services are running. Starting ASHA with full functionality.")
    else:
        print("Starting ASHA with limited functionality.")
    
    start_app()