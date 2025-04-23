#!/bin/bash

echo "===== ASHA BOT Training Process ====="

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
  echo "Error: Ollama is not running. Please start Ollama first."
  exit 1
fi

# Run the example generation script if it hasn't been run yet
if [ ! -f data/training/examples.jsonl ]; then
  echo "Generating training examples..."
  ./generate_examples.py
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