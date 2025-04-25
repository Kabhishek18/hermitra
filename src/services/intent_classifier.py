import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

class IntentClassifier:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.career_intents = [
            'career_guidance', 'job_search', 'skill_development',
            'interview_preparation', 'workplace_challenges'
        ]
    
    def classify_intent(self, query):
        try:
            classification_result = self.ollama_client.classify(query, {
                'classification_categories': [
                    'career_guidance', 'job_search', 'skill_development',
                    'interview_preparation', 'workplace_challenges',
                    'off_topic', 'inappropriate'
                ]
            })
            
            intent = classification_result['category']
            
            return {
                'intent': intent,
                'is_career_related': intent in self.career_intents,
                'is_safe_query': intent != 'inappropriate',
                'confidence': classification_result.get('confidence', 1.0)
            }
        except Exception as e:
            logger.error(f"Intent classification error: {str(e)}")
            # Default to safe, career-related intent in case of error
            return {
                'intent': 'general',
                'is_career_related': True,
                'is_safe_query': True,
                'error': str(e)
            }