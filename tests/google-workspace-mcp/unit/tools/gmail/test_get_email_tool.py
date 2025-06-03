"""
Unit tests for Gmail get_gmail_email tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import get_gmail_email

pytestmark = pytest.mark.anyio


class TestGetGmailEmail:
    """Tests for the get_gmail_email tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.gmail.GmailService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_email_success(self, mock_gmail_service):
        """Test get_gmail_email successful case."""
        mock_service_response = {
            "id": "msg123",
            "threadId": "thread456",
            "snippet": "This is a test email snippet...",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "date": "2024-01-01T12:00:00Z",
            "body": "This is the email body.",
        }
        mock_gmail_service.get_email.return_value = mock_service_response

        args = {"email_id": "msg123"}
        result = await get_gmail_email(**args)

        mock_gmail_service.get_email.assert_called_once_with(email_id="msg123")
        assert result == mock_service_response

    async def test_get_email_service_error(self, mock_gmail_service):
        """Test get_gmail_email when the service returns an error."""
        mock_gmail_service.get_email.return_value = {
            "error": True,
            "message": "API Error: Email not found",
        }

        args = {"email_id": "nonexistent"}
        with pytest.raises(ValueError, match="API Error: Email not found"):
            await get_gmail_email(**args)

    async def test_get_email_missing_id(self):
        """Test get_gmail_email with missing email_id."""
        args = {"email_id": ""}
        with pytest.raises(ValueError, match="Email ID cannot be empty"):
            await get_gmail_email(**args)
