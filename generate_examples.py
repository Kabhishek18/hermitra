#!/usr/bin/env python3
import json
import os
import re

def extract_text_from_description(desc_json):
    """Extract text content from the nested description JSON structure."""
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
    
    return " ".join(extracted_text)

def parse_sessions_data(json_file):
    """Extract useful information from multiple sessions in the JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Handle both array and object formats
        if isinstance(data, list):
            sessions_data = data
        else:
            # If it's paste.txt format with multiple sessions
            sessions_data = [data]
            # Check if there are more sessions after the first object
            for i in range(10):  # Look for up to 10 more sessions
                next_char = f.read(1)
                if next_char == ',':
                    session_data = json.loads(f.read())
                    sessions_data.append(session_data)
                else:
                    break
        
        processed_sessions = []
        
        for data in sessions_data:
            session_info = {
                "session_id": data.get("session_id", ""),
                "session_title": data.get("session_title", ""),
                "description": "",
                "host": [],
                "category_tags": []
            }
            
            # Extract description content
            desc = data.get("description", "{}")
            try:
                desc_json = json.loads(desc)
                extracted_text = extract_text_from_description(desc_json)
                if extracted_text:
                    session_info["description"] = extracted_text
            except json.JSONDecodeError:
                # If description isn't valid JSON, use it directly
                session_info["description"] = desc
            
            # Extract host info
            hosts = data.get("host_user", [])
            for host in hosts:
                host_info = {
                    "username": host.get("username", ""),
                    "headline": host.get("headlines", {}).get("headline1", "")
                }
                session_info["host"].append(host_info)
            
            # Extract categories and tags
            session_info["category_tags"].extend(data.get("categories", []))
            session_info["category_tags"].extend(data.get("tags", []))
            
            processed_sessions.append(session_info)
        
        return processed_sessions
    
    except Exception as e:
        print(f"Error parsing session data: {e}")
        return [{
            "session_title": "Online vs in-person group discussion", 
            "description": "Pros and cons of online and in-person group discussions",
            "host": [{"username": "Udhaya C", "headline": "A Passionate Engineer"}],
            "category_tags": ["career development", "networking", "professional growth"]
        }]

def generate_training_examples(sessions_info):
    """Create training examples from multiple session data."""
    all_examples = []
    
    for session_info in sessions_info:
        # Get session details
        title = session_info.get("session_title", "")
        description = session_info.get("description", "")
        hosts = [h.get("username", "") for h in session_info.get("host", [])]
        host_str = ", ".join(hosts) if hosts else "an expert host"
        
        # Shorten description if needed
        short_desc = description[:150] + "..." if len(description) > 150 else description
        
        # Example 1: Asking about the session
        all_examples.append({
            "Input": f"Tell me about the session titled '{title}'",
            "Response": f"The session '{title}' discusses {description}. It is hosted by {host_str}. This session would be valuable for women professionals looking to enhance their knowledge in this area. ASHA - Advancing careers, empowering professionals."
        })
        
        # Example 2: Recommending the session
        all_examples.append({
            "Input": f"I'm looking for sessions like {title}",
            "Response": f"Based on your interest, I recommend the session '{title}' hosted by {host_str}. This session covers {short_desc} It's designed to help women professionals advance their careers through practical insights. Would you like to know more about this session? ASHA - Advancing careers, empowering professionals."
        })
    
    return all_examples

def create_additional_examples():
    """Create additional career guidance examples not tied to specific sessions."""
    examples = [
        {
            "Input": "How do I handle gender bias in the workplace?",
            "Response": "To handle gender bias in the workplace: 1) Document instances of bias, 2) Build a support network of allies, 3) Address issues directly when appropriate using 'I' statements, 4) Know your company's policies and HR procedures, and 5) Focus on your performance and achievements. Remember that addressing bias is a systemic issue, not just an individual one. Would you like more specific strategies for your particular situation? ASHA - Advancing careers, empowering professionals."
        },
        {
            "Input": "What are some effective networking strategies for women?",
            "Response": "Effective networking strategies for women professionals include: 1) Join women-focused professional organizations in your field, 2) Attend both industry-wide and women-specific events, 3) Develop an elevator pitch that clearly communicates your expertise, 4) Follow up consistently after making connections, 5) Seek mentorship relationships, and 6) Consider starting your own networking group if you identify a gap. Quality connections often matter more than quantity. Would you like me to elaborate on any of these strategies? ASHA - Advancing careers, empowering professionals."
        },
        {
            "Input": "How can I improve my resume?",
            "Response": "To improve your resume: 1) Highlight achievements with measurable results rather than just listing responsibilities, 2) Customize it for each application by matching keywords from the job description, 3) Include relevant skills and certifications, 4) Keep the format clean and scannable with consistent formatting, 5) Start with a strong professional summary, and 6) Have it reviewed by a trusted colleague. Would you like specific guidance on any section of your resume? ASHA - Advancing careers, empowering professionals."
        },
        {
            "Input": "I feel stuck in my current job. What should I do?",
            "Response": "If you're feeling stuck in your current job, consider these steps: 1) Identify exactly what's causing the stagnation - is it lack of challenges, growth opportunities, or something else? 2) Have a conversation with your manager about your career goals, 3) Look for stretch assignments or cross-functional projects, 4) Invest in upskilling through courses or certifications, 5) Expand your network within and outside your organization, and 6) Consider if it's time for a change. Would you like to discuss any of these strategies in more detail? ASHA - Advancing careers, empowering professionals."
        }
    ]
    return examples

# Main execution
if __name__ == "__main__":
    print("Generating training examples for ASHA BOT...")
    
    os.makedirs("data/training", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # Parse the session data from the herkey.sessions.json file
    raw_file_path = "data/raw/herkey.sessions.json"
    if not os.path.exists(raw_file_path):
        # Fallback to paste.txt if herkey.sessions.json doesn't exist
        print(f"Warning: {raw_file_path} not found, trying paste.txt")
        raw_file_path = "paste.txt"
    
    sessions_info = parse_sessions_data(raw_file_path)
    
    # Save processed session info
    with open("data/processed/sessions_info.json", "w") as f:
        json.dump(sessions_info, f, indent=2)
    
    print(f"Successfully processed {len(sessions_info)} sessions")
    
    # Generate session-specific examples
    session_examples = generate_training_examples(sessions_info)
    
    # Generate additional examples
    additional_examples = create_additional_examples()
    
    # Combine all examples
    all_examples = session_examples + additional_examples
    
    # Write examples to file
    with open("data/training/examples.jsonl", "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")
    
    print(f"Generated {len(all_examples)} training examples")
    print(f"- {len(session_examples)} session-specific examples")
    print(f"- {len(additional_examples)} general career guidance examples")
    print("Examples saved to data/training/examples.jsonl")
    
    # Generate sessions.json file for the streamlit app
    streamlined_sessions = []
    for session in sessions_info:
        hosts = session.get("host", [])
        host_name = hosts[0].get("username", "Unknown Host") if hosts else "Unknown Host"
        host_headline = hosts[0].get("headline", "") if hosts else ""
        
        streamlined_session = {
            "session_id": session.get("session_id", ""),
            "title": session.get("session_title", ""),
            "description": session.get("description", ""),
            "host": host_name,
            "host_headline": host_headline,
            "date": "2025-04-23",  # Current date as placeholder
            "duration": "60 minutes",
            "format": "online",
            "topics": session.get("category_tags", ["professional development"]),
            "skill_level": "all levels"
        }
        streamlined_sessions.append(streamlined_session)
    
    with open("data/sessions.json", "w") as f:
        json.dump(streamlined_sessions, f, indent=2)
    
    print("Generated sessions.json for the streamlit app")