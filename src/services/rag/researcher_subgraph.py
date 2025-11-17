# ===================================================================================
# Project: ChatSkLearn
# File: src/services/rag/researcher_subgraph.py
# Description: Implementation of researcher sub-graph
# Author: LALAN KUMAR
# Created: [06-11-2025]
# Updated: [06-11-2025]
# LAST MODIFIED BY: LALAN KUMAR [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

import os
import sys
import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict, cast, List
from langchain_core.documents import Document

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.logger import logging

from src.services.rag.states import ResearcherState, QueryState
from src.services.rag.prompts import GENERATE_QUERIES_SYSTEM_PROMPT
from src.config import LLM_MODEL, EMBEDDING_MODEL, INDEX_NAME
from src.dependencies import get_opensearch_client
from src.services.opensearch.hybrid_search_service import hybrid_search

async def generate_queries(state:ResearcherState)->dict:
    """Generate search queries based on the question (a step in the research plan)"""

    class Response(TypedDict):
        queries: list[str]

    model = LLM_MODEL.with_structured_output(Response)

    messages = [
        {"role": "system", "content": GENERATE_QUERIES_SYSTEM_PROMPT},
        {"role": "human", "content": state["question"]}
    ]

    response = cast(Response, await model.ainvoke(messages))

    return {"queries": response["queries"]}


async def retrieve_documents(
    state: QueryState
) -> dict[str, List[Document]]:
    """
    Retrieve documents using hybrid search for a single query.
    
    Args:
        state: QueryState containing the query
        
    Returns:
        Dictionary with documents key containing retrieved documents
    """

    
    try:
        logging.info(f"Performing hybrid search for query: {state['query']}")

        opensearch_client = get_opensearch_client()

        results = hybrid_search(
            query=state["query"],
            client=opensearch_client,
            embedding_client=EMBEDDING_MODEL,
            index_name=INDEX_NAME,
            top_k=5,
            include_code=True,
            bm25_weight=0.4,
            vector_weight=0.6
        )

        documents = []
        for result in results:
            doc = Document(
                page_content=result["content"]["full_text"],
                metadata={
                    "chunk_id": result["chunk_id"],
                    "score": result["score"],
                    "source_url": result["metadata"]["source_url"],
                    "page_type": result["metadata"]["page_type"],
                    "heading": result["content"]["heading"],
                    "title": result["metadata"]["title"],
                    "breadcrumbs": result["metadata"]["breadcrumbs"],
                    "has_code": result["has_code"],
                    "code_blocks": result["code_blocks"]
                }
            )
            documents.append(doc)

        logging.info(f"Retrieved {len(documents)} documents for query: {state['query']}")
        return {"documents": documents}
    
    except Exception as e:
        logging.error(f"Error in hybrid search for query '{state['query']}': {e}")
        raise


def retrieve_in_parallel(state: ResearcherState) -> list[Send]:
    """
    Create parallel retrieval tasks for each generated query.
    
    Args:
        state: ResearcherState containing the list of queries
        
    Returns:
        List of Send objects to execute retrieve_documents in parallel for each query
    """
    return [
        Send("retrieve_documents", {"query": query, "documents": []}) 
        for query in state["queries"]
    ]



def create_researcher_graph():
    """Create and return the researcher graph."""
    builder = StateGraph(ResearcherState)
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("retrieve_documents", retrieve_documents)
    builder.add_edge(START, "generate_queries")
    builder.add_conditional_edges(
        "generate_queries",
        retrieve_in_parallel,  
        path_map=["retrieve_documents"],
    )
    builder.add_edge("retrieve_documents", END)
    
    # Compile into a graph object
    researcher_graph = builder.compile()
    researcher_graph.name = "ResearcherGraph"
    
    return researcher_graph


# Example usage:
#if __name__ == "__main__":
    #graph=create_researcher_graph()
    #print(graph)
    #print(graph.name)
    #print(graph.nodes)

    #state = ResearcherState(question="How to perform PCA on images?")
    #result = asyncio.run(graph.ainvoke(state))
    #print(result)
    #logging.info(f"----------------------------------------------------Results------------------------------------------------------\n {result}")