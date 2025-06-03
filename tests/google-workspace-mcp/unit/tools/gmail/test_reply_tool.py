"""
Unit tests for Gmail reply tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import gmail_reply_to_email

pytestmark = pytest.mark.anyio


class TestGmailReplyToEmailTool:
    """Tests for the gmail_reply_to_email tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_gmail_reply_to_email_success(self, mock_gmail_service):
        """Test successful reply creation."""
        # Mock successful service response
        expected_result = {
            "id": "reply_msg123",
            "threadId": "thread456",
            "subject": "Re: Original Subject",
        }
        mock_gmail_service.reply_to_email.return_value = expected_result

        # Call the tool
        result = await gmail_reply_to_email("original_msg123", "This is my reply")

        # Verify service was called correctly
        mock_gmail_service.reply_to_email.assert_called_once_with(
            email_id="original_msg123", reply_body="This is my reply", reply_all=False
        )

        # Verify result
        assert result == expected_result

    async def test_gmail_reply_to_email_with_reply_all(self, mock_gmail_service):
        """Test reply with reply_all option."""
        # Mock successful service response
        expected_result = {"id": "reply_msg123"}
        mock_gmail_service.reply_to_email.return_value = expected_result

        # Call the tool with reply_all=True
        result = await gmail_reply_to_email("original_msg123", "Reply to all", reply_all=True)

        # Verify service was called correctly
        mock_gmail_service.reply_to_email.assert_called_once_with(
            email_id="original_msg123", reply_body="Reply to all", reply_all=True
        )

        # Verify result
        assert result == expected_result

    async def test_gmail_reply_to_email_missing_params(self, mock_gmail_service):
        """Test reply with missing parameters."""
        with pytest.raises(ValueError, match="Email ID and reply body are required"):
            await gmail_reply_to_email("", "Reply body")

        with pytest.raises(ValueError, match="Email ID and reply body are required"):
            await gmail_reply_to_email("msg123", "")

        with pytest.raises(ValueError, match="Email ID and reply body are required"):
            await gmail_reply_to_email("", "")

    async def test_gmail_reply_to_email_service_error(self, mock_gmail_service):
        """Test reply with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Original message not found"}
        mock_gmail_service.reply_to_email.return_value = error_response

        with pytest.raises(ValueError, match="Original message not found"):
            await gmail_reply_to_email("nonexistent_msg", "Reply body")

    async def test_gmail_reply_to_email_service_returns_none(self, mock_gmail_service):
        """Test reply when service returns None."""
        # Mock service returning None
        mock_gmail_service.reply_to_email.return_value = None

        with pytest.raises(ValueError, match="Error trying to create reply draft"):
            await gmail_reply_to_email("msg123", "Reply body")
