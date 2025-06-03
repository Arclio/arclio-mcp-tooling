"""
Unit tests for Gmail get_gmail_attachment tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import get_gmail_attachment

pytestmark = pytest.mark.anyio


class TestGetGmailAttachment:
    """Tests for the get_gmail_attachment tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_attachment_success(self, mock_gmail_service):
        """Test get_gmail_attachment successful case."""
        mock_service_response = {
            "filename": "document.pdf",
            "mimeType": "application/pdf",
            "data": "base64_encoded_data...",
            "size": 1024,
        }
        mock_gmail_service.get_attachment.return_value = mock_service_response

        args = {
            "message_id": "msg123",
            "attachment_id": "attach456",
        }
        result = await get_gmail_attachment(**args)

        mock_gmail_service.get_attachment.assert_called_once_with(message_id="msg123", attachment_id="attach456")
        assert result == mock_service_response

    async def test_get_attachment_service_error(self, mock_gmail_service):
        """Test get_gmail_attachment when the service returns an error."""
        mock_gmail_service.get_attachment.return_value = {
            "error": True,
            "message": "API Error: Attachment not found",
        }

        args = {
            "message_id": "msg123",
            "attachment_id": "invalid_attach",
        }
        with pytest.raises(ValueError, match="API Error: Attachment not found"):
            await get_gmail_attachment(**args)

    async def test_get_attachment_missing_args(self):
        """Test get_gmail_attachment with missing required arguments."""
        # Test missing message_id
        args = {"message_id": "", "attachment_id": "attach123"}
        with pytest.raises(ValueError, match="Message ID and attachment ID are required"):
            await get_gmail_attachment(**args)

        # Test missing attachment_id
        args = {"message_id": "msg123", "attachment_id": ""}
        with pytest.raises(ValueError, match="Message ID and attachment ID are required"):
            await get_gmail_attachment(**args)
