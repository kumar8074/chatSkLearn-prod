# ===================================================================================
# Project: ChatSkLearn
# File: src/services/opensearch/hybrid_search_service.py
# Description: Hybrid Search (BM25 + Vector) with RRF for scikit-learn documentation
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import os
import sys
from langchain.embeddings import Embeddings
from opensearchpy import OpenSearch
from typing import List, Dict, Any, Optional

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.logger import logging


def detect_query_type(query: str) -> str:
    """
    Detect the type of query to optimize search strategy.
    
    Args:
        query: The user's search query
        
    Returns:
        str: One of 'code', 'api', 'example', or 'general'
    """
    query_lower = query.lower()
    
    # Code-related keywords
    code_keywords = ['code', 'example', 'how to', 'implement', 'syntax', 'usage']
    if any(keyword in query_lower for keyword in code_keywords):
        return 'code'
    
    # API reference keywords
    api_keywords = ['parameters', 'arguments', 'returns', 'attributes', 'methods', 'class', 'function']
    if any(keyword in query_lower for keyword in api_keywords):
        return 'api'
    
    # Example keywords
    example_keywords = ['example', 'demo', 'tutorial', 'guide', 'walkthrough']
    if any(keyword in query_lower for keyword in example_keywords):
        return 'example'
    
    return 'general'


def get_search_fields(query_type: str) -> List[str]:
    """
    Get optimized search fields based on query type.
    
    Args:
        query_type: Type of query ('code', 'api', 'example', 'general')
        
    Returns:
        List of field names with boost values
    """
    field_configs = {
        'code': [
            'code_blocks.code^3.5',
            'full_text^3',
            'heading^2',
            'text^1.5',
            'code_blocks.context^1.5'
        ],
        'api': [
            'heading^3.5',
            'metadata.title^3',
            'text^2.5',
            'enriched_text^2',
            'code_blocks.code^1.5'
        ],
        'example': [
            'full_text^3',
            'code_blocks.code^3',
            'heading^2.5',
            'text^2',
            'enriched_text^1.5'
        ],
        'general': [
            'heading^3',
            'text^2.5',
            'enriched_text^2',
            'metadata.title^2',
            'full_text^1.5'
        ]
    }
    
    return field_configs.get(query_type, field_configs['general'])


def get_page_type_boost(query_type: str) -> Dict[str, float]:
    """
    Get page type boosting based on query type.
    
    Args:
        query_type: Type of query
        
    Returns:
        Dictionary mapping page types to boost values
    """
    boost_configs = {
        'code': {
            'example': 1.4,
            'tutorial': 1.2,
            'user_guide': 1.0,
            'api_reference': 0.9
        },
        'api': {
            'api_reference': 1.4,
            'user_guide': 1.1,
            'example': 1.0,
            'tutorial': 0.9
        },
        'example': {
            'example': 1.5,
            'tutorial': 1.3,
            'user_guide': 1.0,
            'api_reference': 0.8
        },
        'general': {
            'user_guide': 1.2,
            'tutorial': 1.1,
            'example': 1.1,
            'api_reference': 1.0
        }
    }
    
    return boost_configs.get(query_type, boost_configs['general'])


def build_bm25_query(
    query: str,
    query_type: str,
    top_k: int,
    include_code: bool = True
) -> Dict[str, Any]:
    """
    Build optimized BM25 query based on query type.
    
    Args:
        query: Search query
        query_type: Type of query
        top_k: Number of results
        include_code: Whether to boost results with code
        
    Returns:
        OpenSearch BM25 query dictionary
    """
    search_fields = get_search_fields(query_type)
    page_type_boosts = get_page_type_boost(query_type)
    
    # Build should clauses for page type boosting
    should_clauses = []
    for page_type, boost in page_type_boosts.items():
        should_clauses.append({
            "term": {
                "page_type": {
                    "value": page_type,
                    "boost": boost
                }
            }
        })
    
    # Add code boost if requested
    if include_code and query_type in ['code', 'example']:
        should_clauses.append({
            "term": {
                "has_code": {
                    "value": True,
                    "boost": 1.3
                }
            }
        })
    
    query_body = {
        "size": top_k * 2,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": search_fields,
                            "type": "best_fields",
                            "operator": "or",
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "should": should_clauses,
                "minimum_should_match": 0
            }
        },
        "_source": {
            "excludes": ["embedding"]  # Don't return embeddings in results
        }
    }
    
    return query_body


def build_vector_query(
    query_embedding: List[float],
    top_k: int,
    query_type: str,
    include_code: bool = True
) -> Dict[str, Any]:
    """
    Build vector similarity query with filters.
    
    Args:
        query_embedding: Query vector
        top_k: Number of results
        query_type: Type of query
        include_code: Whether to prefer results with code
        
    Returns:
        OpenSearch vector query dictionary
    """
    page_type_boosts = get_page_type_boost(query_type)
    
    # Build filter for page types (not as strict as must)
    should_clauses = []
    for page_type in page_type_boosts.keys():
        should_clauses.append({
            "term": {"page_type": page_type}
        })
    
    query_body = {
        "size": top_k * 2,
        "query": {
            "script_score": {
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 0
                    }
                },
                "script": {
                    "source": "knn_score",
                    "lang": "knn",
                    "params": {
                        "field": "embedding",
                        "query_value": query_embedding,
                        "space_type": "cosinesimil"
                    }
                }
            }
        },
        "_source": {
            "excludes": ["embedding"]
        }
    }
    
    return query_body


def reciprocal_rank_fusion(
    bm25_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    k: int = 60,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6
) -> Dict[str, float]:
    """
    Combine results using Reciprocal Rank Fusion with weights.
    
    Args:
        bm25_results: Results from BM25 search
        vector_results: Results from vector search
        k: RRF constant (default: 60)
        bm25_weight: Weight for BM25 scores
        vector_weight: Weight for vector scores
        
    Returns:
        Dictionary mapping document IDs to combined scores
    """
    combined_scores: Dict[str, float] = {}
    
    # Process BM25 results
    for rank, hit in enumerate(bm25_results):
        doc_id = hit["_id"]
        rrf_score = 1.0 / (k + rank + 1)
        combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + (rrf_score * bm25_weight)
    
    # Process vector results
    for rank, hit in enumerate(vector_results):
        doc_id = hit["_id"]
        rrf_score = 1.0 / (k + rank + 1)
        combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + (rrf_score * vector_weight)
    
    return combined_scores


def format_search_result(doc: Dict[str, Any], score: float) -> Dict[str, Any]:
    """
    Format a search result for consumption by the RAG system.
    
    Args:
        doc: Document from OpenSearch
        score: Combined RRF score
        
    Returns:
        Formatted result dictionary
    """
    source = doc["_source"]
    
    return {
        "chunk_id": source.get("chunk_id", ""),
        "score": score,
        "content": {
            "heading": source.get("heading", ""),
            "text": source.get("text", ""),
            "full_text": source.get("full_text", ""),  # Includes code
            "enriched_text": source.get("enriched_text", "")
        },
        "code_blocks": source.get("code_blocks", []),
        "has_code": source.get("has_code", False),
        "metadata": {
            "source_url": source.get("source_url", ""),
            "page_type": source.get("page_type", ""),
            "breadcrumbs": source.get("breadcrumbs", []),
            "title": source.get("metadata", {}).get("title", "")
        }
    }


def hybrid_search(
    query: str,
    client: OpenSearch,
    embedding_client: Embeddings,
    index_name: str,
    top_k: int = 5,
    include_code: bool = True,
    bm25_weight: float = 0.4,
    vector_weight: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining BM25 and vector similarity with RRF.
    Optimized for scikit-learn documentation retrieval.
    
    Args:
        query: Natural language search query
        client: OpenSearch client instance
        embedding_client: LangChain embeddings model
        index_name: Name of the OpenSearch index
        top_k: Number of final results to return
        include_code: Whether to boost results with code examples
        bm25_weight: Weight for BM25 scores (default: 0.4)
        vector_weight: Weight for vector scores (default: 0.6)
        
    Returns:
        List of formatted search results with scores and metadata
        
    Example:
        >>> results = hybrid_search(
        ...     "How to use RandomForestClassifier",
        ...     client,
        ...     embedding_model,
        ...     "sklearn_documentation",
        ...     top_k=5
        ... )
        >>> for result in results:
        ...     print(result["metadata"]["title"], result["score"])
    """
    
    logging.info(f"Performing hybrid search for query: '{query}'")
    
    # Detect query type for optimization
    query_type = detect_query_type(query)
    logging.info(f"Detected query type: {query_type}")
    
    # Generate query embedding
    try:
        query_embedding: List[float] = embedding_client.embed_query(query)
    except Exception as e:
        logging.error(f"Failed to generate query embedding: {e}")
        raise
    
    # Build and execute BM25 search
    bm25_query = build_bm25_query(query, query_type, top_k, include_code)
    try:
        bm25_results = client.search(index=index_name, body=bm25_query)
        bm25_hits = bm25_results["hits"]["hits"]
        logging.info(f"BM25 search returned {len(bm25_hits)} results")
    except Exception as e:
        logging.error(f"BM25 search failed: {e}")
        bm25_hits = []
    
    # Build and execute vector search
    vector_query = build_vector_query(query_embedding, top_k, query_type, include_code)
    try:
        vector_results = client.search(index=index_name, body=vector_query)
        vector_hits = vector_results["hits"]["hits"]
        logging.info(f"Vector search returned {len(vector_hits)} results")
    except Exception as e:
        logging.error(f"Vector search failed: {e}")
        vector_hits = []
    
    # Combine results using RRF
    combined_scores = reciprocal_rank_fusion(
        bm25_hits,
        vector_hits,
        k=60,
        bm25_weight=bm25_weight,
        vector_weight=vector_weight
    )
    
    # Sort by combined score
    ranked_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    logging.info(f"Combined {len(ranked_docs)} unique documents")
    
    # Retrieve and format top-k results
    final_results: List[Dict[str, Any]] = []
    for doc_id, score in ranked_docs[:top_k]:
        try:
            doc = client.get(index=index_name, id=doc_id)
            formatted_result = format_search_result(doc, score)
            final_results.append(formatted_result)
        except Exception as e:
            logging.warning(f"Failed to retrieve document {doc_id}: {e}")
            continue
    
    logging.info(f"Returning {len(final_results)} final results")
    
    return final_results


def search_with_filters(
    query: str,
    client: OpenSearch,
    embedding_client: Embeddings,
    index_name: str,
    top_k: int = 5,
    page_types: Optional[List[str]] = None,
    must_have_code: bool = False,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search with additional filters.
    
    Args:
        query: Search query
        client: OpenSearch client
        embedding_client: Embeddings model
        index_name: Index name
        top_k: Number of results
        page_types: Filter by specific page types (e.g., ['example', 'tutorial'])
        must_have_code: Only return results with code examples
        **kwargs: Additional arguments for hybrid_search
        
    Returns:
        List of filtered search results
    """
    # Perform base hybrid search with more results
    results = hybrid_search(
        query=query,
        client=client,
        embedding_client=embedding_client,
        index_name=index_name,
        top_k=top_k * 2,  # Get more results for filtering
        **kwargs
    )
    
    # Apply filters
    filtered_results = []
    for result in results:
        # Filter by page type
        if page_types and result["metadata"]["page_type"] not in page_types:
            continue
        
        # Filter by code presence
        if must_have_code and not result["has_code"]:
            continue
        
        filtered_results.append(result)
        
        # Stop when we have enough results
        if len(filtered_results) >= top_k:
            break
    
    return filtered_results


    
    