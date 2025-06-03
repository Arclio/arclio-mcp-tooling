"""
Unit tests for Gmail draft operations.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError

# from google_workspace_mcp.services.gmail import GmailService # Removed unused import


class TestGmailDrafts:
    """Tests for Gmail draft operations."""

    # Removed local mock_gmail_service fixture

    def test_create_draft_success(self, mock_gmail_service):
        """Test successful draft creation."""
        # Test data
        to = "recipient@example.com"
        subject = "Test Subject"
        body = "Test email body"
        cc = ["cc1@example.com", "cc2@example.com"]

        # Mock API response
        mock_draft_response = {
            "id": "draft123",
            "message": {"id": "msg123", "threadId": "thread123"},
        }

        # Setup execute mock to return our draft response
        mock_execute = MagicMock(return_value=mock_draft_response)
        mock_gmail_service.service.users.return_value.drafts.return_value.create.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_gmail_service.create_draft(
            to=to, subject=subject, body=body, cc=cc
        )

        # Verify the API call - we need to check that create() was called
        # but we can't easily verify the exact message content since it's encoded
        mock_gmail_service.service.users.return_value.drafts.return_value.create.assert_called_once()

        # Verify the draft ID is in the result
        assert result["id"] == "draft123"
        assert result["message"]["id"] == "msg123"

    def test_create_draft_error(self, mock_gmail_service):
        """Test draft creation failure."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Invalid email address"}}'
        )

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.drafts.return_value.create.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid email address",
            "operation": "create_draft",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.create_draft(
            to="invalid@", subject="Test", body="Body"
        )

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with(
            "create_draft", http_error
        )
        assert result == expected_error

    def test_delete_draft_success(self, mock_gmail_service):
        """Test successful draft deletion."""
        draft_id = "draft_to_delete"

        # Mock successful deletion (typically returns None)
        mock_execute = MagicMock(return_value=None)
        mock_gmail_service.service.users.return_value.drafts.return_value.delete.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_gmail_service.delete_draft(draft_id)

        # Verify API call
        mock_gmail_service.service.users.return_value.drafts.return_value.delete.assert_called_once_with(
            userId="me", id=draft_id
        )

        # Verify result is True for success
        assert result is True

    def test_delete_draft_error(self, mock_gmail_service):
        """Test draft deletion failure."""
        draft_id = "nonexistent_draft"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Draft not found"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.drafts.return_value.delete.return_value.execute.side_effect = (
            http_error
        )

        # Call the method
        result = mock_gmail_service.delete_draft(draft_id)

        # Verify API call was attempted
        mock_gmail_service.service.users.return_value.drafts.return_value.delete.assert_called_once_with(
            userId="me", id=draft_id
        )

        # For draft deletion, the method returns False on error (it doesn't use handle_api_error)
        assert result is False

    def test_send_draft_success(self, mock_gmail_service):
        """Test successful draft sending."""
        draft_id = "draft123"

        # Mock API response
        mock_sent_message = {
            "id": "sent_msg123",
            "threadId": "thread456",
            "labelIds": ["SENT"],
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_sent_message)
        mock_gmail_service.service.users.return_value.drafts.return_value.send.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_gmail_service.send_draft(draft_id)

        # Verify API call
        mock_gmail_service.service.users.return_value.drafts.return_value.send.assert_called_once_with(
            userId="me", body={"id": draft_id}
        )

        # Verify result
        assert result == mock_sent_message
        assert result["id"] == "sent_msg123"

    def test_send_draft_error(self, mock_gmail_service):
        """Test draft sending failure."""
        draft_id = "nonexistent_draft"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Draft not found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Draft not found"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.drafts.return_value.send.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Draft not found",
            "operation": "send_draft",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.send_draft(draft_id)

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with(
            "send_draft", http_error
        )
        assert result == expected_error
