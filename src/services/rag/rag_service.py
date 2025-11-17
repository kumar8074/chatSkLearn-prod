# ===================================================================================
# Project: ChatSkLearn
# File: src/services/rag/rag_service.py
# Description: Implementation of RAG service
# Author: LALAN KUMAR
# Created: [08-11-2025]
# Updated: [09-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import os
import sys
from typing import Any, AsyncGenerator, Dict, Optional
from langchain_core.messages import HumanMessage

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.rag.sklearn_graph import create_assistant_graph
from src.services.rag.states import AgentState
from src.services.langfuse.langfuse_tracer import get_langfuse_callback, get_langfuse_config                                                                            


class RAGService:
    """Service for executing RAG operations with thread-based checkpointing."""
    
    def __init__(self):
        """Initialize the RAG service with the compiled assistant graph."""
        self.graph = create_assistant_graph()
        self.langfuse_config = get_langfuse_config()

    def _prepare_config(
            self,
            thread_id: str,
            user_id: str,
            session_id: Optional[str] = None,
            metadata: Optional[dict] = None
        )-> Dict[str,Any]:
        """
        Prepare configuration with Langfuse callback handler
        
        Args:
            thread_id: Conversation thread ID
            user_id: User identifier
            session_id: Optional session ID (defaults to thread_id)
            metadata: Additional metadata for the trace
            
        Returns:
            Configuration dictionary with callback handlers
        """
        # Use thread_id as session_id if not provided
        session_id = session_id or thread_id
        
        # Prepare trace metadata
        trace_metadata = {
            "thread_id": thread_id,
            "user_id": user_id,
            "session_id": session_id,
            "service": "sklearn-assistant",
            **(metadata or {})
        }
        
        # Get Langfuse callback handler
        langfuse_handler = get_langfuse_callback()
        
        # Build config
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            },
            "metadata": trace_metadata,
            "tags": ["sklearn-assistant", "rag", "langgraph", f"user:{user_id}"],
            "run_name": f"sklearn-assistant-{thread_id}"
        }
        
        # Add Langfuse callback if enabled
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]
        
        return config

    
    async def execute_rag(
        self,
        user_message: str,
        thread_id: str,
        user_id: str | None = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Execute RAG pipeline synchronously and return final result.
        
        Uses thread_id for checkpointing to maintain conversation state across calls.
        
        Args:
            user_message: The user's query or message
            thread_id: Unique identifier for conversation thread (used as checkpoint ID)
            user_id: Optional user identifier for tracking
            session_id: Optional session ID for grouping traces
            metadata: Additional metadata to attach to the trace
        
        Returns:
            Dictionary containing the final state with messages, documents, and router info
        """

        user_id = user_id or "unknown_user"

        # prepare config with Langfuse callback
        config = self._prepare_config(
            thread_id=thread_id,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "message_length": len(user_message),
                **(metadata or {})
            }
        )
        
        # Prepare input state
        input_state: AgentState = {
            "messages": [HumanMessage(content=user_message)]
        }
        
        try:
            # Execute graph with Langfuse tracing
            result = await self.graph.ainvoke(input_state, config)
            
            # Flush Langfuse to ensure traces are sent
            self.langfuse_config.flush()
            
            return result
        except Exception as e:
            # Log error and flush
            print(f"❌ Error in execute_rag: {e}")
            self.langfuse_config.flush()
            raise

    
    async def execute_rag_stream(
        self,
        user_message: str,
        thread_id: str,
        user_id: str | None = None,
        stream_mode: str = "updates",
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute RAG pipeline with streaming output.
        
        Yields intermediate state updates as the graph processes the query.
        Uses thread_id for checkpointing to maintain conversation state.
        
        Args:
            user_message: The user's query or message
            thread_id: Unique identifier for conversation thread (used as checkpoint ID)
            user_id: Optional user identifier for tracking
            session_id: Optional session ID for grouping traces
            metadata: Additional metadata to attach to the trace
            stream_mode: Streaming mode - "updates" (default) or "values"
                - "updates": Yields only changed values for each node
                - "values": Yields full state after each node completes
        
        Yields:
            Dictionary containing streamed updates from each node execution
        """

        user_id = user_id or "unknown_user"

        # Prepare config with Langfuse callback
        config = self._prepare_config(
            thread_id=thread_id,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "message_length": len(user_message),
                "stream_mode": stream_mode,
                **(metadata or {})
            }
        )
        
        # Prepare input state
        input_state: AgentState = {
            "messages": [HumanMessage(content=user_message)]
        }

        try:
            # Stream graph execution with Langfuse tracing
            async for chunk in self.graph.astream(
                input_state,
                config,
                stream_mode=stream_mode
            ):
                yield chunk
            
            # Flush Langfuse after streaming completes
            self.langfuse_config.flush()
        except Exception as e:
            # Log error and flush
            print(f"❌ Error in execute_rag_stream: {e}")
            self.langfuse_config.flush()
            raise

    
    async def get_conversation_history(
        self,
        thread_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieve the full conversation history for a thread.
        
        Uses the checkpointer to load the last state of the conversation.
        
        Args:
            thread_id: Unique identifier for the conversation thread
        
        Returns:
            The last saved state including messages, documents, and metadata
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Get the state at the end of the thread
        state = await self.graph.aget_state(config)
        
        return state.values if state else {}

