# ASHA Chatbot Installation Guide

This guide will help you set up and run the ASHA career guidance chatbot for women professionals.

## Prerequisites

Ensure you have the following installed on your system:

1. Python 3.8 or newer
2. MongoDB
3. Ollama (optional, for enhanced AI capabilities)

## Installation Steps

### Step 1: Clone or download the ASHA chatbot project

Download the ASHA chatbot application files to your local machine.

### Step 2: Fix MongoDB Import Errors

The application initially had an issue with the MongoDB ObjectId import. This has been fixed in the updated files, which now use:

```python
from bson.objectid import ObjectId
```

instead of:

```python
from pymongo import ObjectId
```

### Step 3: Create a virtual environment (recommended)

```bash
# Create a virtual environment
python -m venv asha_env

# Activate the virtual environment
# On Windows:
asha_env\Scripts\activate
# On macOS/Linux:
source asha_env/bin/activate
```

### Step 4: Install dependencies

```bash
pip install -r requirements.txt
```

If you encounter any issues with the dependencies, you can install the core dependencies manually:

```bash
pip install streamlit pymongo pillow opencv-python numpy pandas faiss-cpu langchain-community sentence-transformers requests streamlit-option-menu watchdog
```

### Step 5: Start MongoDB

Ensure MongoDB is running on your system.

```bash
# On macOS/Linux, you can start MongoDB with:
mongod --dbpath=/path/to/data/directory

# On Windows, start the MongoDB service or use MongoDB Compass
```

### Step 6: Run the application

```bash
python run.py
```

The script will:
1. Check for dependencies and install any missing ones
2. Verify MongoDB connection
3. Initialize the database with sample sessions if needed
4. Start the Streamlit application
5. Open the application in your web browser

## Troubleshooting

### MongoDB Connection Issues

If you see an error like:
```
ImportError: cannot import name 'SON' from 'bson'
```
or
```
ModuleNotFoundError: No module named 'bson.objectid'
```

Try these steps:

1. Uninstall the standalone bson package:
```bash
pip uninstall bson
```

2. Reinstall pymongo:
```bash
pip install pymongo
```

### Other Issues

- **"No module named 'streamlit'"**: Run `pip install streamlit`
- **Ollama not found**: The application will fall back to a simulated response mode
- **Database errors**: The application can run with limited functionality without MongoDB

## Using ASHA

Once the application is running:

1. Create an account or log in
2. Complete your profile for personalized recommendations
3. Chat with ASHA for career guidance
4. Explore recommended professional development sessions

## Optional: Configure Ollama

For enhanced AI capabilities, install Ollama and the Mistral model:

```bash
# Install Ollama (visit https://ollama.ai for instructions)

# Pull the Mistral model
ollama pull mistral:latest
```

The ASHA chatbot will automatically detect and use Ollama if available.