"""
Unit tests for Gmail get_gmail_email tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import get_gmail_email

pytestmark = pytest.mark.anyio


class TestGetGmailEmailTool:
    """Tests for the get_gmail_email tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_email_success(self, mock_gmail_service):
        """Test get_gmail_email successful case."""
        mock_email_data = {"id": "email123", "subject": "Test Email"}
        mock_attachments = [{"id": "att1", "filename": "doc.pdf"}]
        mock_gmail_service.get_email_with_attachments.return_value = (
            mock_email_data,
            mock_attachments,
        )

        args = {"email_id": "email123", "user_id": "test@example.com"}
        result = await get_gmail_email(**args)

        mock_gmail_service.get_email_with_attachments.assert_called_once_with("email123")
        expected_result = mock_email_data.copy()
        expected_result["attachments"] = mock_attachments
        assert result == expected_result

    async def test_get_email_service_error_dict(self, mock_gmail_service):
        """Test get_gmail_email when service returns an error dict."""
        mock_gmail_service.get_email_with_attachments.return_value = (
            {"error": True, "message": "Email not found"},
            [],  # Assume empty attachments list on error
        )

        args = {"email_id": "notfound123", "user_id": "test@example.com"}
        with pytest.raises(ValueError, match="Email not found"):
            await get_gmail_email(**args)

    async def test_get_email_service_error_none(self, mock_gmail_service):
        """Test get_gmail_email when service returns None for email."""
        mock_gmail_service.get_email_with_attachments.return_value = (
            None,
            [],  # Assume empty attachments list on error
        )

        args = {"email_id": "error_none_id", "user_id": "test@example.com"}
        with pytest.raises(ValueError, match="Failed to retrieve email with ID: error_none_id"):
            await get_gmail_email(**args)

    async def test_get_email_empty_id(self):
        """Test get_gmail_email tool validation for empty email_id."""
        args = {"email_id": "", "user_id": "test@example.com"}
        with pytest.raises(ValueError, match="Email ID cannot be empty"):
            await get_gmail_email(**args)
