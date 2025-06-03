"""
Unit tests for Gmail bulk delete tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import gmail_bulk_delete_messages

pytestmark = pytest.mark.anyio


class TestGmailBulkDeleteMessagesTool:
    """Tests for the gmail_bulk_delete_messages tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.gmail.GmailService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_gmail_bulk_delete_messages_success(self, mock_gmail_service):
        """Test successful bulk delete operation."""
        # Mock successful service response
        expected_result = {
            "success": True,
            "count_requested": 3,
            "message": "Batch delete request for 3 message(s) sent successfully.",
        }
        mock_gmail_service.bulk_delete_messages.return_value = expected_result

        # Call the tool
        message_ids = ["msg1", "msg2", "msg3"]
        result = await gmail_bulk_delete_messages(message_ids)

        # Verify service was called correctly
        mock_gmail_service.bulk_delete_messages.assert_called_once_with(
            message_ids=message_ids
        )

        # Verify result
        assert result == expected_result

    async def test_gmail_bulk_delete_messages_invalid_input(self, mock_gmail_service):
        """Test bulk delete with invalid input."""
        # Test with non-list input
        with pytest.raises(ValueError, match="Message IDs must be provided as a list"):
            await gmail_bulk_delete_messages("not_a_list")

        # Test with empty list
        with pytest.raises(ValueError, match="Message IDs list cannot be empty"):
            await gmail_bulk_delete_messages([])

    async def test_gmail_bulk_delete_messages_service_error(self, mock_gmail_service):
        """Test bulk delete with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Invalid message IDs"}
        mock_gmail_service.bulk_delete_messages.return_value = error_response

        with pytest.raises(ValueError, match="Invalid message IDs"):
            await gmail_bulk_delete_messages(["invalid_id"])

    async def test_gmail_bulk_delete_messages_service_returns_none(
        self, mock_gmail_service
    ):
        """Test bulk delete when service returns None."""
        # Mock service returning None
        mock_gmail_service.bulk_delete_messages.return_value = None

        with pytest.raises(ValueError, match="Error during bulk deletion"):
            await gmail_bulk_delete_messages(["msg1", "msg2"])
