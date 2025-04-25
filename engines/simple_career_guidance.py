# asha/engines/simple_career_guidance.py

class SimpleCareerGuidanceEngine:
    """A simple, fast version of the career guidance engine for testing"""
    def __init__(self):
        self.conversation_history = []
        
    def process_query(self, query):
        """Process a user query with pre-defined responses for testing"""
        self.conversation_history.append({"role": "user", "content": query})
        
        # Simple pattern matching for quick responses
        query_lower = query.lower()
        
        if "name" in query_lower:
            response = "I am ASHA, your AI career guidance assistant. I'm here to help with your professional development."
        elif "hello" in query_lower or "hi" in query_lower:
            response = "Hello! I'm ASHA, your career guidance assistant. How can I help with your professional development today?"
        elif "interview" in query_lower:
            response = "For interview preparation, I recommend: 1) Research the company thoroughly, 2) Practice common questions, 3) Prepare examples of your achievements, and 4) Have questions ready to ask the interviewer."
        elif "salary" in query_lower or "negotiation" in query_lower:
            response = "When negotiating salary, research market rates for your role and location, highlight your specific value to the company, and practice your negotiation conversation beforehand. Consider the total compensation package, not just the base salary."
        elif "ai" in query_lower or "session" in query_lower:
            response = "AI career sessions often focus on skills like machine learning, data analysis, and programming languages such as Python. They may also cover AI ethics, emerging trends, and industry applications."
        else:
            response = "As your career guidance assistant, I'm here to help with professional development questions. Could you provide more details about your career goals or challenges you're facing?"
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response