"""
MCP tools for AWS S3 operations.

Implements high-level S3 tools following the specification in 02_TOOLS.md.
All tools use the @mcp.tool decorator and proper error handling.
"""

import logging
from typing import Any

from aws_s3_mcp.app import mcp
from aws_s3_mcp.services.s3_service import S3Service

logger = logging.getLogger(__name__)

# Initialize S3 service
s3_service = S3Service()


@mcp.tool()
async def s3_list_objects(
    bucket_name: str, prefix: str = "", max_keys: int = 1000
) -> dict[str, Any]:
    """
    List objects within a specified S3 bucket.

    Args:
        bucket_name: The S3 bucket name
        prefix: Limits the response to keys that begin with this prefix (optional)
        max_keys: Maximum number of objects to return (default: 1000)

    Returns:
        Dictionary with 'count' and 'objects' list containing object metadata

    Raises:
        ValueError: If the service returns an error
    """
    logger.info(
        f"Listing objects in bucket '{bucket_name}' with prefix '{prefix}' (max: {max_keys})"
    )

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")

    if not isinstance(max_keys, int) or max_keys <= 0:
        raise ValueError("max_keys must be a positive integer")

    # Call service layer
    result = await s3_service.list_objects(bucket_name, prefix, max_keys)

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        logger.error(f"S3 list objects failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully listed {result['count']} objects from bucket '{bucket_name}'"
    )
    return result


@mcp.tool()
async def s3_get_object_content(bucket_name: str, key: str) -> dict[str, Any]:
    """
    Retrieve the content of a specific object from S3.

    Args:
        bucket_name: The S3 bucket name
        key: The full key path of the object (e.g., 'folder/file.pdf')

    Returns:
        Dictionary with 'content', 'mime_type', 'encoding', and 'size'
        - content: Raw string for text files, Base64 for binary files
        - mime_type: Inferred or provided MIME type
        - encoding: 'utf-8' for text, 'base64' for binary
        - size: Size of the object in bytes

    Raises:
        ValueError: If the service returns an error
    """
    logger.info(f"Getting content for object '{key}' from bucket '{bucket_name}'")

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not key or not isinstance(key, str):
        raise ValueError("key must be a non-empty string")

    # Call service layer
    result = await s3_service.get_object_content(bucket_name, key)

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        logger.error(f"S3 get object content failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully retrieved content for object '{key}' from bucket '{bucket_name}' "
        f"({result['size']} bytes, {result['encoding']} encoding)"
    )
    return result
