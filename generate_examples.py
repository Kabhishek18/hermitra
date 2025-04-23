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

def parse_session_data(json_file):
    """Extract useful information from the session JSON."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
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
        
        return session_info
    
    except Exception as e:
        print(f"Error parsing session data: {e}")
        return {"session_title": "Online vs in-person group discussion", 
                "description": "Pros and cons of online and in-person group discussions",
                "host": [{"username": "Udhaya C", "headline": "A Passionate Engineer"}],
                "category_tags": ["career development", "networking", "professional growth"]}

def generate_training_examples(session_info):
    """Create training examples from session data."""
    examples = []
    
    # Get session details
    title = session_info.get("session_title", "")
    description = session_info.get("description", "")
    hosts = [h.get("username", "") for h in session_info.get("host", [])]
    host_str = ", ".join(hosts) if hosts else "an expert host"
    
    # Shorten description if needed
    short_desc = description[:150] + "..." if len(description) > 150 else description
    
    # Example 1: Asking about the session
    examples.append({
        "Input": f"Tell me about the session titled '{title}'",
        "Response": f"The session '{title}' discusses {description}. It is hosted by {host_str}. This session would be valuable for women professionals looking to enhance their knowledge in this area. ASHA - Advancing careers, empowering professionals."
    })
    
    # Example 2: Recommending the session
    examples.append({
        "Input": "I'm looking for professional development sessions. Any recommendations?",
        "Response": f"Based on your interest in professional development, I recommend the session '{title}' hosted by {host_str}. This session covers {short_desc} It's designed to help women professionals advance their careers through practical insights. Would you like to know more about this session? ASHA - Advancing careers, empowering professionals."
    })
    
    # Example 3: Specific to online/in-person discussions
    if "online" in title.lower() or "in-person" in title.lower():
        examples.append({
            "Input": "What are the advantages of online sessions versus in-person ones?",
            "Response": f"Based on the session '{title}', online sessions offer flexibility, accessibility from anywhere, and often lower costs. However, in-person sessions typically provide better networking opportunities, stronger engagement, and non-verbal communication benefits. The best choice depends on your specific situation and learning preferences. Would you like me to elaborate on either format? ASHA - Advancing careers, empowering professionals."
        })
    
    # Example 4: Career guidance for women
    examples.append({
        "Input": "How can I improve my leadership skills as a woman in tech?",
        "Response": "To improve your leadership skills as a woman in tech, I recommend: 1) Join professional networks like Women in Tech or AnitaB.org, 2) Find a mentor who understands the challenges women face in tech leadership, 3) Participate in sessions like leadership workshops specifically designed for women in tech, 4) Practice assertive communication techniques, and 5) Seek projects that showcase your leadership abilities. Would you like specific resources on any of these strategies? ASHA - Advancing careers, empowering professionals."
    })
    
    # Example 5: Handling off-topic requests
    examples.append({
        "Input": "Can you help me find a restaurant nearby?",
        "Response": "I'm designed to focus on career guidance and professional development for women. While I can't help with restaurant recommendations, I'd be happy to assist you with finding career resources, professional development sessions like '{title}', or discussing strategies for workplace advancement. Is there a professional development topic I can help you with? ASHA - Advancing careers, empowering professionals."
    })
    
    # Example 6: Adding more general career guidance
    examples.append({
        "Input": "What's the best way to negotiate a salary increase?",
        "Response": "When negotiating a salary increase, I recommend these strategies: 1) Research industry standards for your role and experience level, 2) Document your achievements and contributions, 3) Practice your negotiation pitch, emphasizing the value you bring, 4) Consider the entire compensation package, not just salary, and 5) Approach the conversation with confidence but remain collaborative. Would you like more specific guidance on any of these points? ASHA - Advancing careers, empowering professionals."
    })
    
    return examples

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
    
    # Parse the session data
    session_info = parse_session_data("data/raw/sessions.json")
    
    # Save processed session info
    with open("data/processed/session_info.json", "w") as f:
        json.dump(session_info, f, indent=2)
    
    print(f"Successfully processed session: {session_info['session_title']}")
    
    # Generate session-specific examples
    session_examples = generate_training_examples(session_info)
    
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