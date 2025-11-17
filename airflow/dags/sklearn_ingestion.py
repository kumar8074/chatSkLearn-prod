# ===================================================================================
# Project: ChatSkLearn
# File: airflow/dags/sklearn_ingestion.py
# Description: Main Airflow DAG for scikit-learn documentation ingestion
# Author: LALAN KUMAR
# Created: [02-11-2025]
# Updated: [02-11-2025]
# LAST MODIFIED BY: LALAN KUMAR
# Version: 1.0.0
# ===================================================================================

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.utils.timezone import make_aware
import pendulum
import sys

sys.path.insert(0, '/opt/airflow/dags')

from ingestion_tasks.scrapper_task import scrape_sklearn_urls
from ingestion_tasks.chunking_task import chunk_sklearn_content
from ingestion_tasks.embedding_task import generate_sklearn_embeddings
from ingestion_tasks.indexing_task import index_sklearn_to_opensearch

# Define IST timezone
ist = pendulum.timezone('Asia/Kolkata')

# Default arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
with DAG(
    'sklearn_documentation_ingestion',
    default_args=default_args,
    description='Ingest scikit-learn documentation into OpenSearch with embeddings',
    schedule_interval='0 23 27 * *',  # Run at 11:00 PM IST on 27th of every month (cron format)
    start_date=datetime(2025, 11, 1, tzinfo=ist),
    catchup=False,
    tags=['sklearn', 'documentation', 'rag', 'opensearch', 'monthly'],
) as dag:
    
    # Task 1: Crawl scikit-learn documentation URLs
    crawl_urls = PythonOperator(
        task_id='crawl_sklearn_urls',
        python_callable=scrape_sklearn_urls,
        op_kwargs={
            'base_url': 'https://scikit-learn.org/stable/',
            'output_dir': 'temp',
            'max_depth': 5,
            'max_pages': 10000,
            'concurrency': 25
        },
    )
    
    # Task 2: Chunk the documentation content
    chunk_content = PythonOperator(
        task_id='chunk_sklearn_content',
        python_callable=chunk_sklearn_content,
        op_kwargs={
            'urls_file': 'temp/successful_urls.txt',
            'output_dir': 'temp/sklearn_scraped_data',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'max_pages': None  # Process all pages
        },
    )
    
    # Task 3: Generate embeddings
    generate_embeddings_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_sklearn_embeddings,
        op_kwargs={
            'chunks_file': 'temp/sklearn_scraped_data/chunks_for_rag.jsonl',
            'output_file': 'temp/sklearn_scraped_data/embedded_chunks.json',
            'batch_size': 100
        },
    )
    
    # Task 4: Index to OpenSearch
    index_to_opensearch = PythonOperator(
        task_id='index_to_opensearch',
        python_callable=index_sklearn_to_opensearch,
        op_kwargs={
            'embedded_chunks_file': 'temp/sklearn_scraped_data/embedded_chunks.json',
            'index_name': 'sklearn_documentation'
        },
    )
    
    # Define task dependencies
    crawl_urls >> chunk_content >> generate_embeddings_task >> index_to_opensearch