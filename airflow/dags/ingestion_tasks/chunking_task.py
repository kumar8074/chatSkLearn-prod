# ===================================================================================
# Project: ChatSkLearn
# File: airflow/dags/ingestion_tasks/chunking_task.py
# Description: Airflow TASK to load and intelligently chunk scikit-learn documentation content
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.0.0
# ===================================================================================

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '/opt/airflow')

from src.services.chunking.content_chunker import SkLearnContentLoader
from src.logger import logging


def chunk_sklearn_content(
    urls_file: str = "temp/successful_urls.txt",
    output_dir: str = "temp/sklearn_scraped_data",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_pages: int = None
) -> dict:
    """
    Load and chunk scikit-learn documentation content
    
    This task:
    1. Loads URLs from successful_urls.txt
    2. Fetches content from each URL
    3. Extracts and preserves code blocks
    4. Creates overlapping chunks
    5. Saves chunks as JSONL and JSON
    
    Args:
        urls_file: Path to file containing URLs to process
        output_dir: Output directory for chunks
        chunk_size: Size of text chunks in words
        chunk_overlap: Overlap between chunks in words
        max_pages: Maximum pages to process (None for all)
    
    Returns:
        dict: Statistics about chunking
    """
    try:
        logging.info(f"Starting content chunking from: {urls_file}")
        start_time = time.time()
        
        # Initialize content loader
        loader = SkLearnContentLoader(
            urls_file=urls_file,
            output_dir=output_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Process all URLs
        loader.process_all_urls(max_pages=max_pages)
        
        # Save data
        loader.save_data()
        
        duration = time.time() - start_time
        
        # Calculate statistics
        stats = {
            'total_pages': len(loader.crawled_data),
            'total_chunks': sum(p['total_chunks'] for p in loader.crawled_data),
            'total_words': sum(p['total_words'] for p in loader.crawled_data),
            'total_code_blocks': sum(p['total_code_blocks'] for p in loader.crawled_data),
            'failed_pages': len(loader.failed_pages),
            'avg_chunks_per_page': (
                sum(p['total_chunks'] for p in loader.crawled_data) / len(loader.crawled_data)
                if loader.crawled_data else 0
            ),
            'duration_seconds': round(duration, 2),
            'chunks_file': f"{output_dir}/chunks_for_rag.jsonl",
            'all_chunks_file': f"{output_dir}/all_chunks.json",
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        
        logging.info(f"Content chunking completed: {stats}")
        return stats
        
    except Exception as e:
        logging.error(f"Content chunking failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise