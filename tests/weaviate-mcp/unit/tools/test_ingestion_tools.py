"""
Unit tests for ingestion tools.

Tests the MCP tool layer for data ingestion functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weaviate_mcp.tools.ingestion_tools import (
    weaviate_ingest_from_url,
    weaviate_ingest_text_content,
)


class TestIngestionTools:
    """Test cases for ingestion MCP tools."""

    @pytest.mark.asyncio
    async def test_weaviate_ingest_from_url_success(self):
        """Test successful URL ingestion tool."""
        # Mock the ingestion service result
        mock_result = {
            "success": True,
            "chunks_ingested": 3,
            "collection_name": "test_collection",
            "source_url": "https://example.com/article",
            "inserted_ids": ["id1", "id2", "id3"],
            "metadata": {"title": "Test Article", "content_type": "text/html"},
        }

        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService"),
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_from_url = AsyncMock(return_value=mock_result)
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool
            result = await weaviate_ingest_from_url(
                url="https://example.com/article",
                collection_name="test_collection",
                max_tokens_per_chunk=400,
                chunk_overlap=50,
            )

            # Verify result
            assert result == mock_result
            assert result["success"] is True
            assert result["chunks_ingested"] == 3

            # Verify service calls
            mock_ingestion_service.assert_called_once()
            mock_ingestion_instance.ingest_from_url.assert_called_once_with(
                url="https://example.com/article",
                collection_name="test_collection",
                chunk_size=1000,  # default value
                chunk_overlap=50,
                max_tokens_per_chunk=400,
            )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_from_url_service_error(self):
        """Test URL ingestion tool with service error."""
        # Mock the ingestion service error
        mock_result = {
            "error": True,
            "message": "Failed to download content from URL",
        }

        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService"),
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_from_url = AsyncMock(return_value=mock_result)
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool and expect ValueError
            with pytest.raises(ValueError, match="Failed to download content from URL"):
                await weaviate_ingest_from_url(
                    url="https://example.com/nonexistent",
                    collection_name="test_collection",
                )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_from_url_validation_errors(self):
        """Test URL ingestion tool input validation."""
        # Test empty URL
        with pytest.raises(ValueError, match="URL cannot be empty"):
            await weaviate_ingest_from_url(
                url="",
                collection_name="test_collection",
            )

        # Test empty collection name
        with pytest.raises(ValueError, match="Collection name cannot be empty"):
            await weaviate_ingest_from_url(
                url="https://example.com/article",
                collection_name="",
            )

        # Test invalid max_tokens_per_chunk
        with pytest.raises(ValueError, match="max_tokens_per_chunk must be positive"):
            await weaviate_ingest_from_url(
                url="https://example.com/article",
                collection_name="test_collection",
                max_tokens_per_chunk=0,
            )

        # Test negative chunk_overlap
        with pytest.raises(ValueError, match="chunk_overlap cannot be negative"):
            await weaviate_ingest_from_url(
                url="https://example.com/article",
                collection_name="test_collection",
                chunk_overlap=-1,
            )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_from_url_unexpected_error(self):
        """Test URL ingestion tool with unexpected error."""
        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService"),
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks to raise unexpected error
            mock_ingestion_service.side_effect = RuntimeError("Unexpected error")

            # Call the tool and expect ValueError with wrapped error
            with pytest.raises(ValueError, match="Ingestion error: Unexpected error"):
                await weaviate_ingest_from_url(
                    url="https://example.com/article",
                    collection_name="test_collection",
                )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_text_content_success(self):
        """Test successful text content ingestion tool."""
        # Mock the batch insertion result
        mock_batch_result = {
            "success": True,
            "inserted_ids": ["id1", "id2"],
            "count": 2,
        }

        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService") as mock_weaviate_service,
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_weaviate_instance = MagicMock()
            mock_weaviate_instance.batch_insert_objects = AsyncMock(return_value=mock_batch_result)
            mock_weaviate_service.return_value = mock_weaviate_instance

            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance._create_optimal_chunks = MagicMock(return_value=["Chunk 1 content", "Chunk 2 content"])
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool
            result = await weaviate_ingest_text_content(
                content="This is a long text content that will be chunked into multiple pieces.",
                collection_name="test_collection",
                source_identifier="manual_input_001",
                title="Test Document",
                max_tokens_per_chunk=400,
            )

            # Verify result
            assert result["success"] is True
            assert result["chunks_ingested"] == 2
            assert result["collection_name"] == "test_collection"
            assert result["source_identifier"] == "manual_input_001"
            assert result["title"] == "Test Document"

            # Verify service calls
            mock_weaviate_instance.batch_insert_objects.assert_called_once()
            call_args = mock_weaviate_instance.batch_insert_objects.call_args
            assert call_args[1]["collection_name"] == "test_collection"
            assert len(call_args[1]["objects"]) == 2

    @pytest.mark.asyncio
    async def test_weaviate_ingest_text_content_validation_errors(self):
        """Test text content ingestion tool input validation."""
        # Test empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await weaviate_ingest_text_content(
                content="",
                collection_name="test_collection",
                source_identifier="test_001",
            )

        # Test empty collection name
        with pytest.raises(ValueError, match="Collection name cannot be empty"):
            await weaviate_ingest_text_content(
                content="Test content",
                collection_name="",
                source_identifier="test_001",
            )

        # Test empty source identifier
        with pytest.raises(ValueError, match="Source identifier cannot be empty"):
            await weaviate_ingest_text_content(
                content="Test content",
                collection_name="test_collection",
                source_identifier="",
            )

        # Test invalid max_tokens_per_chunk
        with pytest.raises(ValueError, match="max_tokens_per_chunk must be positive"):
            await weaviate_ingest_text_content(
                content="Test content",
                collection_name="test_collection",
                source_identifier="test_001",
                max_tokens_per_chunk=0,
            )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_text_content_no_chunks_created(self):
        """Test text content ingestion when no chunks are created."""
        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService"),
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance._create_optimal_chunks = MagicMock(return_value=[])
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool and expect ValueError
            with pytest.raises(ValueError, match="No content chunks were created"):
                await weaviate_ingest_text_content(
                    content="Short",
                    collection_name="test_collection",
                    source_identifier="test_001",
                )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_text_content_batch_insert_error(self):
        """Test text content ingestion with batch insertion error."""
        # Mock the batch insertion error
        mock_batch_result = {
            "error": True,
            "message": "Database connection failed",
        }

        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService") as mock_weaviate_service,
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_weaviate_instance = MagicMock()
            mock_weaviate_instance.batch_insert_objects = AsyncMock(return_value=mock_batch_result)
            mock_weaviate_service.return_value = mock_weaviate_instance

            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance._create_optimal_chunks = MagicMock(return_value=["Chunk 1 content"])
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool and expect ValueError
            with pytest.raises(ValueError, match="Database connection failed"):
                await weaviate_ingest_text_content(
                    content="Test content for batch insertion error.",
                    collection_name="test_collection",
                    source_identifier="test_001",
                )

    @pytest.mark.asyncio
    async def test_weaviate_ingest_text_content_default_title(self):
        """Test text content ingestion with default title generation."""
        # Mock the batch insertion result
        mock_batch_result = {
            "success": True,
            "inserted_ids": ["id1"],
            "count": 1,
        }

        with (
            patch("weaviate_mcp.tools.ingestion_tools.WeaviateService") as mock_weaviate_service,
            patch("weaviate_mcp.tools.ingestion_tools.IngestionService") as mock_ingestion_service,
        ):
            # Setup mocks
            mock_weaviate_instance = MagicMock()
            mock_weaviate_instance.batch_insert_objects = AsyncMock(return_value=mock_batch_result)
            mock_weaviate_service.return_value = mock_weaviate_instance

            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance._create_optimal_chunks = MagicMock(return_value=["Single chunk content"])
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool without title
            result = await weaviate_ingest_text_content(
                content="Test content without title.",
                collection_name="test_collection",
                source_identifier="manual_input_123",
            )

            # Verify default title is generated
            assert result["title"] == "Text Content manual_input_123"

            # Verify the object has the correct title
            call_args = mock_weaviate_instance.batch_insert_objects.call_args
            objects = call_args[1]["objects"]
            assert objects[0]["title"] == "Text Content manual_input_123"
