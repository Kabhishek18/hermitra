# asha/utils/mcp_integration.py
import logging
import sys
import os
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import enhanced components
from utils.enhanced_vector_store import enhanced_vector_store
from utils.mcp_handler import mcp_session_manager
from utils.improved_nlp_search import ImprovedNLPSearch
from engines.enhanced_career_guidance import enhanced_career_guidance_engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_integration")

class MCPIntegration:
    """
    Integration class for Model Context Protocol components
    
    This class provides a unified interface for integrating MCP functionality
    into the existing ASHA chatbot system, enabling:
    
    1. Enhanced session search directly in chat conversations
    2. Context-aware session references and follow-ups
    3. Proactive session recommendations based on career discussions
    """
    
    def __init__(self):
        """Initialize MCP integration components"""
        # Verify all components are initialized
        self._check_components()
        logger.info("MCP Integration initialized successfully")
        
    def _check_components(self):
        """Verify all required components are initialized"""
        # Check vector store
        if not hasattr(enhanced_vector_store, 'index') or enhanced_vector_store.index is None:
            logger.warning("Enhanced vector store is not initialized")
            
        # Check NLP search
        if not hasattr(ImprovedNLPSearch, 'sessions'):
            logger.warning("Improved NLP search is not initialized")
            
        # Check session manager
        if not hasattr(mcp_session_manager, 'session_context'):
            logger.warning("MCP session manager is not initialized")
            
        # Check guidance engine
        if not hasattr(enhanced_career_guidance_engine, 'conversation_history'):
            logger.warning("Enhanced career guidance engine is not initialized")
            
    def process_query(self, query: str, user_id: str = "default_user") -> str:
        """
        Process a user query using the enhanced components
        
        Args:
            query: The user query text
            user_id: User identifier for context tracking
            
        Returns:
            Formatted response text
        """
        return enhanced_career_guidance_engine.process_query(query, user_id)
        
    def is_session_query(self, query: str) -> bool:
        """
        Determine if a query is related to session search
        
        Args:
            query: The user query text
            
        Returns:
            True if the query is a session search, False otherwise
        """
        return ImprovedNLPSearch.is_search_query(query)
        
    def get_session_context(self, user_id: str, max_sessions: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent sessions from user context
        
        Args:
            user_id: User identifier
            max_sessions: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries
        """
        return mcp_session_manager.get_session_context(user_id, max_sessions)
        
    def get_debug_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get debug information about the user's context
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with debug information
        """
        return {
            "session_context": mcp_session_manager.get_context_serializable(user_id),
            "vector_store_status": {
                "initialized": hasattr(enhanced_vector_store, 'index') and enhanced_vector_store.index is not None,
                "items_count": len(enhanced_vector_store.items) if hasattr(enhanced_vector_store, 'items') else 0
            },
            "nlp_search_status": {
                "initialized": hasattr(ImprovedNLPSearch, 'sessions'),
                "sessions_count": len(ImprovedNLPSearch.sessions) if hasattr(ImprovedNLPSearch, 'sessions') else 0
            },
            "guidance_engine_status": {
                "initialized": hasattr(enhanced_career_guidance_engine, 'conversation_history'),
                "history_length": len(enhanced_career_guidance_engine.conversation_history) if hasattr(enhanced_career_guidance_engine, 'conversation_history') else 0
            }
        }
    
    def update_existing_career_engine(self, existing_engine):
        """
        Patch an existing career engine instance with MCP capabilities
        
        Args:
            existing_engine: The existing career guidance engine instance
            
        Returns:
            The updated engine instance
        """
        # Add MCP session manager capabilities
        existing_engine.is_followup_query = mcp_session_manager.is_followup_query
        existing_engine.handle_followup_query = mcp_session_manager.handle_followup_query
        
        # Add improved NLP search capabilities
        existing_engine.is_search_query = ImprovedNLPSearch.is_search_query
        existing_engine.search_sessions = ImprovedNLPSearch.search_sessions
        existing_engine.extract_search_params = ImprovedNLPSearch.extract_search_params
        
        # Replace process_query method with the enhanced version
        existing_engine.original_process_query = existing_engine.process_query
        existing_engine.process_query = lambda query, user_id="default_user": self._wrapped_process_query(existing_engine, query, user_id)
        
        # Add proactive session recommendation function
        existing_engine.get_proactive_session_recommendations = enhanced_career_guidance_engine.get_proactive_session_recommendations
        
        logger.info("Successfully updated existing career engine with MCP capabilities")
        return existing_engine
    
    def _wrapped_process_query(self, engine, query: str, user_id: str = "default_user") -> str:
        """
        Wrapped process_query method that adds MCP capabilities to existing engine
        
        Args:
            engine: The original engine instance
            query: The user query
            user_id: User identifier for context tracking
            
        Returns:
            Formatted response text
        """
        # Check if this is a follow-up question about sessions
        if mcp_session_manager.is_followup_query(user_id, query):
            logger.info("Handling as session follow-up")
            response = mcp_session_manager.handle_followup_query(user_id, query)
            if response:
                # Add to engine's conversation history
                if hasattr(engine, 'conversation_history'):
                    engine.conversation_history.append({"role": "user", "content": query})
                    engine.conversation_history.append({"role": "assistant", "content": response})
                return response
        
        # Check if this is a session search query
        if ImprovedNLPSearch.is_search_query(query):
            logger.info("Processing as session search")
            response = ImprovedNLPSearch.process_query(query, user_id)
            # Add to engine's conversation history
            if hasattr(engine, 'conversation_history'):
                engine.conversation_history.append({"role": "user", "content": query})
                engine.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # Otherwise use the original process_query method
        response = engine.original_process_query(query)
        
        # Check if we should add proactive session recommendations
        if not ImprovedNLPSearch.is_search_query(query):
            recommendations = enhanced_career_guidance_engine.get_proactive_session_recommendations(query, user_id)
            if recommendations:
                response += recommendations
                # Update the last response in conversation history if it exists
                if hasattr(engine, 'conversation_history') and engine.conversation_history:
                    for i in range(len(engine.conversation_history) - 1, -1, -1):
                        if engine.conversation_history[i]['role'] == 'assistant':
                            engine.conversation_history[i]['content'] = response
                            break
        
        return response
        
    def initialize_for_app(self):
        """Initialize MCP integration for use in the app"""
        # Start by logging initialization
        logger.info("Initializing MCP integration for app use")
        
        # Perform any necessary initialization tasks
        # 1. Ensure vector store is initialized
        if not hasattr(enhanced_vector_store, 'index') or enhanced_vector_store.index is None:
            logger.info("Vector store not initialized, starting initialization...")
            # This will trigger initialization if needed
            ImprovedNLPSearch._initialize_vector_store()
        
        # 2. Pre-cache common patterns
        logger.info("Pre-caching common search patterns")
        test_queries = [
            "leadership sessions",
            "find negotiation sessions",
            "sessions about career transitions",
            "show me upcoming sessions"
        ]
        
        for query in test_queries:
            ImprovedNLPSearch.extract_search_params(query)
            
        logger.info("MCP integration initialization complete")
        
        return {
            "status": "success",
            "vector_store_items": len(enhanced_vector_store.items) if hasattr(enhanced_vector_store, 'items') else 0,
            "sessions_count": len(ImprovedNLPSearch.sessions) if hasattr(ImprovedNLPSearch, 'sessions') else 0
        }

# Create global MCP integration instance
mcp_integration = MCPIntegration()