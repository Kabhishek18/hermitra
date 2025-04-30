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
import concurrent.futures
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
headless = true

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[runner]
# Disable file watching for torch to prevent segmentation fault
moduleExcludedFromWatching = ["torch", "tensorflow", "transformers", "langchain", "deepface"]
fastReruns = true
magicEnabled = false

[theme]
primaryColor = "#FF1493"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[logger]
level = "warning"

[client]
toolbarMode = "minimal"
showErrorDetails = false

[global]
developmentMode = false
disableWatchdogWarning = true
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
                "--wiredTigerCacheSizeGB", "0.5",  # Limit cache to 500MB
                "--storageEngine", "wiredTiger",
                "--wiredTigerJournalCompressor", "snappy",
                "--syncdelay", "60",  # Reduce sync frequency to 60 seconds
                "--nojournal"  # Disable journaling for better performance
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for MongoDB to start
        for _ in range(5):  # Try for 5 seconds
            time.sleep(1)
            if check_mongodb():
                print("MongoDB started successfully")
                return True
        
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
        for _ in range(5):  # Try for 5 seconds
            time.sleep(1)
            if check_ollama():
                print("Ollama started successfully")
                return True
        
        print("Failed to start Ollama, using simulated responses")
        return False
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def initialize_database():
    """Initialize database collections and sample data"""
    try:
        print("Initializing database...")
        subprocess.run([sys.executable, "initialize_db.py"], check=False, timeout=30)
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def preload_dependencies():
    """Preload dependencies to speed up startup"""
    try:
        print("Preloading dependencies...")
        
        # Preload key modules
        def preload_module(module_name):
            try:
                __import__(module_name)
                return f"Preloaded {module_name}"
            except Exception as e:
                return f"Failed to preload {module_name}: {e}"
        
        modules = [
            "streamlit", "pymongo", "datetime", "numpy", "pandas", 
            "PIL", "requests", "json", "core", "performance_optimization"
        ]
        
        # Use concurrent loading to speed up the process
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(preload_module, module): module for module in modules}
            for future in concurrent.futures.as_completed(futures):
                module = futures[future]
                try:
                    result = future.result()
                    print(result)
                except Exception as e:
                    print(f"Error preloading {module}: {e}")
        
        # Create a lightweight initialization script to preload specific objects
        init_script = """
import sys
try:
    from core import AshaBot, SessionRecommender
    from optimized_chat import ChatManager
    print("Successfully preloaded core components")
except Exception as e:
    print(f"Error preloading core components: {e}")
    sys.exit(1)
sys.exit(0)
"""
        with open("preload_temp.py", "w") as f:
            f.write(init_script)
        
        # Run the script in a separate process
        subprocess.run([sys.executable, "preload_temp.py"], timeout=10)
        
        # Clean up
        if os.path.exists("preload_temp.py"):
            os.remove("preload_temp.py")
        
        return True
    except Exception as e:
        print(f"Error preloading dependencies: {e}")
        return False

def apply_ui_fixes():
    """Apply fixes to various components"""
    try:
        print("Applying UI fixes...")
        
        # Create a patched version of enhanced_login_form
        login_form_patch = """
import streamlit as st
import base64
from core import verify_password, generate_session_token, check_memory, optimize_memory, ObjectId

def enhanced_login_form(db):
    '''Display enhanced login form with better UI'''
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("Login to ASHA")
        
        with st.form(key="login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            # Avoid nested columns inside form - use a simple layout instead
            st.markdown('<div style="display: flex; gap: 10px;">', unsafe_allow_html=True)
            
            # Add explicit form submit buttons
            forgot_password_btn = st.form_submit_button("Forgot Password?")
            
            st.markdown('<div style="flex-grow: 1;">', unsafe_allow_html=True)
            login_btn = st.form_submit_button("Sign In")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle form submission
        if login_btn:
            # Check memory usage
            check_memory()
                
            if not email or not password:
                st.error("Please enter both email and password.")
                return
            
            if db is not None:
                try:
                    user = db.users.find_one({"email": email})
                    if not user:
                        st.error("User not found.")
                        return
                    
                    # Convert binary data to bytes if necessary
                    stored_password = user["password"]
                    if isinstance(stored_password, dict) and '$binary' in stored_password:
                        stored_password = base64.b64decode(stored_password['$binary']['base64'])
                    
                    if verify_password(stored_password, password):
                        # Success - set up session
                        st.success("Login successful!")
                        
                        # Store user information in session state
                        st.session_state.user = {
                            "id": str(user["_id"]),
                            "name": user["name"],
                            "email": user["email"],
                            "gender": user.get("self_identified_gender", "Unknown")
                        }
                        
                        # If AI verified gender is available
                        if "ai_verified_gender" in user:
                            st.session_state.user["ai_verified_gender"] = user["ai_verified_gender"]
                        
                        st.session_state.logged_in = True
                        st.session_state.show_login = False
                        
                        # Create token for session persistence
                        token = generate_session_token(str(user["_id"]))
                        st.session_state.token = token
                        
                        # Force a rerun to update the UI
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                except Exception as e:
                    st.error(f"Error during login: {e}")
                    optimize_memory()  # Clean up memory after error
                    
        if forgot_password_btn:
            st.info("Please contact support to reset your password.")
    
    with col2:
        st.image("https://img.icons8.com/color/240/null/login-rounded-right--v1.png", width=100)
    
    st.markdown('</div>', unsafe_allow_html=True)
"""

        # Create a chat interface fix for the nested columns error
        chat_interface_patch = """
import streamlit as st

def fixed_rename_dialog(current_thread, user_id, chat_manager):
    '''Fixed rename dialog to avoid nested columns'''
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h4>Rename Conversation</h4>", unsafe_allow_html=True)
    
    # Use a form without nested columns
    with st.form(key="rename_form"):
        new_title = st.text_input("New conversation title:", value=current_thread.title)
        # Single submit button with proper form handling
        submit_button = st.form_submit_button("Save Changes")
    
    # Handle form submission outside the form
    if submit_button:
        if chat_manager.rename_thread(current_thread.thread_id, user_id, new_title):
            st.session_state.show_rename = False
            st.success("Conversation renamed successfully.")
            st.rerun()
    
    # Add a cancel button outside the form
    if st.button("Cancel", key="rename_cancel"):
        st.session_state.show_rename = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
"""

        # Enhanced UI Styles to fix appearance
        enhanced_styles = """
import streamlit as st

def apply_enhanced_ui():
    '''Apply enhanced UI styles for ASHA application'''
    st.markdown('''
    <style>
    /* Modern color scheme */
    :root {
        --primary-color: #FF1493;
        --secondary-color: #9370DB;
        --accent-color: #00CED1;
        --background-color: #F8F9FA;
        --text-color: #212529;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --error-color: #dc3545;
        --info-color: #17a2b8;
        --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        --hover-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
    }
    
    /* Global styles */
    .main .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }
    
    body {
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        color: var(--text-color);
        background-color: var(--background-color);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        font-weight: 600;
    }
    
    /* Header styles */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 0.5rem 0;
    }
    
    .subheader {
        font-size: 1.2rem;
        color: var(--secondary-color);
        margin-bottom: 0.5rem;
        font-weight: 500;
        text-align: center;
    }
    
    /* Card component */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: var(--card-shadow);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    /* More compact layout */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
        margin: 0.1rem 0;
        padding: 0.3rem 0.8rem;
    }
    
    /* Improved sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
    }
    
    /* More compact chat container */
    .chat-container {
        max-height: 65vh;
        overflow-y: auto;
        padding: 0.8rem;
        background-color: #f9f9f9;
        border-radius: 10px;
        margin-bottom: 0.8rem;
    }
    
    /* More attractive messages */
    .user-message {
        background-color: #e3f2fd;
        padding: 10px 15px;
        border-radius: 18px 18px 18px 0;
        margin: 8px 0;
        max-width: 85%;
        align-self: flex-start;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        border-left: 3px solid #1976D2;
    }
    
    .assistant-message {
        background-color: #fce4ec;
        padding: 10px 15px;
        border-radius: 18px 18px 0 18px;
        margin: 8px 0 8px auto;
        max-width: 85%;
        align-self: flex-end;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        border-right: 3px solid #FF1493;
    }
    
    /* Optimize spacing */
    .stTextInput, .stTextArea {
        margin-bottom: 0.5rem;
    }
    
    /* Hide Streamlit watermark and hamburger menu */
    #MainMenu, footer, header {
        display: none !important;
    }
    
    /* Make error messages less intrusive */
    .stException, .stError, .stWarning {
        padding: 0.5rem !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Responsive layout for mobile */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
        .card {
            padding: 0.8rem;
        }
    }
    
    /* Fix for column nesting errors */
    div.row-widget.stRadio > div {
        flex-direction: row;
        align-items: center;
    }
    
    /* Fix Streamlit form issues */
    section[data-testid="stForm"] {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Clean up error display */
    div[data-baseweb="notification"] {
        margin: 0.5rem 0 !important;
    }
    </style>
    ''', unsafe_allow_html=True)
"""

        # Create patch files
        with open("login_form_patch.py", "w") as f:
            f.write(login_form_patch)
        
        with open("chat_interface_patch.py", "w") as f:
            f.write(chat_interface_patch)
        
        with open("enhanced_styles.py", "w") as f:
            f.write(enhanced_styles)
        
        print("UI fix patches created successfully")
        return True
    except Exception as e:
        print(f"Error applying UI fixes: {e}")
        return False

def optimize_startup():
    """Additional optimizations for faster startup"""
    # Set environment variables for better performance
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"
    os.environ["OMP_NUM_THREADS"] = "1"  # Limit OpenMP threads
    os.environ["MKL_NUM_THREADS"] = "1"  # Limit MKL threads
    os.environ["OPENBLAS_NUM_THREADS"] = "1"  # Limit OpenBLAS threads
    os.environ["VECLIB_MAXIMUM_THREADS"] = "1"  # Limit VecLib threads
    os.environ["NUMEXPR_NUM_THREADS"] = "1"  # Limit NumExpr threads
    os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Disable HF tokenizers parallelism
    
    # Run garbage collection to clean up memory
    import gc
    gc.collect()
    
    print("Startup optimizations applied")
    return True

def start_streamlit():
    """Start Streamlit application with optimizations"""
    global streamlit_process
    
    try:
        print("Starting ASHA application...")
        
        # Set environment variables for better performance
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        env["STREAMLIT_THEME"] = "light"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:64"
        env["TORCH_JIT_DISABLE"] = "1"
        env["MALLOC_TRIM_THRESHOLD_"] = "65536"
        env["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings
        
        # Add our patches to PYTHONPATH
        patched_pythonpath = os.getcwd()
        env["PYTHONPATH"] = patched_pythonpath
        
        # Create a startup script that applies the patches
        startup_script = """
import os
import sys
import streamlit as st

# Apply UI patches first
try:
    # Apply login form patch
    import login_form_patch
    
    # Apply chat interface patch
    import chat_interface_patch
    
    # Apply enhanced styles
    import enhanced_styles
    
    print("Applied UI patches successfully")
except Exception as e:
    print(f"Error applying UI patches: {e}")

# Then run the main app
import asha_app
"""
        with open("run_patched_asha.py", "w") as f:
            f.write(startup_script)
        
        # Launch the patched Streamlit app
        streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", 
             "run_patched_asha.py", 
             "--server.maxUploadSize=20",
             "--server.maxMessageSize=50",
             "--server.enableCORS=false",
             "--server.enableXsrfProtection=false",
             "--server.enableWebsocketCompression=true",
             "--browser.gatherUsageStats=false",
             "--runner.fastReruns=true",
             "--runner.maxCachedMessageAge=60"],
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
    
    # Clean up patch files
    for file in ["login_form_patch.py", "chat_interface_patch.py", "enhanced_styles.py", "run_patched_asha.py"]:
        if os.path.exists(file):
            os.remove(file)
    
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
    parser.add_argument("--fast", action="store_true", help="Fast startup with minimal initialization")
    args = parser.parse_args()
    
    print("ASHA Career Guidance Chatbot Launcher")
    print("====================================")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Apply startup optimizations
    optimize_startup()
    
    # Initialize directories
    init_directories()
    
    # Setup Streamlit configuration
    setup_streamlit_config()
    
    # Apply UI fixes
    apply_ui_fixes()
    
    # Start MongoDB if needed
    if not args.skip_db and not args.fast:
        if not start_mongodb():
            print("Warning: MongoDB initialization failed. Continuing with limited functionality.")
    
    # Initialize database
    if not args.skip_db and not args.fast:
        initialize_database()
    
    # Start Ollama if needed
    if not args.skip_ollama and not args.fast:
        if not start_ollama():
            print("Warning: Ollama initialization failed. Chatbot will use fallback responses.")
    
    # Preload dependencies for faster startup
    if not args.fast:
        preload_dependencies()
    
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