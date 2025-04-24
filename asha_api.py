#!/usr/bin/env python3
import requests
import json

def ask_asha(question):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "asha-bot",
            "prompt": question,
            "stream": False
        }
    )
    if response.status_code == 200:
        return response.json()["response"]
    else:
        return f"Error: {response.status_code}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(ask_asha(question))
    else:
        print("Please provide a question as an argument.")
