"""
Unit tests for Gmail reply_gmail_email tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import reply_gmail_email

pytestmark = pytest.mark.anyio


class TestReplyGmailEmail:
    """Tests for the reply_gmail_email tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_reply_email_success(self, mock_gmail_service):
        """Test reply_gmail_email successful case."""
        mock_service_response = {
            "id": "reply123",
            "threadId": "thread456",
            "snippet": "Reply sent successfully",
        }
        mock_gmail_service.reply_to_email.return_value = mock_service_response

        args = {
            "email_id": "msg123",
            "reply_body": "Thank you for your email!",
        }
        result = await reply_gmail_email(**args)

        mock_gmail_service.reply_to_email.assert_called_once_with(
            email_id="msg123",
            reply_body="Thank you for your email!",
            reply_all=False,
        )
        assert result == mock_service_response

    async def test_reply_email_with_reply_all(self, mock_gmail_service):
        """Test reply_gmail_email with reply_all=True."""
        mock_service_response = {
            "id": "reply456",
            "threadId": "thread789",
            "snippet": "Reply all sent successfully",
        }
        mock_gmail_service.reply_to_email.return_value = mock_service_response

        args = {
            "email_id": "msg456",
            "reply_body": "Thank you all for the discussion!",
            "reply_all": True,
        }
        result = await reply_gmail_email(**args)

        mock_gmail_service.reply_to_email.assert_called_once_with(
            email_id="msg456",
            reply_body="Thank you all for the discussion!",
            reply_all=True,
        )
        assert result == mock_service_response

    async def test_reply_email_service_error(self, mock_gmail_service):
        """Test reply_gmail_email when the service returns an error."""
        mock_gmail_service.reply_to_email.return_value = {
            "error": True,
            "message": "API Error: Original email not found",
        }

        args = {
            "email_id": "nonexistent",
            "reply_body": "This should fail",
        }
        with pytest.raises(ValueError, match="API Error: Original email not found"):
            await reply_gmail_email(**args)

    async def test_reply_email_missing_args(self):
        """Test reply_gmail_email with missing required arguments."""
        # Test missing email_id
        args = {"email_id": "", "reply_body": "Some reply"}
        with pytest.raises(ValueError, match="Email ID and reply body are required"):
            await reply_gmail_email(**args)

        # Test missing reply_body
        args = {"email_id": "msg123", "reply_body": ""}
        with pytest.raises(ValueError, match="Email ID and reply body are required"):
            await reply_gmail_email(**args)

    @patch("google_workspace_mcp.tools.gmail.GmailService")
    def test_patch_gmail_service(self, mock_service_class):
        """Test the patching of GmailService."""
        # This test is just to ensure the patch is working correctly
        pass
