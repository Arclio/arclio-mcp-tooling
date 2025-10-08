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
        f"Successfully retrieved text content for object '{key}' from bucket '{bucket_name}' ({result['size']} bytes)"
    )
    return result


@mcp.tool()
async def s3_count_objects(bucket_name: str, prefix: str = "") -> dict[str, Any]:
    """
    Count total number of objects in an S3 bucket.

    This tool efficiently counts all objects in a bucket (or with a specific prefix)
    without loading object content. Useful for understanding bucket size before
    processing or pagination.

    Args:
        bucket_name: The S3 bucket name
        prefix: Limits count to keys beginning with this prefix (default: "")

    Returns:
        Dictionary with:
        - count: Total number of objects
        - bucket_name: Echo of the bucket name
        - prefix: Echo of the prefix filter

    Raises:
        ValueError: If bucket doesn't exist or access is denied

    Examples:
        # Count all objects in bucket
        result = await s3_count_objects(bucket_name="my-pdfs")
        # Result: {"count": 1543, "bucket_name": "my-pdfs", "prefix": ""}

        # Count objects with specific prefix
        result = await s3_count_objects(
            bucket_name="my-pdfs",
            prefix="reports/"
        )
        # Result: {"count": 287, "bucket_name": "my-pdfs", "prefix": "reports/"}

    Use Cases:
        - Determine total files before starting batch processing
        - Calculate how many batches will be needed
        - Monitor bucket growth over time
        - Verify upload completion
    """
    logger.info(f"Counting objects in bucket '{bucket_name}' with prefix '{prefix}'")

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")

    # Call service layer
    result = await s3_service.count_objects(bucket_name, prefix)

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        logger.error(f"S3 count objects failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully counted {result['count']} objects in bucket '{bucket_name}'"
    )
    return result


@mcp.tool()
async def s3_list_objects_paginated(
    bucket_name: str,
    prefix: str = "",
    start_index: int = 0,
    batch_size: int = 100,
    continuation_token: str = "",
) -> dict[str, Any]:
    """
    List objects in S3 with user-friendly numeric index pagination.

    This tool provides INDEX-BASED pagination where you specify numeric indices
    (0, 100, 200) instead of filenames. Perfect for processing large buckets
    in manageable batches.

    KEY FEATURES:
    - 🎯 Numeric indices (0-99, 100-199, 200-299) - intuitive!
    - ✅ Consistent results (same indices = same files, if bucket unchanged)
    - 🚀 Efficient (only fetches requested batch)
    - 📦 No bucket size limit
    - 🔄 Deterministic (no LLM needed)

    Args:
        bucket_name: The S3 bucket name
        prefix: Limits response to keys beginning with this prefix (default: "")
        start_index: Zero-based index to start from - use 0, 100, 200, etc.
        batch_size: Number of objects to return per batch (default: 100)
        continuation_token: Opaque token from previous call (default: "")
                           Copy this from the previous response's continuation_token

    Returns:
        Dictionary with:
        - objects: Array of object metadata (key, size, last_modified, etag)
        - keys: Convenience array of just the file keys
        - count: Number of objects in THIS batch
        - start_index: Index this batch started at (echoed from input)
        - next_start_index: Index for next batch (start_index + batch_size)
        - has_more: True if more objects exist beyond this batch
        - continuation_token: Opaque token to pass to next call

    Raises:
        ValueError: If bucket doesn't exist or access is denied

    Examples:
        # First batch: Get files 0-99
        batch1 = await s3_list_objects_paginated(
            bucket_name="my-pdfs",
            start_index=0,
            batch_size=100
        )
        # Result: {
        #   "keys": ["doc_000.pdf", ..., "doc_099.pdf"],
        #   "count": 100,
        #   "start_index": 0,
        #   "next_start_index": 100,
        #   "has_more": True,
        #   "continuation_token": "eyJsYXN0X2tl...="
        # }

        # Second batch: Get files 100-199
        batch2 = await s3_list_objects_paginated(
            bucket_name="my-pdfs",
            start_index=100,  # Simple numeric index!
            batch_size=100,
            continuation_token=batch1["continuation_token"]  # Copy from previous
        )
        # Result: {
        #   "keys": ["doc_100.pdf", ..., "doc_199.pdf"],
        #   "start_index": 100,
        #   "next_start_index": 200,
        #   ...
        # }

    Workflow Usage:
        1. Run with start_index=0 (no token needed)
        2. Process the returned files
        3. If has_more=True, run again with:
           - start_index = previous next_start_index
           - continuation_token = previous continuation_token
        4. Repeat until has_more=False

    Consistency Guarantee:
        As long as no files are added/removed between calls, the same start_index
        always returns the same files (in alphabetical order by filename).

    Note:
        The continuation_token is an opaque string that internally stores the
        last filename. You don't need to understand it - just copy it from the
        previous response.
    """
    logger.info(
        f"Listing objects (paginated) in bucket '{bucket_name}' start_index={start_index}, batch_size={batch_size}"
    )

    # Validate inputs
    if not bucket_name or not isinstance(bucket_name, str):
        raise ValueError("bucket_name must be a non-empty string")

    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")

    if not isinstance(start_index, int) or start_index < 0:
        raise ValueError("start_index must be a non-negative integer")

    if not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    if not isinstance(continuation_token, str):
        raise ValueError("continuation_token must be a string")

    # Call service layer
    result = await s3_service.list_objects_paginated(
        bucket_name, prefix, start_index, batch_size, continuation_token
    )

    # Handle service errors by raising ValueError for MCP
    if result.get("error"):
        error_message = result.get("message", "Unknown error occurred")
        logger.error(f"S3 list objects paginated failed: {error_message}")
        raise ValueError(error_message)

    logger.info(
        f"Successfully listed {result['count']} objects from bucket '{bucket_name}' "
        f"(start_index={start_index}, has_more={result['has_more']})"
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
