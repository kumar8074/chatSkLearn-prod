#!/usr/bin/env python3
"""
Test script to verify Langfuse integration works correctly
Usage: python test_langfuse.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()


# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.langfuse.langfuse_tracer import get_langfuse_config, get_langfuse_callback


def test_langfuse_config():
    """Test Langfuse configuration"""
    print("=" * 60)
    print("Testing Langfuse Configuration")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    env_vars = {
        "LANGFUSE_ENABLED": os.getenv("LANGFUSE_ENABLED", "not set"),
        "LANGFUSE_PUBLIC_KEY": os.getenv("LANGFUSE_PUBLIC_KEY", "not set")[:20] + "..." if os.getenv("LANGFUSE_PUBLIC_KEY") else "not set",
        "LANGFUSE_SECRET_KEY": os.getenv("LANGFUSE_SECRET_KEY", "not set")[:20] + "..." if os.getenv("LANGFUSE_SECRET_KEY") else "not set",
        "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST", "not set"),
    }
    
    for key, value in env_vars.items():
        print(f"   {key}: {value}")
    
    # Get config
    print("\n2. Initializing Langfuse config...")
    config = get_langfuse_config()
    
    if not config.enabled:
        print("   ❌ Langfuse is disabled or not configured")
        print("\n   To enable Langfuse:")
        print("   1. Sign up at https://cloud.langfuse.com")
        print("   2. Get your API keys")
        print("   3. Add to .env:")
        print("      LANGFUSE_ENABLED=true")
        print("      LANGFUSE_PUBLIC_KEY=pk-lf-...")
        print("      LANGFUSE_SECRET_KEY=sk-lf-...")
        return False
    
    print("   ✅ Langfuse is enabled")
    print(f"   Host: {config.host}")
    
    # Test callback handler creation
    print("\n3. Testing callback handler creation...")
    handler = get_langfuse_callback(
        session_id="test_session_001",
        user_id="test_user",
        trace_name="test-trace",
        metadata={"test": True},
        tags=["test", "sklearn-assistant"]
    )
    
    if handler is None:
        print("   ❌ Failed to create callback handler")
        return False
    
    print("   ✅ Callback handler created successfully")
    print(f"   Handler type: {type(handler).__name__}")
    
    # Test flush
    print("\n4. Testing flush...")
    try:
        config.flush()
        print("   ✅ Flush completed successfully")
    except Exception as e:
        print(f"   ❌ Flush failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Make API requests to your FastAPI app")
    print("2. View traces at:", config.host)
    print("3. Look for traces tagged with 'sklearn-assistant'")
    
    return True


def test_simple_trace():
    """Test creating a simple trace"""
    print("\n" + "=" * 60)
    print("Testing Simple Trace Creation")
    print("=" * 60)
    
    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Get callback
    handler = get_langfuse_callback(
        session_id="test_simple_trace",
        user_id="test_user",
        trace_name="simple-test-trace",
        tags=["test", "simple"]
    )
    
    if handler is None:
        print("❌ Langfuse not configured. Skipping trace test.")
        return False
    
    print("\n1. Creating test LLM call with Langfuse tracing...")
    
    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.7
        )
        
        # Make a simple call with callback
        messages = [HumanMessage(content="Say 'Hello from Langfuse test!'")]
        response = llm.invoke(messages, config={"callbacks": [handler]})
        
        print(f"   ✅ LLM response: {response.content[:100]}...")
        
        # Flush to ensure trace is sent
        print("\n2. Flushing traces...")
        config = get_langfuse_config()
        config.flush()
        
        print("   ✅ Trace flushed successfully")
        print(f"\n3. View your trace at: {config.host}")
        print("   Look for trace named: simple-test-trace")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_rag_service():
    """Test with actual RAG service"""
    print("\n" + "=" * 60)
    print("Testing RAG Service with Langfuse")
    print("=" * 60)
    
    try:
        from src.services.rag.rag_service import RAGService
        
        print("\n1. Initializing RAG service...")
        rag_service = RAGService()
        
        print("\n2. Executing test query with tracing...")
        result = await rag_service.execute_rag(
            user_message="What is scikit-learn?",
            thread_id="test_rag_trace_001",
            user_id="test_user",
            metadata={"test": True, "purpose": "integration_test"}
        )
        
        print(f"   ✅ Query executed successfully")
        
        if result.get("messages"):
            final_message = result["messages"][-1].content
            print(f"   Response preview: {final_message[:100]}...")
        
        config = get_langfuse_config()
        print(f"\n3. View your trace at: {config.host}")
        print("   Look for trace named: sklearn-assistant-test_rag_trace_001")
        print("   This trace will show all graph nodes, LLM calls, and retrievals")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        print("\n   This test requires:")
        print("   - OpenSearch running and indexed")
        print("   - All environment variables configured")
        print("   - Run from within Docker container or with proper setup")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Langfuse Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Configuration
    if not test_langfuse_config():
        print("\n❌ Configuration test failed. Fix the issues and try again.")
        return
    
    # Test 2: Simple trace
    input("\nPress Enter to run simple trace test (requires GOOGLE_API_KEY)...")
    test_simple_trace()
    
    # Test 3: RAG service (optional)
    print("\n" + "=" * 60)
    response = input("\nRun RAG service test? (requires full setup) [y/N]: ")
    if response.lower() == 'y':
        asyncio.run(test_with_rag_service())
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()