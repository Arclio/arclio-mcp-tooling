"""
Unit tests for Gmail get attachment tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import gmail_get_attachment_content

pytestmark = pytest.mark.anyio


class TestGmailGetAttachmentContentTool:
    """Tests for the gmail_get_attachment_content tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_gmail_get_attachment_content_success(self, mock_gmail_service):
        """Test successful attachment content retrieval."""
        # Mock successful service response
        expected_result = {
            "filename": "test_file.pdf",
            "mimeType": "application/pdf",
            "size": 12345,
            "data": "base64encodeddata",
        }
        mock_gmail_service.get_attachment_content.return_value = expected_result

        # Call the tool
        result = await gmail_get_attachment_content("msg123", "att456")

        # Verify service was called correctly
        mock_gmail_service.get_attachment_content.assert_called_once_with(message_id="msg123", attachment_id="att456")

        # Verify result
        assert result == expected_result

    async def test_gmail_get_attachment_content_missing_params(self, mock_gmail_service):
        """Test attachment content retrieval with missing parameters."""
        with pytest.raises(ValueError, match="Message ID and attachment ID are required"):
            await gmail_get_attachment_content("", "att456")

        with pytest.raises(ValueError, match="Message ID and attachment ID are required"):
            await gmail_get_attachment_content("msg123", "")

        with pytest.raises(ValueError, match="Message ID and attachment ID are required"):
            await gmail_get_attachment_content("", "")

    async def test_gmail_get_attachment_content_service_error(self, mock_gmail_service):
        """Test attachment content retrieval with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Attachment not found"}
        mock_gmail_service.get_attachment_content.return_value = error_response

        with pytest.raises(ValueError, match="Attachment not found"):
            await gmail_get_attachment_content("msg123", "nonexistent")

    async def test_gmail_get_attachment_content_service_returns_none(self, mock_gmail_service):
        """Test attachment content retrieval when service returns None."""
        # Mock service returning None
        mock_gmail_service.get_attachment_content.return_value = None

        with pytest.raises(ValueError, match="Error getting attachment"):
            await gmail_get_attachment_content("msg123", "att456")
