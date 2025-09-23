"""
Unit tests for IngestionService.

Tests the ingestion service functionality including URL downloading,
content extraction, optimal chunking, and batch insertion.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from weaviate_mcp.services.ingestion_service import IngestionService
from weaviate_mcp.services.weaviate_service import WeaviateService


class TestIngestionService:
    """Test cases for IngestionService."""

    @pytest.fixture
    def mock_weaviate_service(self):
        """Create a mock WeaviateService."""
        service = MagicMock(spec=WeaviateService)
        service.batch_insert_objects = AsyncMock()
        return service

    @pytest.fixture
    def ingestion_service(self, mock_weaviate_service):
        """Create an IngestionService instance with mocked dependencies."""
        return IngestionService(mock_weaviate_service)

    def test_init(self, mock_weaviate_service):
        """Test IngestionService initialization."""
        service = IngestionService(mock_weaviate_service)
        assert service.weaviate_service == mock_weaviate_service
        assert service._encoding is not None

    @pytest.mark.asyncio
    async def test_ingest_from_url_success_html(self, ingestion_service, mock_weaviate_service):
        """Test successful URL ingestion with HTML content."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>This is the first paragraph of the test article.</p>
                <p>This is the second paragraph with more content to test chunking.</p>
            </article>
        </body>
        </html>
        """
        mock_response.headers = {"content-type": "text/html"}
        mock_response.status_code = 200
        mock_response.content = mock_response.text.encode()
        mock_response.raise_for_status = MagicMock()

        # Mock successful batch insertion
        mock_weaviate_service.batch_insert_objects.return_value = {
            "success": True,
            "inserted_ids": ["id1", "id2"],
            "count": 2,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ingestion_service.ingest_from_url(
                url="https://example.com/article",
                collection_name="test_collection",
                max_tokens_per_chunk=100,
            )

        assert result["success"] is True
        assert result["collection_name"] == "test_collection"
        assert result["source_url"] == "https://example.com/article"
        assert result["chunks_ingested"] > 0
        assert "metadata" in result
        assert result["metadata"]["title"] == "Test Article"

        # Verify batch_insert_objects was called
        mock_weaviate_service.batch_insert_objects.assert_called_once()
        call_args = mock_weaviate_service.batch_insert_objects.call_args
        assert call_args[1]["collection_name"] == "test_collection"
        assert len(call_args[1]["objects"]) > 0

    @pytest.mark.asyncio
    async def test_ingest_from_url_success_plain_text(self, ingestion_service, mock_weaviate_service):
        """Test successful URL ingestion with plain text content."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = "This is a plain text document with multiple sentences. " * 50
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.status_code = 200
        mock_response.content = mock_response.text.encode()
        mock_response.raise_for_status = MagicMock()

        # Mock successful batch insertion
        mock_weaviate_service.batch_insert_objects.return_value = {
            "success": True,
            "inserted_ids": ["id1", "id2", "id3"],
            "count": 3,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ingestion_service.ingest_from_url(
                url="https://example.com/document.txt",
                collection_name="test_collection",
                max_tokens_per_chunk=200,
            )

        assert result["success"] is True
        assert result["chunks_ingested"] > 0

    @pytest.mark.asyncio
    async def test_ingest_from_url_http_error(self, ingestion_service):
        """Test URL ingestion with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("HTTP 404 Not Found"))

            result = await ingestion_service.ingest_from_url(
                url="https://example.com/nonexistent",
                collection_name="test_collection",
            )

        assert result["error"] is True
        assert "HTTP 404 Not Found" in result["message"]

    @pytest.mark.asyncio
    async def test_ingest_from_url_empty_content(self, ingestion_service):
        """Test URL ingestion with empty content."""
        # Mock HTTP response with empty content
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ingestion_service.ingest_from_url(
                url="https://example.com/empty",
                collection_name="test_collection",
            )

        assert result["error"] is True
        assert "No meaningful content" in result["message"]

    @pytest.mark.asyncio
    async def test_ingest_from_url_batch_insert_error(self, ingestion_service, mock_weaviate_service):
        """Test URL ingestion with batch insertion error."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = "This is a longer test content for batch insertion error. " * 20
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.status_code = 200
        mock_response.content = mock_response.text.encode()
        mock_response.raise_for_status = MagicMock()

        # Mock failed batch insertion
        mock_weaviate_service.batch_insert_objects.return_value = {
            "error": True,
            "message": "Database connection failed",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ingestion_service.ingest_from_url(
                url="https://example.com/test",
                collection_name="test_collection",
            )

        assert result["error"] is True
        assert "Database connection failed" in result["message"]

    def test_create_optimal_chunks_basic(self, ingestion_service):
        """Test basic text chunking functionality."""
        text = "This is a test paragraph.\n\nThis is another paragraph with more content."

        chunks = ingestion_service._create_optimal_chunks(text, max_tokens=50, overlap_tokens=10)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(chunk.strip() for chunk in chunks)

    def test_create_optimal_chunks_empty_text(self, ingestion_service):
        """Test chunking with empty text."""
        chunks = ingestion_service._create_optimal_chunks("", max_tokens=100)
        assert chunks == []

        chunks = ingestion_service._create_optimal_chunks("   ", max_tokens=100)
        assert chunks == []

    def test_create_optimal_chunks_long_text(self, ingestion_service):
        """Test chunking with long text that requires multiple chunks."""
        # Create a long text with multiple paragraphs
        paragraphs = [f"This is paragraph {i} with some content." for i in range(20)]
        text = "\n\n".join(paragraphs)

        chunks = ingestion_service._create_optimal_chunks(text, max_tokens=100, overlap_tokens=20)

        assert len(chunks) > 1
        # Verify no chunk is too large (approximate check)
        for chunk in chunks:
            token_count = len(ingestion_service._encoding.encode(chunk))
            assert token_count <= 150  # Allow some buffer

    def test_extract_html_content(self, ingestion_service):
        """Test HTML content extraction."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
            <meta name="author" content="Test Author">
        </head>
        <body>
            <nav>Navigation</nav>
            <main>
                <h1>Main Content</h1>
                <p>This is the main content.</p>
            </main>
            <footer>Footer</footer>
        </body>
        </html>
        """

        content, metadata = ingestion_service._extract_html_content(html, "https://example.com")

        assert "Main Content" in content
        assert "This is the main content" in content
        assert "Navigation" not in content  # Should be removed
        assert "Footer" not in content  # Should be removed

        assert metadata["title"] == "Test Page"
        assert metadata["description"] == "Test description"
        assert metadata["author"] == "Test Author"

    def test_extract_title_from_url(self, ingestion_service):
        """Test title extraction from URL."""
        # Test with path
        title = ingestion_service._extract_title_from_url("https://example.com/my-article")
        assert title == "My Article"

        # Test with file extension
        title = ingestion_service._extract_title_from_url("https://example.com/document.pdf")
        assert title == "Document"

        # Test with no path
        title = ingestion_service._extract_title_from_url("https://example.com")
        assert title == "example.com"

    def test_split_into_sentences(self, ingestion_service):
        """Test sentence splitting functionality."""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        sentences = ingestion_service._split_into_sentences(text)

        assert len(sentences) == 4
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"
        assert sentences[2] == "Third sentence?"
        assert sentences[3] == "Fourth sentence."

    def test_get_overlap_text(self, ingestion_service):
        """Test overlap text generation."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        # Test with reasonable overlap
        overlap = ingestion_service._get_overlap_text(text, overlap_tokens=10)
        assert len(overlap) > 0
        assert overlap in text

        # Test with zero overlap
        overlap = ingestion_service._get_overlap_text(text, overlap_tokens=0)
        assert overlap == ""

        # Test with very large overlap
        overlap = ingestion_service._get_overlap_text(text, overlap_tokens=1000)
        assert len(overlap) > 0
