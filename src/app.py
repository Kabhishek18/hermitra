import streamlit as st
import os
import uuid
from pymongo import MongoClient
from datetime import datetime
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('asha_bot')

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="ASHA - Career Guidance for Women",
    page_icon="👩‍💼",
    layout="wide"
)

# Initialize session state variables
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'db' not in st.session_state:
    st.session_state.db = None
if 'ollama_client' not in st.session_state:
    st.session_state.ollama_client = None
if 'aws_client' not in st.session_state:
    st.session_state.aws_client = None
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = None
if 'intent_classifier' not in st.session_state:
    st.session_state.intent_classifier = None
if 'context_retriever' not in st.session_state:
    st.session_state.context_retriever = None
if 'response_generator' not in st.session_state:
    st.session_state.response_generator = None
if 'services_initialized' not in st.session_state:
    st.session_state.services_initialized = False

# Streamlit UI
st.title("ASHA - Career Guidance Assistant for Women")

# Import service classes with error handling
try:
    from services.ollama_client import OllamaClient
    from services.aws_client import AWSBedrockClient
    from services.session_manager import SessionManager
    from services.intent_classifier import IntentClassifier
    from services.context_retriever import ContextRetriever
    from services.response_generator import ResponseGenerator
    
    # Initialize MongoDB client (don't use cache_resource for this)
    def init_mongodb():
        try:
            client = MongoClient(os.getenv('MONGODB_URI'))
            return client[os.getenv('MONGODB_DB_NAME')]
        except Exception as e:
            st.error(f"Failed to connect to MongoDB: {str(e)}")
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return None

    # Initialize service clients (don't use cache_resource for these)
    def init_service_clients():
        try:
            ollama_client = OllamaClient()
            aws_client = AWSBedrockClient()
            return ollama_client, aws_client
        except Exception as e:
            st.error(f"Failed to initialize clients: {str(e)}")
            logger.error(f"Failed to initialize clients: {str(e)}")
            return None, None

    # Initialize services
    def init_services(db, ollama_client, aws_client):
        try:
            session_manager = SessionManager()
            intent_classifier = IntentClassifier(ollama_client)
            context_retriever = ContextRetriever(db, aws_client)
            response_generator = ResponseGenerator(ollama_client)
            return session_manager, intent_classifier, context_retriever, response_generator
        except Exception as e:
            st.error(f"Failed to initialize services: {str(e)}")
            logger.error(f"Failed to initialize services: {str(e)}")
            return None, None, None, None

    # Initialize all services if not already initialized
    if not st.session_state.services_initialized:
        # Initialize MongoDB
        st.session_state.db = init_mongodb()
        
        # Initialize clients
        st.session_state.ollama_client, st.session_state.aws_client = init_service_clients()
        
        if (st.session_state.db is not None and 
            st.session_state.ollama_client is not None and 
            st.session_state.aws_client is not None):
            
            # Initialize services
            (st.session_state.session_manager, 
             st.session_state.intent_classifier, 
             st.session_state.context_retriever, 
             st.session_state.response_generator) = init_services(
                st.session_state.db, 
                st.session_state.ollama_client, 
                st.session_state.aws_client
            )
            
            if (st.session_state.session_manager is not None and 
                st.session_state.intent_classifier is not None and 
                st.session_state.context_retriever is not None and 
                st.session_state.response_generator is not None):
                
                st.session_state.services_initialized = True
                logger.info("All services initialized successfully")
except Exception as e:
    st.error(f"Error during initialization: {str(e)}")
    logger.error(f"Error during initialization: {str(e)}")

# Process user query
def process_user_query(user_id, query):
    if not st.session_state.services_initialized:
        return "I'm sorry, I'm having trouble accessing my services right now. Please try again later."
    
    try:
        # Get user session
        user_session = st.session_state.session_manager.get_user_session(user_id)
        
        # Classify intent
        intent_classification = st.session_state.intent_classifier.classify_intent(query)
        
        if not intent_classification['is_safe_query']:
            safety_response = "I'm sorry, but I can't respond to that kind of request. I'm designed to provide career guidance for women professionals. How can I help you with your career today?"
            
            st.session_state.session_manager.update_user_session(user_id, query, safety_response)
            return safety_response
        
        if intent_classification['is_career_related']:
            # Retrieve relevant context
            relevant_context = st.session_state.context_retriever.retrieve_context(query, user_id)
            
            # Assemble context for LLM
            prompt_context = st.session_state.context_retriever.assemble_context(
                user_session, 
                relevant_context, 
                query
            )
            
            # Generate response
            response = st.session_state.response_generator.generate_response(prompt_context, {
                'use_advanced_model': intent_classification['intent'] == 'career_guidance'
            })
        else:
            # Handle non-career related query
            response = "I'm here to help with your career development. Could you share more about your professional goals or challenges you're facing in your career?"
        
        # Update user session with the conversation
        conversation = st.session_state.session_manager.update_user_session(user_id, query, response)
        
        # Generate and store embedding for this conversation
        try:
            embedding_text = f"Query: {query}\nResponse: {response}"
            embedding = st.session_state.aws_client.create_embedding(embedding_text)
            st.session_state.context_retriever.store_embedding(user_id, embedding_text, embedding)
        except Exception as e:
            logger.error(f"Error storing embedding: {str(e)}")
            # Continue even if embedding storage fails
        
        return response
    except Exception as e:
        logger.error(f"Error processing query for user {user_id}: {str(e)}")
        return "I'm sorry, I encountered an issue processing your request. Let's try a different approach."

# Sidebar with user preferences
st.sidebar.header("Your Career Profile")

# Career interests multiselect
career_interests = st.sidebar.multiselect(
    "Career Interests",
    ["Technology", "Leadership", "Healthcare", "Finance", "Education", 
     "Design", "Marketing", "Entrepreneurship", "Research", "Non-profit"],
    help="Select areas that interest you professionally"
)

# Experience level select
experience_level = st.sidebar.selectbox(
    "Experience Level",
    ["Entry Level", "Mid-Career", "Senior", "Executive", "Transitioning"],
    help="Select your current experience level"
)

# Industry select
industry = st.sidebar.selectbox(
    "Industry",
    ["Technology", "Healthcare", "Finance", "Education", "Retail", 
     "Manufacturing", "Media", "Government", "Non-profit", "Other"],
    help="Select your current or target industry"
)

# Save preferences button
if st.sidebar.button("Save Preferences"):
    if st.session_state.services_initialized:
        preferences = {
            "career_interests": career_interests,
            "experience_level": experience_level,
            "industry": industry
        }
        
        try:
            st.session_state.session_manager.update_user_preferences(st.session_state.user_id, preferences)
            st.sidebar.success("Preferences saved!")
        except Exception as e:
            st.sidebar.error(f"Error saving preferences: {str(e)}")
    else:
        st.sidebar.error("Services not initialized. Cannot save preferences.")

# Display chat messages
st.subheader("Chat with ASHA")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User input
user_query = st.chat_input("Type your career question here...")

if user_query:
    # Display user message
    with st.chat_message("user"):
        st.write(user_query)
    
    # Add to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    
    # Get ASHA's response
    with st.chat_message("assistant"):
        with st.spinner("ASHA is thinking..."):
            asha_response = process_user_query(st.session_state.user_id, user_query)
            st.write(asha_response)
    
    # Add to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": asha_response})

# Add some information about ASHA at the bottom
with st.expander("About ASHA"):
    st.markdown("""
    **ASHA** is a specialized career guidance assistant for women professionals. ASHA provides:
    
    * Tailored career guidance based on your background and goals
    * Advice on workplace challenges specific to women
    * Skill development recommendations
    * Interview preparation assistance
    * Job search strategies
    
    ASHA uses AI to provide personalized guidance while maintaining privacy and ethical standards.
    """)