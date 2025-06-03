"""
Unit tests for Gmail bulk operations.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestGmailBulkOperations:
    """Tests for Gmail bulk operations."""

    def test_bulk_delete_messages_success(self, mock_gmail_service):
        """Test successful bulk delete operation."""
        # Test data
        message_ids = ["msg1", "msg2", "msg3"]

        # Setup execute mock
        mock_execute = MagicMock()
        mock_gmail_service.service.users.return_value.messages.return_value.batchDelete.return_value.execute = mock_execute

        # Call the method
        result = mock_gmail_service.bulk_delete_messages(message_ids)

        # Verify API call
        mock_gmail_service.service.users.return_value.messages.return_value.batchDelete.assert_called_once_with(
            userId="me", body={"ids": message_ids}
        )

        # Verify result
        assert result["success"] is True
        assert result["count_requested"] == 3
        assert "3 message(s) sent successfully" in result["message"]

    def test_bulk_delete_messages_empty_list(self, mock_gmail_service):
        """Test bulk delete with empty message list."""
        # Test data
        message_ids = []

        # Call the method
        result = mock_gmail_service.bulk_delete_messages(message_ids)

        # Verify result
        assert result["success"] is False
        assert result["message"] == "No message IDs provided"

    def test_bulk_delete_messages_invalid_ids(self, mock_gmail_service):
        """Test bulk delete with invalid message IDs."""
        # Test data with invalid entries
        message_ids = ["msg1", "", "msg3", None]

        # Call the method
        result = mock_gmail_service.bulk_delete_messages(message_ids)

        # Verify result
        assert result["success"] is False
        assert "Invalid message IDs" in result["message"]

    def test_bulk_delete_messages_large_batch(self, mock_gmail_service):
        """Test bulk delete with large batch (over 1000 items)."""
        # Test data - more than max batch size
        message_ids = [f"msg{i}" for i in range(1500)]

        # Setup execute mock
        mock_execute = MagicMock()
        mock_gmail_service.service.users.return_value.messages.return_value.batchDelete.return_value.execute = mock_execute

        # Call the method
        result = mock_gmail_service.bulk_delete_messages(message_ids)

        # Verify multiple API calls were made (should be 2 batches: 1000 + 500)
        assert mock_gmail_service.service.users.return_value.messages.return_value.batchDelete.call_count == 2

        # Verify result
        assert result["success"] is True
        assert result["count_requested"] == 1500

    def test_bulk_delete_messages_api_error(self, mock_gmail_service):
        """Test bulk delete with API error."""
        # Test data
        message_ids = ["msg1", "msg2"]

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid message IDs"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.messages.return_value.batchDelete.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid message IDs",
            "operation": "bulk_delete_messages",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.bulk_delete_messages(message_ids)

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with("bulk_delete_messages", http_error)
        assert result == expected_error


# TODO: Add tests for GmailService.bulk_delete_emails
