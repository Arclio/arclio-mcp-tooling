"""
Unit tests for DocsService create_document method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestDocsCreateDocument:
    """Tests for DocsService create_document method."""

    def test_create_document_success(self, mock_docs_service):
        """Test successful document creation."""
        # Test data
        title = "Test Document"

        # Mock API response
        mock_document_response = {
            "documentId": "test_doc_123",
            "title": "Test Document",
            "revisionId": "rev_456",
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_document_response)
        mock_docs_service.service.documents.return_value.create.return_value.execute = mock_execute

        # Call the method
        result = mock_docs_service.create_document(title)

        # Verify API call
        mock_docs_service.service.documents.return_value.create.assert_called_once_with(body={"title": title})

        # Verify result
        expected_result = {
            "document_id": "test_doc_123",
            "title": "Test Document",
            "document_link": "https://docs.google.com/document/d/test_doc_123/edit",
        }
        assert result == expected_result

    def test_create_document_http_error(self, mock_docs_service):
        """Test document creation with HTTP error."""
        # Test data
        title = "Failed Document"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Insufficient permissions"}}')

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.create.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Insufficient permissions",
            "operation": "create_document",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.create_document(title)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with("create_document", http_error)
        assert result == expected_error

    def test_create_document_unexpected_error(self, mock_docs_service):
        """Test document creation with unexpected error."""
        # Test data
        title = "Error Document"

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Unexpected error occurred")
        mock_docs_service.service.documents.return_value.create.return_value.execute.side_effect = unexpected_error

        # Call the method
        result = mock_docs_service.create_document(title)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Unexpected error occurred"
        assert result["operation"] == "create_document"

    def test_create_document_empty_response(self, mock_docs_service):
        """Test document creation with empty response."""
        # Test data
        title = "Empty Response Document"

        # Mock empty API response
        mock_document_response = {}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_document_response)
        mock_docs_service.service.documents.return_value.create.return_value.execute = mock_execute

        # Call the method
        result = mock_docs_service.create_document(title)

        # Verify result handles missing fields gracefully
        expected_result = {
            "document_id": None,
            "title": None,
            "document_link": "https://docs.google.com/document/d/None/edit",
        }
        assert result == expected_result
