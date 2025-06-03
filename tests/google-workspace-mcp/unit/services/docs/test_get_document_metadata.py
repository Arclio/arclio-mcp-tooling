"""
Unit tests for DocsService get_document_metadata method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestDocsGetDocumentMetadata:
    """Tests for DocsService get_document_metadata method."""

    def test_get_document_metadata_success(self, mock_docs_service):
        """Test successful document metadata retrieval."""
        # Test data
        document_id = "test_doc_123"

        # Mock API response
        mock_document_response = {
            "documentId": "test_doc_123",
            "title": "Test Document",
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_document_response)
        mock_docs_service.service.documents.return_value.get.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_docs_service.get_document_metadata(document_id)

        # Verify API call
        mock_docs_service.service.documents.return_value.get.assert_called_once_with(
            documentId=document_id, fields="documentId,title"
        )

        # Verify result
        expected_result = {
            "document_id": "test_doc_123",
            "title": "Test Document",
            "document_link": "https://docs.google.com/document/d/test_doc_123/edit",
        }
        assert result == expected_result

    def test_get_document_metadata_document_not_found(self, mock_docs_service):
        """Test document metadata retrieval when document is not found."""
        # Test data
        document_id = "nonexistent_doc"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Document not found"}}'
        )

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Document not found",
            "operation": "get_document_metadata",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.get_document_metadata(document_id)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with(
            "get_document_metadata", http_error
        )
        assert result == expected_error

    def test_get_document_metadata_permission_denied(self, mock_docs_service):
        """Test document metadata retrieval with permission denied."""
        # Test data
        document_id = "restricted_doc"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Permission denied"}}'
        )

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "get_document_metadata",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.get_document_metadata(document_id)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with(
            "get_document_metadata", http_error
        )
        assert result == expected_error

    def test_get_document_metadata_unexpected_error(self, mock_docs_service):
        """Test document metadata retrieval with unexpected error."""
        # Test data
        document_id = "error_doc"

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = (
            unexpected_error
        )

        # Call the method
        result = mock_docs_service.get_document_metadata(document_id)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "get_document_metadata"

    def test_get_document_metadata_empty_response(self, mock_docs_service):
        """Test document metadata retrieval with empty response."""
        # Test data
        document_id = "empty_doc"

        # Mock empty API response
        mock_document_response = {}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_document_response)
        mock_docs_service.service.documents.return_value.get.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_docs_service.get_document_metadata(document_id)

        # Verify result handles missing fields gracefully
        expected_result = {
            "document_id": None,
            "title": None,
            "document_link": "https://docs.google.com/document/d/None/edit",
        }
        assert result == expected_result
