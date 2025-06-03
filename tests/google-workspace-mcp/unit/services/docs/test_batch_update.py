"""
Unit tests for DocsService batch_update method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestDocsBatchUpdate:
    """Tests for DocsService batch_update method."""

    def test_batch_update_success(self, mock_docs_service):
        """Test successful batch update."""
        # Test data
        document_id = "test_doc_123"
        requests = [
            {"insertText": {"location": {"index": 1}, "text": "Hello, "}},
            {"insertText": {"location": {"index": 8}, "text": "World!"}},
        ]

        # Mock API response
        mock_response = {
            "documentId": document_id,
            "replies": [{"insertText": {}}, {"insertText": {}}],
            "writeControl": {"requiredRevisionId": "123"},
        }
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = mock_response

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify API call
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "replies": [{"insertText": {}}, {"insertText": {}}],
            "write_control": {"requiredRevisionId": "123"},
        }
        assert result == expected_result

    def test_batch_update_no_requests(self, mock_docs_service):
        """Test batch update with empty requests list."""
        # Test data
        document_id = "test_doc_123"
        requests = []

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify no API call was made
        mock_docs_service.service.documents.return_value.batchUpdate.assert_not_called()

        # Verify result
        expected_result = {
            "document_id": document_id,
            "replies": [],
            "message": "No requests provided.",
        }
        assert result == expected_result

    def test_batch_update_success_empty_replies(self, mock_docs_service):
        """Test successful batch update with empty replies."""
        # Test data
        document_id = "test_doc_123"
        requests = [{"insertText": {"location": {"index": 1}, "text": "Hello"}}]

        # Mock API response with empty replies
        mock_response = {
            "documentId": document_id
            # No 'replies' field
        }
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = mock_response

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify result handles missing fields gracefully
        expected_result = {
            "document_id": document_id,
            "replies": [],  # Should default to empty list
            "write_control": None,  # Should be None when missing
        }
        assert result == expected_result

    def test_batch_update_http_error(self, mock_docs_service):
        """Test batch update with HTTP error."""
        # Test data
        document_id = "restricted_doc"
        requests = [{"insertText": {"location": {"index": 1}, "text": "This will fail"}}]

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission denied"}}')

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "batch_update",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with("batch_update", http_error)
        assert result == expected_error

    def test_batch_update_unexpected_error(self, mock_docs_service):
        """Test batch update with unexpected error."""
        # Test data
        document_id = "error_doc"
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": "This will cause an error",
                }
            }
        ]

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.side_effect = unexpected_error

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "batch_update"

    def test_batch_update_complex_requests(self, mock_docs_service):
        """Test batch update with complex request types."""
        # Test data
        document_id = "test_doc_123"
        requests = [
            {"insertText": {"location": {"index": 1}, "text": "Title\n"}},
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": 6},  # "Title" length
                    "textStyle": {
                        "bold": True,
                        "fontSize": {"magnitude": 14, "unit": "PT"},
                    },
                    "fields": "bold,fontSize",
                }
            },
        ]

        # Mock API response
        mock_response = {
            "documentId": document_id,
            "replies": [{"insertText": {}}, {"updateTextStyle": {}}],
        }
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = mock_response

        # Call the method
        result = mock_docs_service.batch_update(document_id, requests)

        # Verify API call with complex requests
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "replies": [{"insertText": {}}, {"updateTextStyle": {}}],
            "write_control": None,
        }
        assert result == expected_result
