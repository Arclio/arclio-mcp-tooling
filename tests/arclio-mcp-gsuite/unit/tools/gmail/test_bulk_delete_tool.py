"""
Unit tests for Gmail bulk_delete_gmail_emails tool function.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.gmail import bulk_delete_gmail_emails

pytestmark = pytest.mark.anyio


class TestBulkDeleteGmailEmails:
    """Tests for the bulk_delete_gmail_emails function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a patched GmailService for tool tests."""
        with patch("arclio_mcp_gsuite.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_bulk_delete_success(self, mock_gmail_service):
        """Test bulk_delete_gmail_emails with successful deletion."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "success": True,
            "message": "Successfully deleted 3 emails",
            "count": 3,
        }
        mock_gmail_service.bulk_delete_emails.return_value = mock_service_response

        # Define arguments (use 'user_id')
        args = {
            "user_id": "user@example.com",
            "message_ids": ["msg1", "msg2", "msg3"],
        }

        # Call the function
        result = await bulk_delete_gmail_emails(**args)

        # Verify service call
        mock_gmail_service.bulk_delete_emails.assert_called_once_with(
            message_ids=["msg1", "msg2", "msg3"]
        )
        # Verify raw result
        assert result == mock_service_response

    async def test_bulk_delete_service_error(self, mock_gmail_service):
        """Test bulk_delete_gmail_emails when the service returns an error."""
        # Setup mock error response
        mock_gmail_service.bulk_delete_emails.return_value = {
            "error": True,
            "message": "Batch delete failed via API",
            "error_type": "api_error",
        }

        # Define arguments (use 'user_id')
        args = {
            "user_id": "user@example.com",
            "message_ids": ["msg1"],
        }

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="Batch delete failed via API"):
            await bulk_delete_gmail_emails(**args)

        # Verify service call
        mock_gmail_service.bulk_delete_emails.assert_called_once_with(message_ids=["msg1"])

    async def test_bulk_delete_missing_ids(self):
        """Test with missing message_ids list."""
        # Define arguments (use 'user_id')
        args = {"user_id": "user@example.com", "message_ids": None}  # Pass None
        with pytest.raises(ValueError, match="A non-empty list of message_ids is required"):
            await bulk_delete_gmail_emails(**args)

    async def test_bulk_delete_empty_ids(self):
        """Test with empty message_ids list."""
        # Define arguments (use 'user_id')
        args = {"user_id": "user@example.com", "message_ids": []}
        with pytest.raises(ValueError, match="A non-empty list of message_ids is required"):
            await bulk_delete_gmail_emails(**args)
