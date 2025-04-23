#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime

def extract_text_from_description(desc_json_str):
    """Extract text content from the nested description JSON structure."""
    try:
        desc_json = json.loads(desc_json_str)
    except (json.JSONDecodeError, TypeError):
        # If it's not valid JSON or not a string, return as is
        return str(desc_json_str)
    
    extracted_text = []
    
    def extract_text_recursive(node):
        if isinstance(node, dict):
            # Found a text node
            if "type" in node and node["type"] == "text" and "text" in node:
                extracted_text.append(node["text"])
            
            # Process children
            if "children" in node and isinstance(node["children"], list):
                for child in node["children"]:
                    extract_text_recursive(child)
        
        elif isinstance(node, list):
            for item in node:
                extract_text_recursive(item)
    
    # Start extraction from the root
    if "root" in desc_json:
        extract_text_recursive(desc_json["root"])
    
    return " ".join(extracted_text).strip()

def safe_parse_date(date_value):
    """Safely parse a date value that could be in various formats."""
    if isinstance(date_value, dict):
        if "$date" in date_value:
            date_str = date_value["$date"]
            if isinstance(date_str, str):
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass
    elif isinstance(date_value, str):
        try:
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    
    return "2025-04-23"  # Default date

def process_herkey_file(file_path):
    """Process a Herkey sessions file into structured data for training."""
    print(f"Processing file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Check if the file contains multiple JSON objects
    if content.strip().startswith('['):
        # It's already a JSON array
        try:
            raw_sessions = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON array: {e}")
            return []
    else:
        # Try to parse as multiple JSON objects separated by commas
        # Add square brackets to make it a valid JSON array
        try:
            # Check if it might be a series of JSON objects
            if content.strip().startswith('{') and '},\n{' in content:
                modified_content = '[' + content + ']'
                raw_sessions = json.loads(modified_content)
            else:
                # Single JSON object
                raw_sessions = [json.loads(content)]
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON content: {e}")
            print("Trying to clean up the content...")
            
            # Try to extract individual JSON objects
            sessions_content = []
            pattern = r'({.*?})'
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        obj = json.loads(match)
                        sessions_content.append(obj)
                    except json.JSONDecodeError:
                        continue
                
                if sessions_content:
                    print(f"Successfully extracted {len(sessions_content)} session objects")
                    raw_sessions = sessions_content
                else:
                    print("Failed to extract valid JSON objects")
                    return []
            else:
                print("No valid JSON objects found")
                return []
    
    # Process each session
    processed_sessions = []
    
    for session in raw_sessions:
        if not isinstance(session, dict):
            print(f"Skipping non-dictionary item: {type(session)}")
            continue
            
        if "_id" not in session and "session_id" not in session:
            # Skip invalid entries
            print("Skipping entry without _id or session_id")
            continue
        
        try:
            # Extract basic session info
            session_id = session.get("session_id", str(session.get("_id", {}).get("$oid", "")))
            title = session.get("session_title", "Untitled Session")
            
            # Extract description
            desc_raw = session.get("description", "{}")
            description = extract_text_from_description(desc_raw)
            
            # If description is empty or very short, use a default
            if len(description) < 10:
                description = f"Professional development session: {title}"
            
            # Extract host information
            hosts = []
            host_users = session.get("host_user", [])
            for host in host_users:
                username = host.get("username", "")
                headline = ""
                if "headlines" in host and isinstance(host["headlines"], dict):
                    headline = host["headlines"].get("headline1", "")
                elif "headline1" in host:
                    headline = host.get("headline1", "")
                
                if username:
                    hosts.append({
                        "username": username,
                        "headline": headline
                    })
            
            # Extract schedule information safely
            schedule = session.get("schedule", {})
            
            # Parse date safely
            date_str = "2025-04-23"  # Default date
            if isinstance(schedule, dict):
                if "start_time" in schedule:
                    date_str = safe_parse_date(schedule["start_time"])
            
            # Extract duration safely
            duration_min = 60  # Default duration
            if isinstance(schedule, dict):
                if "duration_minutes" in schedule:
                    duration_min = schedule["duration_minutes"]
                elif "duration" in session:
                    duration_str = session["duration"]
                    if isinstance(duration_str, str) and "hr" in duration_str:
                        try:
                            hours = float(duration_str.replace("hr", "").strip())
                            duration_min = int(hours * 60)
                        except (ValueError, TypeError):
                            pass
            
            duration = f"{duration_min} minutes"
            
            # Extract format
            session_format = "online"
            meta_data = session.get("meta_data", {})
            if isinstance(meta_data, dict) and "session_type" in meta_data:
                session_format = meta_data["session_type"]
            
            # Extract categories and tags
            categories = session.get("categories", [])
            tags = session.get("tags", [])
            
            # Combine into topics
            topics = []
            if isinstance(categories, list):
                topics.extend(categories)
            if isinstance(tags, list):
                topics.extend(tags)
                
            if not topics:
                topics = ["professional development", "career growth"]
            
            # Create processed session object
            processed_session = {
                "session_id": session_id,
                "title": title,
                "description": description,
                "host": hosts[0]["username"] if hosts else "Expert Host",
                "host_headline": hosts[0]["headline"] if hosts else "",
                "date": date_str,
                "duration": duration,
                "format": session_format,
                "topics": topics,
                "skill_level": "all levels"
            }
            
            processed_sessions.append(processed_session)
            
        except Exception as e:
            print(f"Error processing session: {e}")
            continue
    
    print(f"Processed {len(processed_sessions)} sessions")
    return processed_sessions

def main():
    # Create necessary directories
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # Input file - prioritize data/raw/herkey.sessions.json, fall back to paste.txt
    input_file = "data/raw/herkey.sessions.json"
    if not os.path.exists(input_file):
        input_file = "paste.txt"
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
        
    print(f"Using input file: {input_file}")
    
    # Process the file
    processed_sessions = process_herkey_file(input_file)
    
    if not processed_sessions:
        print("No sessions were processed. Check the input file format.")
        return
    
    # Save to data/raw/herkey.sessions.json if it's not already there
    if input_file != "data/raw/herkey.sessions.json":
        raw_output_path = "data/raw/herkey.sessions.json"
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_sessions, f, indent=2)
        print(f"Saved processed sessions to: {raw_output_path}")
    
    # Also save to data/sessions.json for direct use by the app
    app_output_path = "data/sessions.json"
    with open(app_output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_sessions, f, indent=2)
    print(f"Saved processed sessions to: {app_output_path}")
    
    print(f"\nProcessed {len(processed_sessions)} sessions successfully.")
    print("You can now run the training script to generate examples from these sessions.")

if __name__ == "__main__":
    main()