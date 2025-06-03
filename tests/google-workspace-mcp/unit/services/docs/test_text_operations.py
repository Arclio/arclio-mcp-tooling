"""
Unit tests for DocsService write operations (append_text and prepend_text).
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestDocsAppendText:
    """Tests for DocsService append_text method."""

    def test_append_text_to_empty_document(self, mock_docs_service):
        """Test appending text to an empty document."""
        # Test data
        document_id = "test_doc_123"
        text_to_append = "This is appended text."

        # Mock document get response for empty document
        mock_document_response = {
            "body": {"content": [{"endIndex": 1}]}  # Empty document end index
        }

        # Setup document get mock
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method
        result = mock_docs_service.append_text(document_id, text_to_append, ensure_newline=True)

        # Verify document get call
        mock_docs_service.service.documents.return_value.get.assert_called_once_with(
            documentId=document_id, fields="body(content(endIndex,paragraph))"
        )

        # Verify batchUpdate call - for empty doc, no newline should be prepended
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 0},  # end_index - 1 = 1 - 1 = 0
                    "text": text_to_append,  # No newline prepended for empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "append_text",
        }
        assert result == expected_result

    def test_append_text_to_existing_document(self, mock_docs_service):
        """Test appending text to a document with existing content."""
        # Test data
        document_id = "test_doc_123"
        text_to_append = "This is appended text."

        # Mock document get response for document with content
        mock_document_response = {
            "body": {"content": [{"endIndex": 15}]}  # Document with content
        }

        # Setup document get mock
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method
        result = mock_docs_service.append_text(document_id, text_to_append, ensure_newline=True)

        # Verify batchUpdate call - newline should be prepended for non-empty doc
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 14},  # end_index - 1 = 15 - 1 = 14
                    "text": "\n" + text_to_append,  # Newline prepended for non-empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "append_text",
        }
        assert result == expected_result

    def test_append_text_ensure_newline_false(self, mock_docs_service):
        """Test appending text with ensure_newline=False."""
        # Test data
        document_id = "test_doc_123"
        text_to_append = "This is appended text."

        # Mock document get response
        mock_document_response = {"body": {"content": [{"endIndex": 10}]}}

        # Setup mocks
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method with ensure_newline=False
        result = mock_docs_service.append_text(document_id, text_to_append, ensure_newline=False)

        # Verify batchUpdate call - no newline should be prepended
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 9},  # end_index - 1
                    "text": text_to_append,  # No newline even for non-empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        assert result["success"] is True

    def test_append_text_http_error(self, mock_docs_service):
        """Test append text with HTTP error."""
        # Test data
        document_id = "restricted_doc"
        text_to_append = "This will fail."

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission denied"}}')

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "append_text",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.append_text(document_id, text_to_append)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with("append_text", http_error)
        assert result == expected_error


class TestDocsPrependText:
    """Tests for DocsService prepend_text method."""

    def test_prepend_text_to_empty_document(self, mock_docs_service):
        """Test prepending text to an empty document."""
        # Test data
        document_id = "test_doc_123"
        text_to_prepend = "This is prepended text."

        # Mock document get response for empty document
        mock_document_response = {"body": {"content": []}}  # Empty content

        # Setup document get mock
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method
        result = mock_docs_service.prepend_text(document_id, text_to_prepend, ensure_newline=True)

        # Verify document get call
        mock_docs_service.service.documents.return_value.get.assert_called_once_with(
            documentId=document_id, fields="body(content(endIndex))"
        )

        # Verify batchUpdate call - for empty doc, no newline should be appended
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 1},  # Beginning of document body
                    "text": text_to_prepend,  # No newline appended for empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "prepend_text",
        }
        assert result == expected_result

    def test_prepend_text_to_existing_document(self, mock_docs_service):
        """Test prepending text to a document with existing content."""
        # Test data
        document_id = "test_doc_123"
        text_to_prepend = "This is prepended text."

        # Mock document get response for document with content
        mock_document_response = {
            "body": {"content": [{"endIndex": 15}]}  # Document with content
        }

        # Setup document get mock
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method
        result = mock_docs_service.prepend_text(document_id, text_to_prepend, ensure_newline=True)

        # Verify batchUpdate call - newline should be appended for non-empty doc
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 1},  # Beginning of document body
                    "text": text_to_prepend + "\n",  # Newline appended for non-empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "prepend_text",
        }
        assert result == expected_result

    def test_prepend_text_ensure_newline_false(self, mock_docs_service):
        """Test prepending text with ensure_newline=False."""
        # Test data
        document_id = "test_doc_123"
        text_to_prepend = "This is prepended text."

        # Mock document get response
        mock_document_response = {"body": {"content": [{"endIndex": 10}]}}

        # Setup mocks
        mock_docs_service.service.documents.return_value.get.return_value.execute.return_value = mock_document_response
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method with ensure_newline=False
        result = mock_docs_service.prepend_text(document_id, text_to_prepend, ensure_newline=False)

        # Verify batchUpdate call - no newline should be appended
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": text_to_prepend,  # No newline even for non-empty doc
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        assert result["success"] is True

    def test_prepend_text_http_error(self, mock_docs_service):
        """Test prepend text with HTTP error."""
        # Test data
        document_id = "restricted_doc"
        text_to_prepend = "This will fail."

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission denied"}}')

        # Setup the mock to raise the error
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "prepend_text",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.prepend_text(document_id, text_to_prepend)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with("prepend_text", http_error)
        assert result == expected_error

    def test_prepend_text_unexpected_error(self, mock_docs_service):
        """Test prepend text with unexpected error."""
        # Test data
        document_id = "error_doc"
        text_to_prepend = "This will cause an error."

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_docs_service.service.documents.return_value.get.return_value.execute.side_effect = unexpected_error

        # Call the method
        result = mock_docs_service.prepend_text(document_id, text_to_prepend)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "prepend_text"


class TestDocsInsertText:
    """Tests for DocsService insert_text method."""

    def test_insert_text_default_index(self, mock_docs_service):
        """Test inserting text with default index."""
        # Test data
        document_id = "test_doc_123"
        text_to_insert = "This is inserted text."

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method with default index
        result = mock_docs_service.insert_text(document_id, text_to_insert)

        # Verify batchUpdate call - should use default index of 1
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": 1},  # Default index
                    "text": text_to_insert,
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "insert_text",
        }
        assert result == expected_result

    def test_insert_text_custom_index(self, mock_docs_service):
        """Test inserting text with custom index."""
        # Test data
        document_id = "test_doc_123"
        text_to_insert = "This is inserted text."
        custom_index = 5

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method with custom index
        result = mock_docs_service.insert_text(document_id, text_to_insert, index=custom_index)

        # Verify batchUpdate call - should use custom index
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": custom_index},
                    "text": text_to_insert,
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "insert_text",
        }
        assert result == expected_result

    def test_insert_text_with_segment_id(self, mock_docs_service):
        """Test inserting text with segment ID."""
        # Test data
        document_id = "test_doc_123"
        text_to_insert = "This is inserted text."
        segment_id = "header_1"
        custom_index = 3

        # Setup batchUpdate mock
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.return_value = {}

        # Call the method with segment ID
        result = mock_docs_service.insert_text(document_id, text_to_insert, index=custom_index, segment_id=segment_id)

        # Verify batchUpdate call - should include segment ID
        expected_requests = [
            {
                "insertText": {
                    "location": {"index": custom_index, "segmentId": segment_id},
                    "text": text_to_insert,
                }
            }
        ]
        mock_docs_service.service.documents.return_value.batchUpdate.assert_called_once_with(
            documentId=document_id, body={"requests": expected_requests}
        )

        # Verify result
        expected_result = {
            "document_id": document_id,
            "success": True,
            "operation": "insert_text",
        }
        assert result == expected_result

    def test_insert_text_http_error(self, mock_docs_service):
        """Test insert text with HTTP error."""
        # Test data
        document_id = "restricted_doc"
        text_to_insert = "This will fail."

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
            "operation": "insert_text",
        }
        mock_docs_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_docs_service.insert_text(document_id, text_to_insert)

        # Verify error handling
        mock_docs_service.handle_api_error.assert_called_once_with("insert_text", http_error)
        assert result == expected_error

    def test_insert_text_unexpected_error(self, mock_docs_service):
        """Test insert text with unexpected error."""
        # Test data
        document_id = "error_doc"
        text_to_insert = "This will cause an error."

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_docs_service.service.documents.return_value.batchUpdate.return_value.execute.side_effect = unexpected_error

        # Call the method
        result = mock_docs_service.insert_text(document_id, text_to_insert)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "insert_text"
