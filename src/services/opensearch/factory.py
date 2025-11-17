# ===================================================================================
# Project: ChatSkLearn
# File: src/services/opensearch/factory.py
# Description: Connects to OpenSearch
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

import os
import sys
from opensearchpy import OpenSearch
from typing import Dict, Tuple, Any

# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)


from src.config import OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS
from src.logger import logging


def connect_to_opensearch(
    opensearch_host: str,
    opensearch_user: str,
    opensearch_pass: str
) -> Tuple[OpenSearch, Dict[str, Any]]:
    """
    Establish a connection to an OpenSearch cluster and verify its health.

    Args:
        opensearch_host (str): The OpenSearch host and port in the format "hostname:port".
        opensearch_user (str): Username for OpenSearch authentication.
        opensearch_pass (str): Password for OpenSearch authentication.

    Returns:
        Tuple[OpenSearch, Dict[str, Any]]:
            A tuple containing:
                - `OpenSearch`: The initialized OpenSearch client.
                - `Dict[str, Any]`: The cluster health response.

    Raises:
        ValueError: If the provided host string is invalid.
        Exception: If the connection to the OpenSearch cluster fails.

    Example:
        >>> client, health = connect_to_opensearch("localhost:9200", "admin", "admin")
        >>> print(health["status"])
        'green'
    """

    logging.info(f"Connecting to OpenSearch at {opensearch_host}")

    # Validate host string format
    if ':' not in opensearch_host:
        raise ValueError("Invalid host format. Expected 'hostname:port'.")

    host, port_str = opensearch_host.split(':', 1)
    try:
        port = int(port_str)
    except ValueError as e:
        raise ValueError(f"Invalid port value in host: {opensearch_host}") from e

    try:
        client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=(opensearch_user, opensearch_pass),
            use_ssl=False,
            verify_certs=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )

        # Check cluster health
        health: Dict[str, Any] = client.cluster.health()
        logging.info(f"OpenSearch cluster health: {health['status']}")

        return client, health

    except Exception as e:
        logging.error(f"Failed to connect to OpenSearch at {opensearch_host}: {e}")
        raise


# Example usage:
if __name__ == "__main__":
    client, health= connect_to_opensearch(OPENSEARCH_HOST, OPENSEARCH_USER, OPENSEARCH_PASS)