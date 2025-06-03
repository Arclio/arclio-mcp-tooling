"""
Unit tests for Google Docs tools.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.docs_tools import (
    docs_append_text,
    docs_batch_update,
    docs_create_document,
    docs_get_content_as_markdown,
    docs_get_document_metadata,
    docs_insert_text,
    docs_prepend_text,
)

pytestmark = pytest.mark.anyio


class TestDocsCreateDocumentTool:
    """Tests for the docs_create_document tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_create_document_success(self, mock_docs_service):
        """Test docs_create_document successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "title": "Test Document",
            "document_link": "https://docs.google.com/document/d/test_doc_123/edit",
        }
        mock_docs_service.create_document.return_value = mock_service_response

        args = {"title": "Test Document"}
        result = await docs_create_document(**args)

        mock_docs_service.create_document.assert_called_once_with(title="Test Document")
        assert result == mock_service_response

    async def test_create_document_empty_title(self, mock_docs_service):
        """Test docs_create_document with empty title."""
        with pytest.raises(ValueError, match="Document title cannot be empty"):
            await docs_create_document("")

        with pytest.raises(ValueError, match="Document title cannot be empty"):
            await docs_create_document("   ")

    async def test_create_document_service_error(self, mock_docs_service):
        """Test docs_create_document with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Insufficient permissions"}
        mock_docs_service.create_document.return_value = error_response

        with pytest.raises(ValueError, match="Insufficient permissions"):
            await docs_create_document("Failed Document")

    async def test_create_document_service_returns_none(self, mock_docs_service):
        """Test docs_create_document when service returns None."""
        # Mock service returning None
        mock_docs_service.create_document.return_value = None

        with pytest.raises(ValueError, match="Failed to create document"):
            await docs_create_document("Test Document")

    async def test_create_document_missing_document_id(self, mock_docs_service):
        """Test docs_create_document when service returns response without document_id."""
        # Mock service returning response without document_id
        mock_service_response = {"title": "Test Document"}
        mock_docs_service.create_document.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to create document"):
            await docs_create_document("Test Document")


class TestDocsGetDocumentMetadataTool:
    """Tests for the docs_get_document_metadata tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_document_metadata_success(self, mock_docs_service):
        """Test docs_get_document_metadata successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "title": "Test Document",
            "document_link": "https://docs.google.com/document/d/test_doc_123/edit",
        }
        mock_docs_service.get_document_metadata.return_value = mock_service_response

        args = {"document_id": "test_doc_123"}
        result = await docs_get_document_metadata(**args)

        mock_docs_service.get_document_metadata.assert_called_once_with(document_id="test_doc_123")
        assert result == mock_service_response

    async def test_get_document_metadata_empty_document_id(self, mock_docs_service):
        """Test docs_get_document_metadata with empty document_id."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_get_document_metadata("")

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_get_document_metadata("   ")

    async def test_get_document_metadata_service_error(self, mock_docs_service):
        """Test docs_get_document_metadata with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Document not found"}
        mock_docs_service.get_document_metadata.return_value = error_response

        with pytest.raises(ValueError, match="Document not found"):
            await docs_get_document_metadata("nonexistent_doc")

    async def test_get_document_metadata_service_returns_none(self, mock_docs_service):
        """Test docs_get_document_metadata when service returns None."""
        # Mock service returning None
        mock_docs_service.get_document_metadata.return_value = None

        with pytest.raises(ValueError, match="Failed to retrieve metadata"):
            await docs_get_document_metadata("test_doc_123")

    async def test_get_document_metadata_missing_document_id_in_response(self, mock_docs_service):
        """Test docs_get_document_metadata when service returns response without document_id."""
        # Mock service returning response without document_id
        mock_service_response = {"title": "Test Document"}
        mock_docs_service.get_document_metadata.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to retrieve metadata"):
            await docs_get_document_metadata("test_doc_123")


class TestDocsGetContentAsMarkdownTool:
    """Tests for the docs_get_content_as_markdown tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_content_as_markdown_success(self, mock_docs_service):
        """Test docs_get_content_as_markdown successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "markdown_content": "# Test Document\n\nThis is test content.",
        }
        mock_docs_service.get_document_content_as_markdown.return_value = mock_service_response

        args = {"document_id": "test_doc_123"}
        result = await docs_get_content_as_markdown(**args)

        mock_docs_service.get_document_content_as_markdown.assert_called_once_with(document_id="test_doc_123")
        assert result == mock_service_response

    async def test_get_content_as_markdown_empty_document_id(self, mock_docs_service):
        """Test docs_get_content_as_markdown with empty document_id."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_get_content_as_markdown("")

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_get_content_as_markdown("   ")

    async def test_get_content_as_markdown_service_error(self, mock_docs_service):
        """Test docs_get_content_as_markdown with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Permission denied"}
        mock_docs_service.get_document_content_as_markdown.return_value = error_response

        with pytest.raises(ValueError, match="Permission denied"):
            await docs_get_content_as_markdown("restricted_doc")

    async def test_get_content_as_markdown_service_returns_none(self, mock_docs_service):
        """Test docs_get_content_as_markdown when service returns None."""
        # Mock service returning None
        mock_docs_service.get_document_content_as_markdown.return_value = None

        with pytest.raises(ValueError, match="Failed to retrieve Markdown content"):
            await docs_get_content_as_markdown("test_doc_123")

    async def test_get_content_as_markdown_missing_content(self, mock_docs_service):
        """Test docs_get_content_as_markdown when service returns response without markdown_content."""
        # Mock service returning response without markdown_content
        mock_service_response = {"document_id": "test_doc_123"}
        mock_docs_service.get_document_content_as_markdown.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to retrieve Markdown content"):
            await docs_get_content_as_markdown("test_doc_123")


class TestDocsAppendTextTool:
    """Tests for the docs_append_text tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_append_text_success(self, mock_docs_service):
        """Test docs_append_text successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "append_text",
        }
        mock_docs_service.append_text.return_value = mock_service_response

        args = {
            "document_id": "test_doc_123",
            "text": "Appended text",
            "ensure_newline": True,
        }
        result = await docs_append_text(**args)

        mock_docs_service.append_text.assert_called_once_with(
            document_id="test_doc_123", text="Appended text", ensure_newline=True
        )
        assert result == mock_service_response

    async def test_append_text_default_ensure_newline(self, mock_docs_service):
        """Test docs_append_text with default ensure_newline value."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "append_text",
        }
        mock_docs_service.append_text.return_value = mock_service_response

        args = {"document_id": "test_doc_123", "text": "Appended text"}
        result = await docs_append_text(**args)

        mock_docs_service.append_text.assert_called_once_with(
            document_id="test_doc_123",
            text="Appended text",
            ensure_newline=True,  # Default value
        )
        assert result == mock_service_response

    async def test_append_text_empty_document_id(self, mock_docs_service):
        """Test docs_append_text with empty document_id."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_append_text("", "Some text")

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_append_text("   ", "Some text")

    async def test_append_text_empty_text_allowed(self, mock_docs_service):
        """Test docs_append_text with empty text (should be allowed)."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "append_text",
        }
        mock_docs_service.append_text.return_value = mock_service_response

        # Empty text should be allowed
        result = await docs_append_text("test_doc_123", "")
        mock_docs_service.append_text.assert_called_once_with(document_id="test_doc_123", text="", ensure_newline=True)
        assert result == mock_service_response

    async def test_append_text_service_error(self, mock_docs_service):
        """Test docs_append_text with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Permission denied"}
        mock_docs_service.append_text.return_value = error_response

        with pytest.raises(ValueError, match="Permission denied"):
            await docs_append_text("restricted_doc", "Some text")

    async def test_append_text_service_returns_none(self, mock_docs_service):
        """Test docs_append_text when service returns None."""
        # Mock service returning None
        mock_docs_service.append_text.return_value = None

        with pytest.raises(ValueError, match="Failed to append text"):
            await docs_append_text("test_doc_123", "Some text")

    async def test_append_text_missing_success_flag(self, mock_docs_service):
        """Test docs_append_text when service returns response without success flag."""
        # Mock service returning response without success flag
        mock_service_response = {
            "document_id": "test_doc_123",
            "operation": "append_text",
        }
        mock_docs_service.append_text.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to append text"):
            await docs_append_text("test_doc_123", "Some text")


class TestDocsPrependTextTool:
    """Tests for the docs_prepend_text tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_prepend_text_success(self, mock_docs_service):
        """Test docs_prepend_text successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "prepend_text",
        }
        mock_docs_service.prepend_text.return_value = mock_service_response

        args = {
            "document_id": "test_doc_123",
            "text": "Prepended text",
            "ensure_newline": False,
        }
        result = await docs_prepend_text(**args)

        mock_docs_service.prepend_text.assert_called_once_with(
            document_id="test_doc_123", text="Prepended text", ensure_newline=False
        )
        assert result == mock_service_response

    async def test_prepend_text_default_ensure_newline(self, mock_docs_service):
        """Test docs_prepend_text with default ensure_newline value."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "prepend_text",
        }
        mock_docs_service.prepend_text.return_value = mock_service_response

        args = {"document_id": "test_doc_123", "text": "Prepended text"}
        result = await docs_prepend_text(**args)

        mock_docs_service.prepend_text.assert_called_once_with(
            document_id="test_doc_123",
            text="Prepended text",
            ensure_newline=True,  # Default value
        )
        assert result == mock_service_response

    async def test_prepend_text_empty_document_id(self, mock_docs_service):
        """Test docs_prepend_text with empty document_id."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_prepend_text("", "Some text")

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_prepend_text("   ", "Some text")

    async def test_prepend_text_empty_text_allowed(self, mock_docs_service):
        """Test docs_prepend_text with empty text (should be allowed)."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "prepend_text",
        }
        mock_docs_service.prepend_text.return_value = mock_service_response

        # Empty text should be allowed
        result = await docs_prepend_text("test_doc_123", "")
        mock_docs_service.prepend_text.assert_called_once_with(document_id="test_doc_123", text="", ensure_newline=True)
        assert result == mock_service_response

    async def test_prepend_text_service_error(self, mock_docs_service):
        """Test docs_prepend_text with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Document not found"}
        mock_docs_service.prepend_text.return_value = error_response

        with pytest.raises(ValueError, match="Document not found"):
            await docs_prepend_text("nonexistent_doc", "Some text")

    async def test_prepend_text_service_returns_none(self, mock_docs_service):
        """Test docs_prepend_text when service returns None."""
        # Mock service returning None
        mock_docs_service.prepend_text.return_value = None

        with pytest.raises(ValueError, match="Failed to prepend text"):
            await docs_prepend_text("test_doc_123", "Some text")

    async def test_prepend_text_missing_success_flag(self, mock_docs_service):
        """Test docs_prepend_text when service returns response without success flag."""
        # Mock service returning response without success flag
        mock_service_response = {
            "document_id": "test_doc_123",
            "operation": "prepend_text",
        }
        mock_docs_service.prepend_text.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to prepend text"):
            await docs_prepend_text("test_doc_123", "Some text")


class TestDocsInsertTextTool:
    """Tests for the docs_insert_text tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_insert_text_success(self, mock_docs_service):
        """Test docs_insert_text successful case."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "insert_text",
        }
        mock_docs_service.insert_text.return_value = mock_service_response

        args = {
            "document_id": "test_doc_123",
            "text": "Inserted text",
            "index": 5,
            "segment_id": "header_1",
        }
        result = await docs_insert_text(**args)

        mock_docs_service.insert_text.assert_called_once_with(
            document_id="test_doc_123",
            text="Inserted text",
            index=5,
            segment_id="header_1",
        )
        assert result == mock_service_response

    async def test_insert_text_default_parameters(self, mock_docs_service):
        """Test docs_insert_text with default parameters."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "insert_text",
        }
        mock_docs_service.insert_text.return_value = mock_service_response

        args = {"document_id": "test_doc_123", "text": "Inserted text"}
        result = await docs_insert_text(**args)

        mock_docs_service.insert_text.assert_called_once_with(
            document_id="test_doc_123",
            text="Inserted text",
            index=None,  # Default value
            segment_id=None,  # Default value
        )
        assert result == mock_service_response

    async def test_insert_text_empty_document_id(self, mock_docs_service):
        """Test docs_insert_text with empty document_id."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_insert_text("", "Some text")

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_insert_text("   ", "Some text")

    async def test_insert_text_empty_text_allowed(self, mock_docs_service):
        """Test docs_insert_text with empty text (should be allowed)."""
        mock_service_response = {
            "document_id": "test_doc_123",
            "success": True,
            "operation": "insert_text",
        }
        mock_docs_service.insert_text.return_value = mock_service_response

        # Empty text should be allowed
        result = await docs_insert_text("test_doc_123", "")
        mock_docs_service.insert_text.assert_called_once_with(document_id="test_doc_123", text="", index=None, segment_id=None)
        assert result == mock_service_response

    async def test_insert_text_service_error(self, mock_docs_service):
        """Test docs_insert_text with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Permission denied"}
        mock_docs_service.insert_text.return_value = error_response

        with pytest.raises(ValueError, match="Permission denied"):
            await docs_insert_text("restricted_doc", "Some text")

    async def test_insert_text_service_returns_none(self, mock_docs_service):
        """Test docs_insert_text when service returns None."""
        # Mock service returning None
        mock_docs_service.insert_text.return_value = None

        with pytest.raises(ValueError, match="Failed to insert text"):
            await docs_insert_text("test_doc_123", "Some text")

    async def test_insert_text_missing_success_flag(self, mock_docs_service):
        """Test docs_insert_text when service returns response without success flag."""
        # Mock service returning response without success flag
        mock_service_response = {
            "document_id": "test_doc_123",
            "operation": "insert_text",
        }
        mock_docs_service.insert_text.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to insert text"):
            await docs_insert_text("test_doc_123", "Some text")


class TestDocsBatchUpdateTool:
    """Tests for the docs_batch_update tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch("google_workspace_mcp.tools.docs_tools.DocsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_batch_update_success(self, mock_docs_service):
        """Test docs_batch_update successful case."""
        requests = [
            {"insertText": {"location": {"index": 1}, "text": "Hello"}},
            {"insertText": {"location": {"index": 6}, "text": " World"}},
        ]
        mock_service_response = {
            "document_id": "test_doc_123",
            "replies": [{"insertText": {}}, {"insertText": {}}],
            "write_control": {"requiredRevisionId": "123"},
        }
        mock_docs_service.batch_update.return_value = mock_service_response

        args = {"document_id": "test_doc_123", "requests": requests}
        result = await docs_batch_update(**args)

        mock_docs_service.batch_update.assert_called_once_with(document_id="test_doc_123", requests=requests)
        assert result == mock_service_response

    async def test_batch_update_empty_requests(self, mock_docs_service):
        """Test docs_batch_update with empty requests list."""
        requests = []
        mock_service_response = {
            "document_id": "test_doc_123",
            "replies": [],
            "message": "No requests provided.",
        }
        mock_docs_service.batch_update.return_value = mock_service_response

        result = await docs_batch_update("test_doc_123", requests)

        mock_docs_service.batch_update.assert_called_once_with(document_id="test_doc_123", requests=requests)
        assert result == mock_service_response

    async def test_batch_update_empty_document_id(self, mock_docs_service):
        """Test docs_batch_update with empty document_id."""
        requests = [{"insertText": {"location": {"index": 1}, "text": "Hello"}}]

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_batch_update("", requests)

        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            await docs_batch_update("   ", requests)

    async def test_batch_update_invalid_requests_type(self, mock_docs_service):
        """Test docs_batch_update with invalid requests type."""
        with pytest.raises(ValueError, match="Requests must be a list"):
            await docs_batch_update("test_doc_123", "not a list")

        with pytest.raises(ValueError, match="Requests must be a list"):
            await docs_batch_update("test_doc_123", {"single": "object"})

    async def test_batch_update_service_error(self, mock_docs_service):
        """Test docs_batch_update with service error."""
        requests = [{"insertText": {"location": {"index": 1}, "text": "Hello"}}]
        # Mock service error response
        error_response = {"error": True, "message": "Invalid request structure"}
        mock_docs_service.batch_update.return_value = error_response

        with pytest.raises(ValueError, match="Invalid request structure"):
            await docs_batch_update("restricted_doc", requests)

    async def test_batch_update_service_returns_none(self, mock_docs_service):
        """Test docs_batch_update when service returns None."""
        requests = [{"insertText": {"location": {"index": 1}, "text": "Hello"}}]
        # Mock service returning None
        mock_docs_service.batch_update.return_value = None

        with pytest.raises(ValueError, match="Failed to execute batch update"):
            await docs_batch_update("test_doc_123", requests)
