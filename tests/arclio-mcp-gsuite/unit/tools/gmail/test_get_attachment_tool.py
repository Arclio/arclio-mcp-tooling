"""
Unit tests for Gmail get_gmail_attachment tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.gmail import get_gmail_attachment

pytestmark = pytest.mark.anyio


class TestGetGmailAttachmentTool:
    """Tests for the get_gmail_attachment tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("arclio_mcp_gsuite.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_attachment_success(self, mock_gmail_service):
        """Test get_gmail_attachment successful case."""
        mock_attachment_data = {
            "size": 12345,
            "data": "base64encodedattachmentdata",
        }
        mock_gmail_service.get_attachment.return_value = mock_attachment_data

        args = {
            "message_id": "msg123",
            "attachment_id": "att456",
            "user_id": "test@example.com",
        }
        result = await get_gmail_attachment(**args)

        mock_gmail_service.get_attachment.assert_called_once_with(
            message_id="msg123", attachment_id="att456"
        )
        assert result == mock_attachment_data

    async def test_get_attachment_service_error(self, mock_gmail_service):
        """Test get_gmail_attachment when service returns an error."""
        mock_gmail_service.get_attachment.return_value = {
            "error": True,
            "message": "Attachment not found",
        }

        args = {
            "message_id": "msg123",
            "attachment_id": "nonexistent",
            "user_id": "test@example.com",
        }
        with pytest.raises(ValueError, match="Attachment not found"):
            await get_gmail_attachment(**args)

    async def test_get_attachment_missing_ids(self):
        """Test get_gmail_attachment with missing IDs."""
        # Test missing message_id
        args = {
            "message_id": "",
            "attachment_id": "att456",
            "user_id": "test@example.com",
        }
        with pytest.raises(ValueError, match="Message ID and Attachment ID cannot be empty"):
            await get_gmail_attachment(**args)

        # Test missing attachment_id
        args = {
            "message_id": "msg123",
            "attachment_id": "",
            "user_id": "test@example.com",
        }
        with pytest.raises(ValueError, match="Message ID and Attachment ID cannot be empty"):
            await get_gmail_attachment(**args)
