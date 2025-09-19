"""
MCP server utilities for Google Workspace integration.
This file now contains utility functions, like parsing capabilities and environment config.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_weaviate_config():
    """
    Parse WEAVIATE_URL, WEAVIATE_HTTP_PORT, and WEAVIATE_GRPC_PORT from environment variables.

    Returns:
        dict: {
            "url": str or None,
            "http_port": int or None,
            "grpc_port": int or None
        }
    """
    url = os.environ.get("WEAVIATE_URL")
    http_port = os.environ.get("WEAVIATE_HTTP_PORT")
    grpc_port = os.environ.get("WEAVIATE_GRPC_PORT")

    def parse_port(port_str, var_name):
        if port_str is None:
            return None
        try:
            return int(port_str)
        except ValueError:
            logger.warning(f"Environment variable {var_name} is not a valid integer: {port_str}")
            return None

    http_port_int = parse_port(http_port, "WEAVIATE_HTTP_PORT")
    grpc_port_int = parse_port(grpc_port, "WEAVIATE_GRPC_PORT")

    config = {
        "url": url,
        "http_port": http_port_int,
        "grpc_port": grpc_port_int,
    }

    logger.info(f"Parsed Weaviate config from environment: {config}")
    return config
