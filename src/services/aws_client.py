import boto3
import json
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

load_dotenv()

class AWSBedrockClient:
    def __init__(self, options=None):
        options = options or {}
        self.region = options.get('region', os.getenv('AWS_BEDROCK_REGION'))
        self.access_key_id = options.get('access_key_id', os.getenv('AWS_BEDROCK_ACCESS_KEY_ID'))
        self.secret_access_key = options.get('secret_access_key', os.getenv('AWS_BEDROCK_SECRET_ACCESS_KEY'))
        self.model_id = options.get('model_id', os.getenv('TITAN_MODEL_ID'))
        
        # Initialize AWS client
        self.bedrock = boto3.client(
            service_name=os.getenv('AWS_BEDROCK_SERVICE_NAME', 'bedrock-runtime'),
            region_name=self.region,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        )
    
    def create_embedding(self, text):
        try:
            body = json.dumps({
                "inputText": text
            })
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                contentType='application/json',
                accept='application/json',
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            # Return a dummy embedding in case of error to avoid crashing
            return [0.0] * 1536  # Standard size for embeddings