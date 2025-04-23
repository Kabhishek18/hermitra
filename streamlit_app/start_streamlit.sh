#!/bin/bash

echo "Starting ASHA BOT Streamlit Interface..."
echo "Make sure Ollama is running in another terminal window."
echo "Press Ctrl+C to stop the web interface."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
  echo "WARNING: Ollama doesn't seem to be running. Please start it first."
  echo "Continue anyway? (y/n)"
  read answer
  if [[ "$answer" != "y" ]]; then
    echo "Exiting."
    exit 1
  fi
fi

# Start the Streamlit app
streamlit run asha_streamlit.py
