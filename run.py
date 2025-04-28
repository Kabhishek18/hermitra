"""
ASHA application runner.
This script initializes the database and starts the ASHA application.
"""

import subprocess
import sys
import os
import time
import webbrowser
import importlib.util

# Import function from core if available
try:
    from core import check_mongodb_running
except ImportError:
    # Define the function here if import fails
    def check_mongodb_running():
        """Check if MongoDB is running"""
        try:
            import pymongo
            client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            return True
        except Exception:
            return False

def check_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        "streamlit", "pymongo", "pillow", "opencv-python", "numpy", 
        "pandas", "faiss-cpu", "langchain-community", "sentence-transformers", 
        "requests", "bson", "streamlit-option-menu", "watchdog"
    ]
    
    missing = []
    for package in required_packages:
        try:
            package_name = package.split('==')[0].split('>=')[0]
            importlib.util.find_spec(package_name.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        choice = input(f"Install missing packages? (y/n): ")
        if choice.lower() == 'y':
            for package in missing:
                print(f"Installing {package}...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    print(f"Successfully installed {package}")
                except Exception as e:
                    print(f"Failed to install {package}: {e}")

def main():
    """Main function to run the ASHA application"""
    print("Starting ASHA - Career Guidance for Women Professionals")
    
    # Check dependencies
    print("Checking dependencies...")
    check_dependencies()
    
    # Check MongoDB
    print("Checking MongoDB connection...")
    mongo_available = check_mongodb_running()
    if not mongo_available:
        print("MongoDB is not running. Please start MongoDB before running the application.")
        print("\nOn Windows: Start the MongoDB service or run 'mongod' in a separate terminal")
        print("On macOS/Linux: Run 'mongod --dbpath=/path/to/data/directory' in a separate terminal")
        
        retry = input("Would you like to continue without MongoDB? Features will be limited. (y/n): ")
        if retry.lower() != 'y':
            print("Exiting...")
            return False
    
    # Initialize database if MongoDB is available
    if mongo_available:
        print("\nInitializing database...")
        try:
            db_result = subprocess.run([sys.executable, "initialize_db.py"], check=False)
            if db_result.returncode != 0:
                print("Warning: Database initialization had issues, but we'll continue.")
        except Exception as e:
            print(f"Error initializing database: {e}")
            print("Continuing with limited functionality...")
    
    # Start Streamlit app
    print("\nStarting ASHA application...")
    try:
        # Open browser after a short delay
        def open_browser():
            time.sleep(3)
            webbrowser.open("http://localhost:8501")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Run Streamlit
        streamlit_process = subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "asha_app.py"], 
            check=True
        )
        return streamlit_process.returncode == 0
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
        return True
    except Exception as e:
        print(f"\nError running Streamlit application: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)