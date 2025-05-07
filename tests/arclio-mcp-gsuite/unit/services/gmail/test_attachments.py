"""
Unit tests for Gmail attachment operations.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError

# from arclio_mcp_gsuite.services.gmail import GmailService # Removed unused import


class TestGmailAttachments:
    """Tests for Gmail attachment operations."""

    # Removed local mock_gmail_service fixture

    def test_get_attachment_success(self, mock_gmail_service):
        """Test successful attachment retrieval."""
        # Test data
        message_id = "msg123"
        attachment_id = "att123"

        # Mock API response
        mock_attachment = {"size": 12345, "data": "base64encodedattachmentdata"}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_attachment)
        mock_gmail_service.service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute = mock_execute

        # Call the method
        result = mock_gmail_service.get_attachment(message_id, attachment_id)

        # Verify API call
        mock_gmail_service.service.users.return_value.messages.return_value.attachments.return_value.get.assert_called_once_with(
            userId="me", messageId=message_id, id=attachment_id
        )

        # Verify result
        assert result["size"] == 12345
        assert result["data"] == "base64encodedattachmentdata"

    def test_get_attachment_error(self, mock_gmail_service):
        """Test attachment retrieval failure."""
        # Test data
        message_id = "msg123"
        attachment_id = "nonexistent"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Attachment not found"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Attachment not found",
            "operation": "get_attachment",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.get_attachment(message_id, attachment_id)

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with("get_attachment", http_error)
        assert result == expected_error
