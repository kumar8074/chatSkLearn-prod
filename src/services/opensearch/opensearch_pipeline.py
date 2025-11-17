# ===================================================================================
# Project: ChatSkLearn
# File: src/services/search/opensearch_pipeline.py
# Description: Used only for local testing
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.0.0
# ===================================================================================

import os
import sys

# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)


from src.config import (OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS, 
                        EMBEDDING_MODEL, INDEX_NAME)
from src.logger import logging

from src.services.opensearch.factory import connect_to_opensearch
from src.services.indexing.opensearch_indexer import index_chunks
from src.services.indexing.index_config import SKLEARN_INDEX_BODY
from src.services.opensearch.hybrid_search_service import hybrid_search


client, _ = connect_to_opensearch("localhost:9200", OPENSEARCH_USER, OPENSEARCH_PASS)

# Test connection
if not client.ping():
    raise ConnectionError("Failed to connect to OpenSearch")
    
logging.info(f"✅ Connected to OpenSearch at {OPENSEARCH_HOST}")
    
# Index chunks
chunks_file = "temp/sklearn_scraped_data/chunks_with_embeddings.json"
    
try:
    indexed_count = index_chunks(
        chunks_embeddings_file=chunks_file,
        index_name=INDEX_NAME,
        client=client,
        index_body=SKLEARN_INDEX_BODY
    )
        
    logging.info(f"\n{'='*60}")
    logging.info(f"✅ Successfully indexed {indexed_count} chunks into '{INDEX_NAME}'")
    logging.info(f"{'='*60}\n")
        
except Exception as e:
    logging.error(f"❌ Failed to index chunks: {e}")
    raise


# Perform hybrid search test
# Test queries
test_queries = [
    "How to use RandomForestClassifier for classification",
    "GridSearchCV parameters and usage",
    "Example of cross-validation in scikit-learn"
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
        
    results = hybrid_search(
        query=query,
        client=client,
        embedding_client=EMBEDDING_MODEL,
        index_name=INDEX_NAME,
        top_k=3
    )
        
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['metadata']['page_type']}] {result['metadata']['title']}")
        print(f"   Score: {result['score']:.4f}")
        print(f"   Has Code: {result['has_code']}")
        print(f"   URL: {result['metadata']['source_url']}")
        print()
