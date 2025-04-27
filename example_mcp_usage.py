#!/usr/bin/env python3
# asha/example_mcp_usage.py
import sys
import os
import time
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import MCP integration
from utils.mcp_integration import mcp_integration

# Import original engine for comparison
from engines.career_guidance import CareerGuidanceEngine

def main():
    """Example script demonstrating MCP integration"""
    parser = argparse.ArgumentParser(description="ASHA MCP Example")
    parser.add_argument("--mode", choices=["enhanced", "compare", "upgrade"], default="enhanced", 
                       help="Run mode: enhanced (MCP only), compare (side by side), upgrade (patch original)")
    parser.add_argument("--user_id", default="example_user", help="User ID for context tracking")
    args = parser.parse_args()
    
    print("\n===== ASHA MCP Integration Example =====\n")
    
    # Initialize MCP for app use
    init_status = mcp_integration.initialize_for_app()
    print(f"Initialization status: {init_status}\n")
    
    # Example queries for demonstration
    sample_queries = [
        "I need advice on improving my leadership skills",
        "Find sessions about career transitions",
        "Who hosts leadership sessions?",
        "Tell me more about that first session",
        "How can I prepare for salary negotiations?",
        "Are there any sessions about networking?",
        "When is the leadership session scheduled?"
    ]
    
    # Run in selected mode
    if args.mode == "enhanced":
        # Use enhanced MCP components
        print("=== Using Enhanced MCP Engine ===\n")
        
        for i, query in enumerate(sample_queries):
            print(f"\n[Query {i+1}]: {query}")
            start_time = time.time()
            response = mcp_integration.process_query(query, args.user_id)
            end_time = time.time()
            print(f"\n[Response] ({end_time - start_time:.2f}s):")
            print(response)
            print("\n" + "-" * 50)
    
    elif args.mode == "compare":
        # Compare MCP with original engine
        print("=== Comparing Enhanced MCP vs. Original Engine ===\n")
        
        # Initialize original engine
        original_engine = CareerGuidanceEngine()
        
        for i, query in enumerate(sample_queries):
            print(f"\n[Query {i+1}]: {query}")
            
            # Run with original engine
            start_time = time.time()
            original_response = original_engine.process_query(query)
            original_time = time.time() - start_time
            
            # Run with MCP
            start_time = time.time()
            mcp_response = mcp_integration.process_query(query, args.user_id)
            mcp_time = time.time() - start_time
            
            # Print results
            print(f"\n[Original Engine] ({original_time:.2f}s):")
            print(original_response)
            
            print(f"\n[Enhanced MCP Engine] ({mcp_time:.2f}s):")
            print(mcp_response)
            
            print("\n" + "-" * 50)
    
    elif args.mode == "upgrade":
        # Upgrade original engine with MCP capabilities
        print("=== Upgrading Original Engine with MCP Capabilities ===\n")
        
        # Initialize original engine
        original_engine = CareerGuidanceEngine()
        
        # First, demonstrate original behavior
        first_query = "Find sessions about leadership"
        print(f"\n[Original Engine Query]: {first_query}")
        start_time = time.time()
        original_response = original_engine.process_query(first_query)
        original_time = time.time() - start_time
        print(f"\n[Original Response] ({original_time:.2f}s):")
        print(original_response)
        
        # Now upgrade the engine
        print("\n--- Upgrading engine with MCP capabilities ---")
        upgraded_engine = mcp_integration.update_existing_career_engine(original_engine)
        
        # Test the upgraded engine on the same query
        print(f"\n[Upgraded Engine Query]: {first_query}")
        start_time = time.time()
        upgraded_response = upgraded_engine.process_query(first_query, args.user_id)
        upgraded_time = time.time() - start_time
        print(f"\n[Upgraded Response] ({upgraded_time:.2f}s):")
        print(upgraded_response)
        
        # Try a follow-up question
        followup_query = "Tell me more about the first session"
        print(f"\n[Follow-up Query]: {followup_query}")
        start_time = time.time()
        followup_response = upgraded_engine.process_query(followup_query, args.user_id)
        followup_time = time.time() - start_time
        print(f"\n[Follow-up Response] ({followup_time:.2f}s):")
        print(followup_response)
        
        print("\n" + "-" * 50)
    
    # Show context information
    print("\n=== User Context Information ===\n")
    context_info = mcp_integration.get_debug_info(args.user_id)
    print(f"Recent sessions in context: {context_info['session_context'].get('mentioned_sessions_count', 0)}")
    print(f"Vector store items: {context_info['vector_store_status']['items_count']}")
    print(f"NLP search sessions: {context_info['nlp_search_status']['sessions_count']}")
    
    print("\nExample complete!")

if __name__ == "__main__":
    main()