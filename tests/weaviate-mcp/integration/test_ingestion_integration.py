"""
Integration tests for ingestion functionality.

Tests the complete ingestion pipeline from URL to Weaviate storage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weaviate_mcp.services.ingestion_service import IngestionService
from weaviate_mcp.services.weaviate_service import WeaviateService
from weaviate_mcp.tools.ingestion_tools import (
    weaviate_ingest_from_url,
    weaviate_ingest_text_content,
)


class TestIngestionIntegration:
    """Integration test cases for the complete ingestion pipeline."""

    @pytest.fixture
    def mock_weaviate_service(self):
        """Create a mock WeaviateService for integration tests."""
        service = MagicMock(spec=WeaviateService)
        service.batch_insert_objects = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_end_to_end_url_ingestion_html(self, mock_weaviate_service):
        """Test complete URL ingestion pipeline with HTML content."""
        # Mock HTTP response with realistic HTML
        mock_response = MagicMock()
        mock_response.text = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Advanced AI Research Paper</title>
            <meta name="description" content="Latest research in artificial intelligence">
            <meta name="author" content="Dr. Jane Smith">
        </head>
        <body>
            <nav>Navigation menu</nav>
            <main>
                <article>
                    <h1>Advanced AI Research Paper</h1>
                    <p>Artificial intelligence has made significant strides in recent years,
                    particularly in the areas of machine learning and natural language processing.</p>

                    <h2>Introduction</h2>
                    <p>This paper explores the latest developments in AI research, focusing on
                    transformer architectures and their applications in various domains.</p>

                    <h2>Methodology</h2>
                    <p>Our research methodology involves comprehensive analysis of existing
                    literature, experimental validation, and performance benchmarking across
                    multiple datasets.</p>

                    <h2>Results</h2>
                    <p>The results demonstrate significant improvements in model performance,
                    with accuracy gains of up to 15% compared to previous state-of-the-art methods.</p>

                    <h2>Conclusion</h2>
                    <p>In conclusion, our research contributes to the advancement of AI technology
                    and opens new possibilities for future applications in various industries.</p>
                </article>
            </main>
            <footer>Copyright information</footer>
        </body>
        </html>
        """
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.status_code = 200
        mock_response.content = mock_response.text.encode()
        mock_response.raise_for_status = MagicMock()

        # Mock successful batch insertion
        mock_weaviate_service.batch_insert_objects.return_value = {
            "success": True,
            "inserted_ids": ["chunk_1", "chunk_2", "chunk_3", "chunk_4"],
            "count": 4,
        }

        # Create ingestion service
        ingestion_service = IngestionService(mock_weaviate_service)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Perform ingestion
            result = await ingestion_service.ingest_from_url(
                url="https://research.example.com/ai-paper",
                collection_name="research_papers",
                max_tokens_per_chunk=300,
                chunk_overlap=50,
            )

        # Verify successful ingestion
        assert result["success"] is True
        assert result["collection_name"] == "research_papers"
        assert result["source_url"] == "https://research.example.com/ai-paper"
        assert result["chunks_ingested"] > 0

        # Verify metadata extraction
        metadata = result["metadata"]
        assert metadata["title"] == "Advanced AI Research Paper"
        assert metadata["description"] == "Latest research in artificial intelligence"
        assert metadata["author"] == "Dr. Jane Smith"
        assert metadata["content_type"] == "text/html; charset=utf-8"

        # Verify batch insertion was called correctly
        mock_weaviate_service.batch_insert_objects.assert_called_once()
        call_args = mock_weaviate_service.batch_insert_objects.call_args

        assert call_args[1]["collection_name"] == "research_papers"
        objects = call_args[1]["objects"]
        assert len(objects) > 0

        # Verify object structure
        first_object = objects[0]
        assert "content" in first_object
        assert first_object["source_url"] == "https://research.example.com/ai-paper"
        assert first_object["chunk_index"] == 0
        assert first_object["total_chunks"] == len(objects)
        assert first_object["title"] == "Advanced AI Research Paper"
        assert first_object["author"] == "Dr. Jane Smith"

    @pytest.mark.asyncio
    async def test_end_to_end_url_ingestion_json(self, mock_weaviate_service):
        """Test complete URL ingestion pipeline with JSON content."""
        # Mock HTTP response with JSON data
        json_data = {
            "title": "API Documentation",
            "version": "1.0",
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "description": "Retrieve all users",
                },
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "description": "Retrieve a specific user by ID",
                },
            ],
            "authentication": {
                "type": "Bearer Token",
                "description": "Include Bearer token in Authorization header",
            },
        }

        mock_response = MagicMock()
        mock_response.json.return_value = json_data
        mock_response.text = '{"title": "API Documentation", "version": "1.0", ...}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.status_code = 200
        mock_response.content = mock_response.text.encode()
        mock_response.raise_for_status = MagicMock()

        # Mock successful batch insertion
        mock_weaviate_service.batch_insert_objects.return_value = {
            "success": True,
            "inserted_ids": ["json_chunk_1"],
            "count": 1,
        }

        # Create ingestion service
        ingestion_service = IngestionService(mock_weaviate_service)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            # Perform ingestion
            result = await ingestion_service.ingest_from_url(
                url="https://api.example.com/docs.json",
                collection_name="api_docs",
                max_tokens_per_chunk=500,
            )

        # Verify successful ingestion
        assert result["success"] is True
        assert result["collection_name"] == "api_docs"
        assert result["chunks_ingested"] > 0

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["content_type"] == "application/json"
        assert "Docs" in metadata["title"]  # Extracted from URL

    @pytest.mark.asyncio
    async def test_tool_integration_with_service_layer(self):
        """Test MCP tool integration with service layer."""
        # Mock the complete service chain
        mock_result = {
            "success": True,
            "chunks_ingested": 2,
            "collection_name": "integration_test",
            "source_url": "https://example.com/test",
            "inserted_ids": ["id1", "id2"],
            "metadata": {"title": "Test Document", "content_type": "text/plain"},
        }

        with (
            patch(
                "weaviate_mcp.tools.ingestion_tools.WeaviateService"
            ) as mock_weaviate_service,
            patch(
                "weaviate_mcp.tools.ingestion_tools.IngestionService"
            ) as mock_ingestion_service,
        ):

            # Setup service mocks
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_from_url = AsyncMock(
                return_value=mock_result
            )
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the MCP tool
            result = await weaviate_ingest_from_url(
                url="https://example.com/test",
                collection_name="integration_test",
                max_tokens_per_chunk=400,
                chunk_overlap=50,
            )

            # Verify the tool returns the service result
            assert result == mock_result

            # Verify proper service instantiation and method calls
            mock_weaviate_service.assert_called_once()
            mock_ingestion_service.assert_called_once()
            mock_ingestion_instance.ingest_from_url.assert_called_once_with(
                url="https://example.com/test",
                collection_name="integration_test",
                chunk_size=1000,
                chunk_overlap=50,
                max_tokens_per_chunk=400,
            )

    @pytest.mark.asyncio
    async def test_text_content_integration(self):
        """Test text content ingestion integration."""
        # Mock batch insertion
        mock_batch_result = {
            "success": True,
            "inserted_ids": ["text_id1", "text_id2", "text_id3"],
            "count": 3,
        }

        with (
            patch(
                "weaviate_mcp.tools.ingestion_tools.WeaviateService"
            ) as mock_weaviate_service,
            patch(
                "weaviate_mcp.tools.ingestion_tools.IngestionService"
            ) as mock_ingestion_service,
        ):

            # Setup mocks
            mock_weaviate_instance = MagicMock()
            mock_weaviate_instance.batch_insert_objects = AsyncMock(
                return_value=mock_batch_result
            )
            mock_weaviate_service.return_value = mock_weaviate_instance

            # Create realistic chunking behavior
            long_content = """
            This is a comprehensive document about machine learning algorithms.

            Machine learning is a subset of artificial intelligence that focuses on
            the development of algorithms that can learn and make decisions from data.

            There are several types of machine learning algorithms including supervised
            learning, unsupervised learning, and reinforcement learning.

            Supervised learning algorithms learn from labeled training data to make
            predictions on new, unseen data.

            Unsupervised learning algorithms find patterns in data without labeled examples.

            Reinforcement learning algorithms learn through interaction with an environment.
            """

            mock_ingestion_instance = MagicMock()
            # Simulate realistic chunking
            mock_chunks = [
                "This is a comprehensive document about machine learning algorithms. Machine learning is a subset of artificial intelligence that focuses on the development of algorithms that can learn and make decisions from data.",
                "There are several types of machine learning algorithms including supervised learning, unsupervised learning, and reinforcement learning. Supervised learning algorithms learn from labeled training data to make predictions on new, unseen data.",
                "Unsupervised learning algorithms find patterns in data without labeled examples. Reinforcement learning algorithms learn through interaction with an environment.",
            ]
            mock_ingestion_instance._create_optimal_chunks = MagicMock(
                return_value=mock_chunks
            )
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Call the tool
            result = await weaviate_ingest_text_content(
                content=long_content,
                collection_name="ml_documents",
                source_identifier="ml_guide_001",
                title="Machine Learning Guide",
                max_tokens_per_chunk=200,
                chunk_overlap=30,
            )

            # Verify successful integration
            assert result["success"] is True
            assert result["chunks_ingested"] == 3
            assert result["collection_name"] == "ml_documents"
            assert result["source_identifier"] == "ml_guide_001"
            assert result["title"] == "Machine Learning Guide"

            # Verify service interactions
            mock_weaviate_instance.batch_insert_objects.assert_called_once()
            call_args = mock_weaviate_instance.batch_insert_objects.call_args

            objects = call_args[1]["objects"]
            assert len(objects) == 3

            # Verify object structure for each chunk
            for i, obj in enumerate(objects):
                assert obj["content"] == mock_chunks[i]
                assert obj["source_url"] == "ml_guide_001"
                assert obj["chunk_index"] == i
                assert obj["total_chunks"] == 3
                assert obj["title"] == "Machine Learning Guide"
                assert obj["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_error_propagation_integration(self):
        """Test error propagation through the integration layers."""
        # Test service layer error propagation
        with (
            patch(
                "weaviate_mcp.tools.ingestion_tools.WeaviateService"
            ) as mock_weaviate_service,
            patch(
                "weaviate_mcp.tools.ingestion_tools.IngestionService"
            ) as mock_ingestion_service,
        ):

            # Setup service to return error
            mock_ingestion_instance = MagicMock()
            mock_ingestion_instance.ingest_from_url = AsyncMock(
                return_value={
                    "error": True,
                    "message": "Network timeout during download",
                }
            )
            mock_ingestion_service.return_value = mock_ingestion_instance

            # Verify error is properly propagated as ValueError
            with pytest.raises(ValueError, match="Network timeout during download"):
                await weaviate_ingest_from_url(
                    url="https://timeout.example.com/document",
                    collection_name="test_collection",
                )

        # Test unexpected exception propagation
        with patch(
            "weaviate_mcp.tools.ingestion_tools.WeaviateService"
        ) as mock_weaviate_service:
            # Setup service to raise unexpected exception
            mock_weaviate_service.side_effect = ConnectionError("Database unreachable")

            # Verify unexpected error is wrapped in ValueError
            with pytest.raises(
                ValueError, match="Ingestion error: Database unreachable"
            ):
                await weaviate_ingest_from_url(
                    url="https://example.com/document",
                    collection_name="test_collection",
                )
