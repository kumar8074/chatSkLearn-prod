# ===================================================================================
# Project: ChatSkLearn
# File: src/services/rag/state.py
# Description: State schema definition for RAG service
# Author: LALAN KUMAR
# Created: [05-11-2025]
# Updated: [05-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

from typing import List, Optional, Any, Annotated
from typing_extensions import TypedDict, Literal, NotRequired
from operator import add
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

#----------------------- Router state definitions -----------------------#
class Router(TypedDict):
    """Structured output for query classification."""
    type: Literal["scikit-learn", "more-info", "general"]
    logic: str

#----------------------- Researcher sub-Agent state definitions -----------------------#
class ResearcherState(TypedDict):
    """Main state for researcher sub-graph"""
    question: str
    queries: List[str]
    documents: Annotated[List[Document], add]

class QueryState(TypedDict):
    """Per-query state used during parallel retrieval"""
    query: str
    documents: List[Document]


#----------------------- Main agent state definitions -----------------------#
class InputState(TypedDict):
    """Initial input from the user to the system."""
    messages: List[BaseMessage]
    
    
class AgentState(TypedDict):
    """Main unified state for the SkLearnAssistantGraph."""

    # Core conversation
    messages: List[BaseMessage]

    # Routing and logic
    router: Router                      # Output from query analysis step
    steps: List[str]                    # Research plan steps
    documents: List[Document]           # Accumulated research documents

    # Conversation management
    summary: Optional[str]              # Summary of past conversation
    last_summarized_index: Optional[int]

    # Optional metadata
    user_id: NotRequired[str]
    thread_id: NotRequired[str]
    config: NotRequired[Any]