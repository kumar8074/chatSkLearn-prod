# ===================================================================================
# Project: ChatSkLearn
# File: airflow/dags/ingestion_tasks/embedding_task.py
# Description: Airflow TASK to generate embeddings for scikit-learn chunks
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.1.0
# ===================================================================================

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '/opt/airflow')

from src.services.embedding.embedding_service import (
    load_chunks,
    generate_embeddings,
    combine_chunks_embeddings
)
from src.config import EMBEDDING_MODEL
from src.logger import logging


def generate_sklearn_embeddings(
    chunks_file: str = "temp/sklearn_scraped_data/chunks_for_rag.jsonl",
    output_file: str = "temp/sklearn_scraped_data/embedded_chunks.json",
    batch_size: int = 100
) -> dict:
    """
    Generate embeddings for scikit-learn documentation chunks
    
    This task:
    1. Loads chunks from JSONL file
    2. Generates embeddings for 'enriched_text' field using Google Gemini
    3. Combines embeddings with chunks
    4. Saves to JSON file
    
    Args:
        chunks_file: Path to chunks JSONL file
        output_file: Path to output file for embedded chunks
        batch_size: Batch size for embedding generation
    
    Returns:
        dict: Statistics about embedding generation
    """
    try:
        logging.info(f"Loading chunks from: {chunks_file}")
        
        # Load chunks using the service function
        chunks = load_chunks(chunks_file)
        
        logging.info(f"Loaded {len(chunks)} chunks")
        
        # Generate embeddings
        logging.info(f"Generating embeddings using {EMBEDDING_MODEL}")
        embeddings = generate_embeddings(
            chunks=chunks,
            batch_size=batch_size,
            client=EMBEDDING_MODEL
        )
        
        logging.info(f"Generated {len(embeddings)} embeddings")
        
        # Combine and save
        logging.info(f"Saving embedded chunks to: {output_file}")
        combine_chunks_embeddings(
            chunks=chunks,
            embeddings=embeddings,
            output_file_path=output_file
        )
        
        # Calculate statistics
        stats = {
            'total_chunks': len(chunks),
            'embedding_dimension': len(embeddings[0]) if embeddings else 0,
            'chunks_with_code': sum(1 for c in chunks if c.get('has_code', False)),
            'total_code_blocks': sum(len(c.get('code_blocks', [])) for c in chunks),
            'output_file': output_file,
            'batch_size': batch_size
        }
        
        logging.info(f"Embedding generation completed: {stats}")
        return stats
        
    except Exception as e:
        logging.error(f"Embedding generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise