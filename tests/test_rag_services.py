import os
import sys

# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.rag.rag_service import RAGService  
from src.logger import logging

rag_service = RAGService()

import asyncio

async def main():
    rag_service = RAGService()

    result = await rag_service.execute_rag(
        user_message="How to perform PCA on images?",
        thread_id="thread-001",
        user_id="user-123"
    )

    logging.info(f"Final RAG Result:{result}")
    print(result)

# Run the async main
asyncio.run(main())
