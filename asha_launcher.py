"""
ASHA Launcher Script - Alternative solution for PyTorch/Streamlit conflicts
"""

import os
import sys
import subprocess
import time

def launch_asha():
    """
    Launch ASHA application with environment variables to prevent PyTorch-Streamlit conflicts
    """
    print("Starting ASHA - Career Guidance for Women Professionals")
    
    # Set environment variables to prevent PyTorch-Streamlit conflicts
    env = os.environ.copy()
    
    # Critical environment variables to prevent PyTorch segfault
    env["PYTHONPATH"] = os.getcwd()
    env["STREAMLIT_THEME"] = "light"
    
    # Disable PyTorch parallelism which can cause conflicts
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    
    # This prevents PyTorch from using too many resources
    env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"
    
    # Disable JIT compilation which can cause issues
    env["TORCH_JIT_DISABLE"] = "1"
    
    # Launch ASHA application in subprocess with modified environment
    try:
        # Run MongoDB initialization first if needed
        if len(sys.argv) > 1 and sys.argv[1] == "--with-db":
            print("Initializing database...")
            subprocess.run([sys.executable, "initialize_db.py"], check=False, env=env)
        
        # Launch Streamlit in a separate process
        print("Launching ASHA application...")
        streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "asha_app.py"],
            env=env
        )
        
        # Open browser after a short delay
        time.sleep(3)
        
        # Keep the script running while Streamlit is running
        print("ASHA application is running at http://localhost:8501")
        print("Press Ctrl+C to stop the application")
        
        try:
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\nShutting down ASHA application...")
            streamlit_process.terminate()
            streamlit_process.wait()
            print("ASHA application has been stopped")
            
    except Exception as e:
        print(f"Error launching ASHA application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(launch_asha())