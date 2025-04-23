#!/bin/bash

echo "===== ASHA BOT Training Process ====="

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
  echo "Error: Ollama is not running. Please start Ollama first."
  exit 1
fi

# Process session data if needed
if [ ! -f data/sessions.json ]; then
  echo "Processing raw session data..."
  if [ -f data/raw/herkey.sessions.json ]; then
    echo "Using existing data/raw/herkey.sessions.json file"
    ./prepare_herkey_data.py data/raw/herkey.sessions.json
  else
    echo "Looking for paste.txt file..."
    ./prepare_herkey_data.py
  fi
  
  if [ ! -f data/sessions.json ]; then
    echo "Error: Failed to process session data. Check your input files."
    exit 1
  fi
fi

# Run the example generation script if it hasn't been run yet
if [ ! -f data/training/examples.jsonl ]; then
  echo "Generating training examples..."
  ./generate_examples.py
  
  if [ ! -f data/training/examples.jsonl ]; then
    echo "Error: Failed to generate training examples."
    exit 1
  fi
fi

# Count training examples
NUM_EXAMPLES=$(wc -l < data/training/examples.jsonl)
echo "Using $NUM_EXAMPLES training examples"

# Create the model in Ollama
echo "Creating ASHA BOT model in Ollama..."
ollama create asha-bot -f model/Modelfile

# Train the model
echo "Fine-tuning ASHA BOT model..."
ollama train asha-bot --modelfile model/Modelfile --data data/training/examples.jsonl

echo "Training complete! You can now use your ASHA BOT with:"
echo "ollama run asha-bot"
echo ""
echo "To launch the web interface, run:"
echo "./streamlit_app/start_enhanced.sh"