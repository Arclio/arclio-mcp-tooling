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


@mcp.tool()
async def s3_get_text_content(bucket_name: str, key: str) -> dict[str, Any]:
    """
    Retrieve the text content of a specific object from S3 (text files only).

    This tool is specifically designed for text file retrieval and will fail
    for binary files (PDFs, images, etc.). Use this when you need plain text
    content for processing, such as ingesting into vector databases.

    Args:
        bucket_name: The S3 bucket name
        key: The full key path of the object (e.g., 'documents/article.txt')

    Returns:
        Dictionary with 'content', 'mime_type', and 'size'
        - content: UTF-8 decoded text content (always a string, never base64)
        - mime_type: Detected MIME type (e.g., 'text/plain', 'text/markdown')
        - size: Size of the object in bytes

    Raises:
        ValueError: If the file is not a text file or cannot be decoded as UTF-8

    Examples:
        # Get text file content
        result = await s3_get_text_content(
            bucket_name="my-bucket",
            key="documents/article.txt"
        )
        print(result["content"])  # Prints the actual text

        # For binary files, use s3_get_object_content instead
    """
    logger.info(f"Getting text content for object '{key}' from bucket '{bucket_name}'")

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not key or not isinstance(key, str):
        raise ValueError("key must be a non-empty string")

    # Call service layer
    result = await s3_service.get_text_content(bucket_name, key)

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        details = result.get("details", {})

        # Provide helpful context for common errors
        if (
            "not a text file" in error_message
            or "could not be decoded" in error_message
        ):
            suggestion = details.get("suggestion", "")
            logger.error(f"S3 get text content failed: {error_message}. {suggestion}")
            raise ValueError(f"{error_message}. {suggestion}")
        logger.error(f"S3 get text content failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully retrieved text content for object '{key}' from bucket '{bucket_name}' "
        f"({result['size']} bytes)"
    )
    return result


@mcp.tool()
async def s3_extract_pdf_text(bucket_name: str, key: str) -> dict[str, Any]:
    """
    Extract text content from a PDF file in S3.

    This tool downloads a PDF document from S3 and extracts all text content.
    Use this for processing PDF documents for text analysis, search indexing,
    or ingestion into vector databases like Weaviate.

    Args:
        bucket_name: The S3 bucket name
        key: The full key path of the PDF file (e.g., 'documents/report.pdf')

    Returns:
        Dictionary with 'text', 'page_count', and 'size'
        - text: Extracted text content from all pages
        - page_count: Number of pages in the PDF
        - size: Size of the PDF file in bytes

    Raises:
        ValueError: If the file is not a valid PDF, empty, or extraction fails

    Examples:
        # Extract text from a PDF for analysis
        result = await s3_extract_pdf_text(
            bucket_name="my-bucket",
            key="research/paper.pdf"
        )
        print(f"Extracted {len(result['text'])} characters from {result['page_count']} pages")

        # Use with Weaviate ingestion
        pdf_text = await s3_extract_pdf_text(
            bucket_name="documents",
            key="reports/annual-report-2024.pdf"
        )
        await weaviate_ingest_text_content(
            collection_name="Documents",
            content=pdf_text["text"],
            source_identifier=key
        )

    Note:
        - This tool extracts text from text-based PDFs only
        - For scanned PDFs (images), OCR would be required
        - Large PDFs may take longer to process
    """
    logger.info(f"Extracting PDF text from object '{key}' in bucket '{bucket_name}'")

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not key or not isinstance(key, str):
        raise ValueError("key must be a non-empty string")

    # Call service layer
    result = await s3_service.extract_pdf_text(bucket_name, key)

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        details = result.get("details", {})

        # Provide helpful context for common errors
        if (
            "does not appear to be a valid PDF" in error_message
            or "appears to be empty" in error_message
            or "Failed to parse PDF" in error_message
        ):
            suggestion = details.get("suggestion", "")
            logger.error(f"S3 PDF extraction failed: {error_message}. {suggestion}")
            raise ValueError(f"{error_message}. {suggestion}")
        logger.error(f"S3 PDF extraction failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully extracted text from PDF '{key}' in bucket '{bucket_name}' "
        f"({result['page_count']} pages, {len(result['text'])} characters)"
    )
    return result
