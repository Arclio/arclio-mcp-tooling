"""
Unit tests for Google Docs tools.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.docs_tools import (
    docs_create_document,
    docs_get_document_metadata,
)

pytestmark = pytest.mark.anyio


class TestDocsCreateDocumentTool:
    """Tests for the docs_create_document tool function."""

    @pytest.fixture
    def mock_docs_service(self):
        """Patch DocsService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.docs_tools.DocsService"
        ) as mock_service_class:
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
        with patch(
            "google_workspace_mcp.tools.docs_tools.DocsService"
        ) as mock_service_class:
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

        mock_docs_service.get_document_metadata.assert_called_once_with(
            document_id="test_doc_123"
        )
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

    async def test_get_document_metadata_missing_document_id_in_response(
        self, mock_docs_service
    ):
        """Test docs_get_document_metadata when service returns response without document_id."""
        # Mock service returning response without document_id
        mock_service_response = {"title": "Test Document"}
        mock_docs_service.get_document_metadata.return_value = mock_service_response

        with pytest.raises(ValueError, match="Failed to retrieve metadata"):
            await docs_get_document_metadata("test_doc_123")
