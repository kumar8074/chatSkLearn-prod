# ===================================================================================
# Project: ChatSkLearn
# File: src/services/indexing/opensearch_indexer.py
# Description: Indexes documents into OpenSearch for efficient retrieval
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

from opensearchpy import OpenSearch, helpers
from tenacity import retry, stop_after_attempt, wait_exponential
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.logger import logging
from src.services.indexing.index_config import SKLEARN_INDEX_BODY


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def index_chunks(
    chunks_embeddings_file: str | Path,
    index_name: str,
    client: OpenSearch,
    index_body: Dict[str, Any]
) -> int:
    """
    Load precomputed chunk embeddings from a JSON file and bulk-index them into OpenSearch.

    Args:
        chunks_embeddings_file (str | Path): Path to the JSON file containing chunks with embeddings.
        index_name (str): Name of the OpenSearch index to create or overwrite.
        client (OpenSearch): An active OpenSearch client instance.
        index_body (Dict[str, Any]): Index mapping and settings configuration.

    Returns:
        int: Number of chunks successfully indexed.

    Raises:
        FileNotFoundError: If the input embeddings file does not exist.
        ValueError: If no valid chunks are found to index.
        opensearchpy.OpenSearchException: If any OpenSearch operation fails.
    """
    file_path = Path(chunks_embeddings_file)
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} not found.")

    logging.info(f"Loading pre-embedded chunks from {file_path}")
    with file_path.open("r", encoding="utf-8") as f:
        chunks: List[Dict[str, Any]] = json.load(f)

    logging.info(f"Loaded {len(chunks)} chunks")

    # Prepare chunks for indexing
    for chunk in chunks:
        # Generate stable unique ID based on source_url and position
        hash_input = f"{chunk.get('source_url', '')}_{chunk.get('heading', '')}_{chunk.get('word_count', '')}"
        chunk["chunk_id"] = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        
        # Add indexed timestamp
        chunk["indexed_at"] = datetime.utcnow().isoformat()
        
        # Ensure all required fields exist with defaults
        chunk.setdefault("type", "content")
        chunk.setdefault("page_type", "documentation")
        chunk.setdefault("heading", "")
        chunk.setdefault("text", "")
        chunk.setdefault("full_text", chunk.get("text", ""))
        chunk.setdefault("enriched_text", "")
        chunk.setdefault("code_blocks", [])
        chunk.setdefault("has_code", False)
        chunk.setdefault("total_code_lines", 0)
        chunk.setdefault("source_url", "")
        chunk.setdefault("breadcrumbs", [])
        chunk.setdefault("metadata", {})
        chunk.setdefault("word_count", 0)

    # Delete existing index if it exists
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        logging.info(f"Deleted existing index: {index_name}")

    # Create a new index
    client.indices.create(index=index_name, body=index_body)
    logging.info(f"Created new index: {index_name}")

    # Prepare bulk actions
    actions = []
    skipped = 0
    
    for chunk in chunks:
        if not chunk.get("embedding"):
            logging.warning(f"Chunk {chunk.get('chunk_id')} missing embedding, skipping")
            skipped += 1
            continue
            
        actions.append({
            "_index": index_name,
            "_id": chunk["chunk_id"],
            "_source": chunk
        })

    if not actions:
        raise ValueError("No valid chunks to index (all missing embeddings).")

    logging.info(f"Indexing {len(actions)} chunks (skipped {skipped} without embeddings)")

    # Bulk index into OpenSearch
    success, failed = helpers.bulk(
        client,
        actions,
        chunk_size=100,
        request_timeout=60,
        raise_on_error=False
    )

    logging.info(f"Bulk indexed: {success} successful, {failed} failed")
    
    # Refresh index to make documents searchable
    client.indices.refresh(index=index_name)
    
    # Get index stats
    stats = client.indices.stats(index=index_name)
    count = client.count(index=index_name)
    
    logging.info(f"✅ Index stats:")
    logging.info(f"   - Total documents: {count['count']}")
    logging.info(f"   - Index size: {stats['_all']['total']['store']['size_in_bytes'] / (1024**2):.2f} MB")
    logging.info(f"   - Documents with code: {sum(1 for c in chunks if c.get('has_code'))}")

    return len(actions)

