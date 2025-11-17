# ===================================================================================
# Project: ChatSkLearn
# File: src/dependencies
# Description: Dependency injection for search & FastAPI. Provides reusable dependencies for OpenSearch client and embedding model
# Author: LALAN KUMAR
# Created: [06-11-2025]
# Updated: [06-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

import os
import sys
from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from opensearchpy import OpenSearch
from langchain.embeddings import Embeddings

# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.config import (
    OPENSEARCH_HOST,
    OPENSEARCH_USER,
    OPENSEARCH_PASS,
    EMBEDDING_MODEL,
    INDEX_NAME
)
from src.services.opensearch.factory import connect_to_opensearch
from src.logger import logging


@lru_cache()
def get_opensearch_client() -> OpenSearch:
    """
    Get OpenSearch client instance (cached)
    
    Returns:
        OpenSearch: Connected client instance
        
    Raises:
        Exception: If connection fails
    """
    try:
        client, health = connect_to_opensearch(
            opensearch_host=OPENSEARCH_HOST,               #"localhost:9200", For local testing
            opensearch_user=OPENSEARCH_USER,
            opensearch_pass=OPENSEARCH_PASS
        )
        logging.info(f"OpenSearch client connected: {health.get('status', 'unknown')}")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to OpenSearch: {e}")
        raise


@lru_cache()
def get_embedding_model() -> Embeddings:
    """
    Get embedding model instance (cached)
    
    Returns:
        Embeddings: LangChain embedding model
    """
    logging.info(f"Using embedding model: {EMBEDDING_MODEL}")
    return EMBEDDING_MODEL


@lru_cache()
def get_index_name() -> str:
    """
    Get configured index name
    
    Returns:
        str: OpenSearch index name
    """
    return INDEX_NAME


# Type aliases for dependency injection
OpenSearchClient = Annotated[OpenSearch, Depends(get_opensearch_client)]
EmbeddingModel = Annotated[Embeddings, Depends(get_embedding_model)]
IndexName = Annotated[str, Depends(get_index_name)]