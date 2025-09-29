"""
Main entry point for running the AWS S3 MCP server via python -m aws_s3_mcp
"""

import asyncio
import logging

from aws_s3_mcp.app import mcp  # Import instance from central location

# Import all tool modules that register components with the FastMCP instance
from aws_s3_mcp.tools import s3_tools  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Reduce noise from AWS libraries
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("aiobotocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("Starting AWS S3 MCP server...")
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        logger.info("Shutting down AWS S3 MCP server...")
    except Exception as e:
        logger.error(f"Failed to start AWS S3 MCP server: {e}")
        raise


if __name__ == "__main__":
    main()
