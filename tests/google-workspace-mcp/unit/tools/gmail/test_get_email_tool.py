"""
Unit tests for Gmail get email tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import gmail_get_message_details

pytestmark = pytest.mark.anyio


class TestGmailGetMessageDetailsTool:
    """Tests for the gmail_get_message_details tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_gmail_get_message_details_success(self, mock_gmail_service):
        """Test successful message details retrieval."""
        # Mock successful service response
        expected_result = {
            "id": "test_msg_id",
            "subject": "Test Subject",
            "from": "sender@example.com",
            "body": "Test email body",
        }
        mock_gmail_service.get_email.return_value = expected_result

        # Call the tool
        result = await gmail_get_message_details("test_msg_id")

        # Verify service was called correctly
        mock_gmail_service.get_email.assert_called_once_with(email_id="test_msg_id")

        # Verify result
        assert result == expected_result

    async def test_gmail_get_message_details_empty_id(self, mock_gmail_service):
        """Test message details retrieval with empty email ID."""
        with pytest.raises(ValueError, match="Email ID cannot be empty"):
            await gmail_get_message_details("")

        with pytest.raises(ValueError, match="Email ID cannot be empty"):
            await gmail_get_message_details("   ")

    async def test_gmail_get_message_details_service_error(self, mock_gmail_service):
        """Test message details retrieval with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Message not found"}
        mock_gmail_service.get_email.return_value = error_response

        with pytest.raises(ValueError, match="Message not found"):
            await gmail_get_message_details("nonexistent_id")

    async def test_gmail_get_message_details_service_returns_none(self, mock_gmail_service):
        """Test message details retrieval when service returns None."""
        # Mock service returning None
        mock_gmail_service.get_email.return_value = None

        with pytest.raises(ValueError, match="Failed to retrieve email with ID"):
            await gmail_get_message_details("test_id")
