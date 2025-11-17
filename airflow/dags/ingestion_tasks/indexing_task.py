# ===================================================================================
# Project: ChatSkLearn
# File: airflow/dags/ingestion_tasks/indexing_task.py
# Description: Airflow TASK to index scikit-learn chunks to OpenSearch
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.1.0
# ===================================================================================

import sys

# Add src to path for imports
sys.path.insert(0, '/opt/airflow')

from src.services.indexing.opensearch_indexer import index_chunks
from src.services.indexing.index_config import SKLEARN_INDEX_BODY
from src.services.opensearch.factory import connect_to_opensearch
from src.config import OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS, INDEX_NAME
from src.logger import logging


def index_sklearn_to_opensearch(
    embedded_chunks_file: str = "temp/sklearn_scraped_data/embedded_chunks.json",
    index_name: str = None
) -> dict:
    """
    Index scikit-learn embedded chunks to OpenSearch
    
    This task:
    1. Connects to OpenSearch cluster
    2. Creates/recreates the index with sklearn-specific configuration
    3. Bulk indexes all embedded chunks
    4. Returns indexing statistics
    
    Args:
        embedded_chunks_file: Path to embedded chunks JSON file
        index_name: Name of OpenSearch index (uses config default if None)
    
    Returns:
        dict: Indexing statistics
    """
    try:
        # Use default index name from config if not provided
        index_name = index_name or INDEX_NAME
        
        logging.info(f"Connecting to OpenSearch at {OPENSEARCH_HOST}")
        
        # Connect to OpenSearch
        client, health = connect_to_opensearch(
            OPENSEARCH_HOST,
            OPENSEARCH_USER,
            OPENSEARCH_PASS
        )
        
        logging.info(f"OpenSearch cluster health: {health['status']}")
        
        # Index chunks
        logging.info(f"Indexing chunks to index: {index_name}")
        total_indexed = index_chunks(
            chunks_embeddings_file=embedded_chunks_file,
            index_name=index_name,
            client=client,
            index_body=SKLEARN_INDEX_BODY
        )
        
        # Get detailed index stats
        stats = client.indices.stats(index=index_name)
        count = client.count(index=index_name)
        
        # Get mapping info
        mapping = client.indices.get_mapping(index=index_name)
        
        result = {
            'total_indexed': total_indexed,
            'index_name': index_name,
            'document_count': count['count'],
            'index_size_bytes': stats['_all']['total']['store']['size_in_bytes'],
            'index_size_mb': round(stats['_all']['total']['store']['size_in_bytes'] / (1024**2), 2),
            'segments_count': stats['_all']['total']['segments']['count'],
            'has_knn': 'knn' in str(mapping),
            'cluster_health': health['status']
        }
        
        logging.info(f"Indexing completed successfully: {result}")
        return result
        
    except Exception as e:
        logging.error(f"Indexing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise