"""
Data ingestion tools for Weaviate operations.

This module provides tools for ingesting content from various sources
into Weaviate collections with optimal chunking and processing.
"""

import logging
from typing import Any

from ..app import mcp  # Import from central app module
from ..services.ingestion_service import IngestionService
from ..services.weaviate_service import WeaviateService

logger = logging.getLogger(__name__)


# --- Data Ingestion Tool Functions --- #


@mcp.tool(
    name="weaviate_ingest_from_url",
    description="Download, chunk, and ingest large documents from URLs into Weaviate for semantic search. Handles HTML, text, and JSON content with intelligent chunking.",
)
async def weaviate_ingest_from_url(
    url: str,
    collection_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    max_tokens_per_chunk: int = 500,
) -> dict[str, Any]:
    """
    Ingest and vectorize content from a public URL into a Weaviate collection.

    This tool downloads content from a URL, processes it using optimal chunking
    strategies (token-aware semantic splitting), and inserts the chunks into
    the specified Weaviate collection. The operation is synchronous and blocks
    until the entire ingestion process is complete.

    Args:
        url: Public URL to ingest content from (supports HTML, text, JSON)
        collection_name: Name of the target Weaviate collection
        chunk_size: Target character count per chunk (fallback, default: 1000)
        chunk_overlap: Character overlap between chunks (default: 100)
        max_tokens_per_chunk: Maximum tokens per chunk using GPT-4 tokenizer (default: 500)

    Returns:
        Dictionary with ingestion results including:
        - success: Boolean indicating success
        - chunks_ingested: Number of chunks created and inserted
        - collection_name: Target collection name
        - source_url: Source URL
        - inserted_ids: List of inserted object IDs
        - metadata: Extracted metadata (title, description, etc.)

    Raises:
        ValueError: If the ingestion process fails

    Example:
        ```python
        result = await weaviate_ingest_from_url(
            url="https://example.com/article",
            collection_name="Documents",
            max_tokens_per_chunk=400,
            chunk_overlap=50
        )

        if result["success"]:
            print(f"Ingested {result['chunks_ingested']} chunks")
        ```

    Features:
        - Automatic content type detection (HTML, text, JSON)
        - HTML content extraction with metadata (title, description, author)
        - Token-aware chunking using tiktoken for optimal context preservation
        - Semantic boundary detection (paragraphs, sentences)
        - Duplicate prevention using source_url and chunk_index
        - Comprehensive error handling and logging
        - Batch insertion for performance
    """
    try:
        logger.info(f"Starting URL ingestion: {url} -> {collection_name}")

        # Validate inputs
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        if not collection_name or not collection_name.strip():
            raise ValueError("Collection name cannot be empty")

        if max_tokens_per_chunk <= 0:
            raise ValueError("max_tokens_per_chunk must be positive")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")

        # Initialize services
        weaviate_service = WeaviateService()
        ingestion_service = IngestionService(weaviate_service)

        # Perform synchronous ingestion
        result = await ingestion_service.ingest_from_url(
            url=url.strip(),
            collection_name=collection_name.strip(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_tokens_per_chunk=max_tokens_per_chunk,
        )

        # Check for errors and raise ValueError if needed
        if result.get("error"):
            error_message = result.get("message", "Unknown ingestion error")
            logger.error(f"Ingestion failed: {error_message}")
            raise ValueError(f"Ingestion failed: {error_message}")

        logger.info(
            f"Successfully ingested {result.get('chunks_ingested', 0)} chunks from {url} into collection '{collection_name}'"
        )

        return result

    except ValueError:
        # Re-raise ValueError as expected by MCP error handling pattern
        raise
    except Exception as e:
        logger.error(f"Unexpected error in weaviate_ingest_from_url: {e}")
        raise ValueError(f"Ingestion error: {str(e)}") from e


@mcp.tool(
    name="weaviate_ingest_text_content",
    description="Process and ingest large text content directly into Weaviate with intelligent chunking. Ideal for books, articles, and long documents.",
)
async def weaviate_ingest_text_content(
    content: str,
    collection_name: str,
    source_identifier: str,
    title: str | None = None,
    max_tokens_per_chunk: int = 500,
    chunk_overlap: int = 50,
) -> dict[str, Any]:
    """
    Ingest raw text content directly into a Weaviate collection.

    This tool processes raw text content using optimal chunking strategies
    and inserts the chunks into the specified Weaviate collection.

    Args:
        content: Raw text content to ingest
        collection_name: Name of the target Weaviate collection
        source_identifier: Unique identifier for the content source
        title: Optional title for the content
        max_tokens_per_chunk: Maximum tokens per chunk (default: 500)
        chunk_overlap: Token overlap between chunks (default: 50)

    Returns:
        Dictionary with ingestion results

    Raises:
        ValueError: If the ingestion process fails

    Example:
        ```python
        result = await weaviate_ingest_text_content(
            content="Long text content...",
            collection_name="Documents",
            source_identifier="manual_input_001",
            title="My Document",
            max_tokens_per_chunk=400
        )
        ```
    """
    try:
        logger.info(
            f"Starting text content ingestion: {source_identifier} -> {collection_name}"
        )

        # Validate inputs
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        if not collection_name or not collection_name.strip():
            raise ValueError("Collection name cannot be empty")

        if not source_identifier or not source_identifier.strip():
            raise ValueError("Source identifier cannot be empty")

        if max_tokens_per_chunk <= 0:
            raise ValueError("max_tokens_per_chunk must be positive")

        # Initialize services
        weaviate_service = WeaviateService()
        ingestion_service = IngestionService(weaviate_service)

        # Create chunks using the optimal chunking method
        chunks = ingestion_service._create_optimal_chunks(
            content.strip(),
            max_tokens=max_tokens_per_chunk,
            overlap_tokens=chunk_overlap,
        )

        if not chunks:
            raise ValueError("No content chunks were created from the input text")

        logger.info(f"Created {len(chunks)} chunks from text content")

        # Prepare objects for Weaviate insertion
        objects = []
        for i, chunk in enumerate(chunks):
            obj = {
                "content": chunk,
                "source_url": source_identifier,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_type": "text/plain",
                "title": title or f"Text Content {source_identifier}",
            }
            objects.append(obj)

        # Batch insert into Weaviate
        insert_result = await weaviate_service.batch_insert_objects(
            collection_name=collection_name.strip(),
            objects=objects,
            unique_properties=["source_url", "chunk_index"],
            batch_size=50,
        )

        if insert_result.get("error"):
            error_message = insert_result.get("message", "Unknown insertion error")
            logger.error(f"Batch insertion failed: {error_message}")
            raise ValueError(f"Insertion failed: {error_message}")

        logger.info(
            f"Successfully ingested {len(chunks)} chunks "
            f"from text content '{source_identifier}' into collection '{collection_name}'"
        )

        return {
            "success": True,
            "chunks_ingested": len(chunks),
            "collection_name": collection_name,
            "source_identifier": source_identifier,
            "inserted_ids": insert_result.get("inserted_ids", []),
            "title": title or f"Text Content {source_identifier}",
        }

    except ValueError:
        # Re-raise ValueError as expected by MCP error handling pattern
        raise
    except Exception as e:
        logger.error(f"Unexpected error in weaviate_ingest_text_content: {e}")
        raise ValueError(f"Text ingestion error: {str(e)}") from e
