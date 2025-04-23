#!/bin/bash

echo "===== ASHA BOT Setup Process ====="

# Create necessary directories
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/training
mkdir -p streamlit_app/logs

# Make scripts executable
chmod +x prepare_herkey_data.py
chmod +x generate_examples.py
chmod +x train.sh
chmod +x test_asha.py
chmod +x asha_api.py
chmod +x streamlit_app/start_streamlit.sh
chmod +x streamlit_app/start_custom.sh
chmod +x streamlit_app/start_enhanced.sh

echo "Setup complete! You can now run:"
echo "1. ./prepare_herkey_data.py - to process raw Herkey session data"
echo "2. ./train.sh - to generate examples and train the model"
echo "3. ./streamlit_app/start_enhanced.sh - to launch the web interface"