# ===================================================================================
# Project: ChatSkLearn
# File: src/routers/rag.py
# Description: FastAPI Endpoints for RAG
# Author: LALAN KUMAR
# Created: [08-11-2025]
# Updated: [09-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

import uuid
import os
import sys
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.schemas.api.rag import (
    RAGRequest,
    RAGResponse,
    StreamChunkSchema,
    StreamInitResponse,
    ErrorResponse,
    MessageSchema
)
from src.services.rag.rag_service import RAGService
from src.logger import logging

# Initialize router
router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    }
)

# Initialize RAG service (can be instantiated once and reused)
rag_service = RAGService()


def validate_request(request: RAGRequest) -> tuple[str, str]:
    """
    Validate request and generate thread_id if needed.
    
    Args:
        request: RAGRequest object
    
    Returns:
        Tuple of (thread_id, user_id)
    
    Raises:
        HTTPException: If validation fails
    """
    # Validate user_id
    if not request.user_id or not request.user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required and cannot be empty"
        )
    
    # Validate message
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message is required and cannot be empty"
        )
    
    # Generate thread_id if not provided
    thread_id = request.thread_id or f"{request.user_id}_{uuid.uuid4().hex[:12]}"
    
    return thread_id, request.user_id


@router.post(
    "/ask",
    response_model=RAGResponse,
    summary="Execute RAG query",
    description="Execute a RAG pipeline query and return the complete result"
)
async def ask(request: RAGRequest) -> RAGResponse:
    """
    Execute RAG pipeline and return the final response.
    
    **Request Parameters:**
    - `user_id` (required): Unique identifier for the user
    - `message` (required): User's query
    - `thread_id` (optional): Thread ID for conversation continuity. Auto-generated if not provided.
    
    **Response:**
    - `thread_id`: Thread ID for this conversation
    - `user_id`: User ID
    - `final_message`: Final response from the assistant
    - `router`: Query classification result
    - `documents_count`: Number of documents retrieved
    - `steps_completed`: Number of research steps completed
    """
    try:
        # Validate request and generate thread_id if needed
        thread_id, user_id = validate_request(request)
        
        # Execute RAG pipeline
        result = await rag_service.execute_rag(
            user_message=request.message.strip(),
            thread_id=thread_id,
            user_id=user_id
        )
        logging.info(f"RAG Result:{result}")
        # Extract final message
        final_message = result["messages"][-1].content if result["messages"] else "No response generated"
        logging.info(f"Final Response:{final_message}")
        
        # Extract router information
        router_info = result.get("router")
        logging.info(f"Information from Router:{router_info}")
        router_schema = None
        if router_info:
            router_schema = {
                "type": router_info.get("type", "unknown"),
                "logic": router_info.get("logic", "")
            }
        
        # Count documents and steps
        documents_count = len(result.get("documents", []))
        logging.info(f"Document Count:{documents_count}")
        steps_completed = len(result.get("steps", []))
        logging.info(f"Steps completed:{steps_completed}")
        
        return RAGResponse(
            thread_id=thread_id,
            user_id=user_id,
            final_message=final_message,
            router=router_schema,
            documents_count=documents_count,
            steps_completed=steps_completed
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )


@router.post(
    "/ask/stream",
    summary="Execute RAG query with streaming",
    description="Execute RAG pipeline with streaming output for real-time updates"
)
async def ask_stream(request: RAGRequest):
    """
    Execute RAG pipeline with streaming output.
    
    **Request Parameters:**
    - `user_id` (required): Unique identifier for the user
    - `message` (required): User's query
    - `thread_id` (optional): Thread ID for conversation continuity. Auto-generated if not provided.
    
    **Response:**
    Returns Server-Sent Events (SSE) stream with:
    1. Initial metadata (thread_id, user_id, status)
    2. Node execution events with data updates
    3. Stream termination signal
    """
    try:
        # Validate request and generate thread_id if needed
        thread_id, user_id = validate_request(request)
        
        # Create async generator for streaming
        async def stream_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events for the stream."""
            
            # Send initial response
            init_response = StreamInitResponse(
                thread_id=thread_id,
                user_id=user_id,
                status="streaming"
            )
            yield f"data: {init_response.model_dump_json()}\n\n"
            
            # Stream execution updates
            try:
                async for chunk in rag_service.execute_rag_stream(
                    user_message=request.message.strip(),
                    thread_id=thread_id,
                    user_id=user_id,
                    stream_mode="updates"
                ):
                    # chunk is a dict like {"node_name": {"key": value, ...}}
                    for node_name, node_data in chunk.items():
                        stream_chunk = StreamChunkSchema(
                            node=node_name,
                            event_type="update",
                            data=node_data
                        )
                        yield f"data: {stream_chunk.model_dump_json()}\n\n"
                
                # IMPORTANT: After streaming completes, invoke the full graph once more
                # to ensure the final state is persisted to the checkpointer
                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "user_id": user_id
                    }
                }
                
                # This final invoke ensures the state is saved to checkpoint
                await rag_service.graph.ainvoke(
                    {"messages": []},  # Empty input, uses existing state from checkpoint
                    config
                )
                
                # Send completion signal
                completion_chunk = StreamChunkSchema(
                    node="stream",
                    event_type="end",
                    data={"status": "completed", "thread_id": thread_id}
                )
                yield f"data: {completion_chunk.model_dump_json()}\n\n"
            
            except Exception as e:
                error_chunk = StreamChunkSchema(
                    node="stream",
                    event_type="error",
                    data={"error": str(e)}
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
        
        # Return streaming response
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for Nginx
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initiating stream: {str(e)}"
        )

@router.get(
    "/thread/{thread_id}",
    summary="Get conversation history",
    description="Retrieve the full conversation history for a specific thread"
)
async def get_thread_history(thread_id: str, user_id: str):
    """
    Get conversation history for a thread.
    
    **Query Parameters:**
    - `thread_id` (path): Thread ID to retrieve
    - `user_id` (query): User ID (for validation)
    
    **Response:**
    - Full state including messages, documents, and metadata
    """
    try:
        # Validate user_id
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id query parameter is required"
            )
        
        # Get conversation history
        history = await rag_service.get_conversation_history(thread_id)
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No conversation history found for thread_id: {thread_id}"
            )
        
        return {
            "thread_id": thread_id,
            "user_id": user_id,
            "history": history
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving history: {str(e)}"
        )