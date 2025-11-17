# ===================================================================================
# Project: ChatSkLearn
# File: src/schemas/api/rag.py
# Description: Pydantic schemas for Request validation and Response serialization
# Author: LALAN KUMAR
# Created: [08-11-2025]
# Updated: [09-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

from typing import Optional
from pydantic import BaseModel, Field

class RAGRequest(BaseModel):
    """Schema for RAG query request."""
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="User's query or message")
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for conversation continuity. If not provided, a new one is generated."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "message": "How to use RandomForestClassifier?",
                "thread_id": "conv_abc123"  # Optional
            }
        }


class MessageSchema(BaseModel):
    """Schema for message objects in responses."""
    type: str
    content: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "HumanMessage",
                "content": "How to use RandomForestClassifier?"
            }
        }


class DocumentSchema(BaseModel):
    """Schema for document objects in responses."""
    page_content: str
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "page_content": "RandomForestClassifier is an ensemble method...",
                "metadata": {"source": "sklearn_docs"}
            }
        }


class RouterSchema(BaseModel):
    """Schema for routing decision."""
    type: str
    logic: str

    class Config:
        json_schema_extra = {
            "example": {
                "type": "scikit-learn",
                "logic": "This is a question about scikit-learn library"
            }
        }


class RAGResponse(BaseModel):
    """Schema for RAG query response."""
    thread_id: str = Field(..., description="Thread ID for this conversation")
    user_id: str = Field(..., description="User ID")
    final_message: str = Field(..., description="Final response message from the assistant")
    router: Optional[RouterSchema] = Field(default=None, description="Query classification result")
    documents_count: int = Field(default=0, description="Number of documents retrieved")
    steps_completed: int = Field(default=0, description="Number of research steps completed")

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "conv_abc123",
                "user_id": "user_123",
                "final_message": "RandomForestClassifier is an ensemble learning method...",
                "router": {
                    "type": "scikit-learn",
                    "logic": "This is about scikit-learn"
                },
                "documents_count": 5,
                "steps_completed": 2
            }
        }


class StreamChunkSchema(BaseModel):
    """Schema for individual stream chunks."""
    node: str = Field(..., description="Name of the node being executed")
    event_type: str = Field(..., description="Type of event: 'start', 'update', 'end'")
    data: Optional[dict] = Field(default=None, description="Updated data from the node")

    class Config:
        json_schema_extra = {
            "example": {
                "node": "analyze_and_route_query",
                "event_type": "end",
                "data": {
                    "router": {
                        "type": "scikit-learn",
                        "logic": "Query about scikit-learn library"
                    }
                }
            }
        }


class StreamInitResponse(BaseModel):
    """Initial response for stream endpoint."""
    thread_id: str = Field(..., description="Thread ID for this conversation")
    user_id: str = Field(..., description="User ID")
    status: str = Field(default="streaming", description="Status of the stream")

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "conv_abc123",
                "user_id": "user_123",
                "status": "streaming"
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
    thread_id: Optional[str] = Field(default=None, description="Thread ID if available")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid user_id",
                "detail": "user_id must be a non-empty string",
                "thread_id": None
            }
        }