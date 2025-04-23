#!/usr/bin/env python3
import subprocess
import sys

# Test queries
test_queries = [
    "Tell me about the session 'Online vs in-person group discussion'",
    "I'm looking for professional development sessions",
    "How can I improve my leadership skills as a woman in tech?",
    "What are some effective networking strategies?",
    "Can you help me find a restaurant nearby?"  # Off-topic test
]

for i, query in enumerate(test_queries):
    print(f"\n--- Test {i+1}: {query} ---\n")
    result = subprocess.run(
        ["ollama", "run", "asha-bot", query],
        capture_output=True,
        text=True
    )
    print(result.stdout)
