"""
Unit tests for Gmail bulk_delete_gmail_emails tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import bulk_delete_gmail_emails

pytestmark = pytest.mark.anyio


class TestBulkDeleteGmailEmails:
    """Tests for the bulk_delete_gmail_emails tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_bulk_delete_success(self, mock_gmail_service):
        """Test bulk_delete_gmail_emails successful deletion."""
        mock_service_response = {
            "deleted_count": 3,
            "message": "Successfully deleted 3 emails",
        }
        mock_gmail_service.bulk_delete_emails.return_value = mock_service_response

        args = {"message_ids": ["msg1", "msg2", "msg3"]}
        result = await bulk_delete_gmail_emails(**args)

        mock_gmail_service.bulk_delete_emails.assert_called_once_with(message_ids=["msg1", "msg2", "msg3"])
        assert result == mock_service_response

    async def test_bulk_delete_service_error(self, mock_gmail_service):
        """Test bulk_delete_gmail_emails when the service returns an error."""
        mock_gmail_service.bulk_delete_emails.return_value = {
            "error": True,
            "message": "API Error: Invalid message ID",
        }

        args = {"message_ids": ["invalid_id"]}
        with pytest.raises(ValueError, match="API Error: Invalid message ID"):
            await bulk_delete_gmail_emails(**args)

    async def test_bulk_delete_empty_list(self):
        """Test bulk_delete_gmail_emails with empty message_ids list."""
        args = {"message_ids": []}
        with pytest.raises(ValueError, match="Message IDs list cannot be empty"):
            await bulk_delete_gmail_emails(**args)

    async def test_bulk_delete_non_list(self):
        """Test bulk_delete_gmail_emails with non-list message_ids."""
        args = {"message_ids": "not_a_list"}
        with pytest.raises(ValueError, match="Message IDs must be provided as a list"):
            await bulk_delete_gmail_emails(**args)
