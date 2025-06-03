"""
Unit tests for GmailService.get_email_by_id method.
"""

import base64
from unittest.mock import MagicMock, patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError

# from google_workspace_mcp.services.gmail import GmailService # Removed unused import


class TestGmailGetEmailById:
    """Tests for the GmailService.get_email_by_id method."""

    # Removed local mock_gmail_service fixture

    def test_get_email_by_id_success(self, mock_gmail_service):
        """Test successful email retrieval by ID."""
        # Mock data for the API response
        email_id = "test_email_123"
        mock_message = {
            "id": email_id,
            "threadId": "thread123",
            "snippet": "Email snippet",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                ],
                "mimeType": "text/plain",
                "body": {"data": base64.b64encode(b"Email body content").decode("utf-8")},
            },
        }

        # Setup execute mock to return our test data
        mock_execute = MagicMock(return_value=mock_message)
        mock_gmail_service.service.users.return_value.messages.return_value.get.return_value.execute = mock_execute

        # Mock parse_message to return structured data
        mock_parsed_message = {
            "id": email_id,
            "threadId": "thread123",
            "subject": "Test Subject",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "body": "Email body content",
            "mimeType": "text/plain",
        }

        with patch.object(mock_gmail_service, "_parse_message", return_value=mock_parsed_message):
            # Call the method
            result = mock_gmail_service.get_email_by_id(email_id)

            # Verify correct API call
            mock_gmail_service.service.users.return_value.messages.return_value.get.assert_called_once_with(
                userId="me", id=email_id
            )

            # Verify the result
            assert result == mock_parsed_message
            assert result["id"] == email_id
            assert result["subject"] == "Test Subject"
            assert result["body"] == "Email body content"

    def test_get_email_by_id_error(self, mock_gmail_service):
        """Test get_email_by_id when API call fails."""
        email_id = "nonexistent_id"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Email Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Email not found"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.messages.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Email not found",
            "operation": "get_email_by_id",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.get_email_by_id(email_id)

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with("get_email_by_id", http_error)
        assert result == expected_error
