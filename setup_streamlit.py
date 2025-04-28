"""
Setup script to create Streamlit configuration directory and file
to prevent PyTorch conflicts with Streamlit's file watcher
"""

import os
import sys

def setup_streamlit_config():
    """
    Create .streamlit directory and config.toml file
    to prevent PyTorch conflicts with file watching
    """
    # Create .streamlit directory if it doesn't exist
    if not os.path.exists(".streamlit"):
        os.makedirs(".streamlit")
        print("Created .streamlit directory")
    
    # Create config.toml file with settings to fix PyTorch conflict
    config_path = os.path.join(".streamlit", "config.toml")
    config_content = """[server]
enableStaticServing = true
enableCORS = false

[runner]
# Disable file watching for torch to prevent segmentation fault
moduleExcludedFromWatching = ["torch"]
"""
    
    with open(config_path, "w") as f:
        f.write(config_content)
    
    print(f"Created {config_path} with PyTorch compatibility settings")
    print("This should prevent the segmentation fault when running Streamlit with PyTorch")

if __name__ == "__main__":
    setup_streamlit_config()
    print("\nSetup complete. You can now run the application with:")
    print("python run.py")