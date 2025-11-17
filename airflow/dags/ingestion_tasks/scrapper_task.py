# ===================================================================================
# Project: ChatSkLearn
# File: airflow/dags/ingestion_tasks/scraper_task.py
# Description: Airflow TASK to scrape scikit-learn website
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.0.0
# ===================================================================================

import asyncio
from pathlib import Path
import sys
import traceback

# Add src to path for imports
sys.path.insert(0, '/opt/airflow')

from src.services.scrapper.sklearn_scraper import DocCrawlerAgent
from src.logger import logging

def scrape_sklearn_urls(
    base_url: str = "https://scikit-learn.org/stable/",
    output_dir: str = "temp",
    max_depth: int = 5,
    max_pages: int = 10000,
    concurrency: int = 25
) -> dict:
    """
    Scrape scikit-learn documentation URLs
    
    Args:
        base_url: Base URL for scikit-learn documentation
        output_dir: Output directory for URLs
        max_depth: Maximum crawl depth
        max_pages: Maximum pages to crawl
        concurrency: Number of concurrent requests
    
    Returns:
        dict: Statistics about the crawling run
    """
    try:
        logging.info(f"Starting URL crawl: {base_url}")
        
        # Initialize crawler
        agent = DocCrawlerAgent(
            base_url=base_url,
            max_depth=max_depth,
            max_pages=max_pages,
            concurrency=concurrency
        )
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the crawler
        loop.run_until_complete(agent.crawl())
        
        # Save results
        agent.save("sklearn_crawl_results.json")
        
        # Return statistics
        stats = {
            'total_urls': len(agent.results),
            'failed_urls': len(agent.failed),
            'visited_urls': len(agent.visited),
            'success_file': agent.success_file,
            'results_file': f"{output_dir}/sklearn_crawl_results.json"
        }
        
        logging.info(f"URL crawling completed: {stats}")
        return stats
        
    except Exception as e:
        logging.error(f"URL crawling failed: {str(e)}")
        traceback.print_exc()
        raise
    finally:
        # Clean up event loop
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as cleanup_error:
            logging.warning(f"Error during cleanup: {cleanup_error}")