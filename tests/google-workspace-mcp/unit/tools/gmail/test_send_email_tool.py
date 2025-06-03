"""
Unit tests for Gmail send email tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import gmail_send_email

pytestmark = pytest.mark.anyio


class TestGmailSendEmailTool:
    """Tests for the gmail_send_email tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_gmail_send_email_success(self, mock_gmail_service):
        """Test successful email sending."""
        # Mock successful service response
        expected_result = {
            "id": "sent_msg123",
            "threadId": "thread456",
            "labelIds": ["SENT"],
        }
        mock_gmail_service.send_email.return_value = expected_result

        # Call the tool
        to = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test email body"
        result = await gmail_send_email(to, subject, body)

        # Verify service was called correctly
        mock_gmail_service.send_email.assert_called_once_with(to=to, subject=subject, body=body, cc=None, bcc=None)

        # Verify result
        assert result == expected_result

    async def test_gmail_send_email_with_cc_and_bcc(self, mock_gmail_service):
        """Test email sending with CC and BCC recipients."""
        # Mock successful service response
        expected_result = {"id": "sent_msg123"}
        mock_gmail_service.send_email.return_value = expected_result

        # Call the tool with CC and BCC
        to = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test email body"
        cc = ["cc@example.com"]
        bcc = ["bcc@example.com"]
        result = await gmail_send_email(to, subject, body, cc=cc, bcc=bcc)

        # Verify service was called correctly
        mock_gmail_service.send_email.assert_called_once_with(to=to, subject=subject, body=body, cc=cc, bcc=bcc)

        # Verify result
        assert result == expected_result

    async def test_gmail_send_email_invalid_to_list(self, mock_gmail_service):
        """Test email sending with invalid 'to' parameter."""
        # Test with empty list
        with pytest.raises(
            ValueError,
            match="Recipients 'to' must be a non-empty list of email strings",
        ):
            await gmail_send_email([], "Subject", "Body")

        # Test with non-list
        with pytest.raises(
            ValueError,
            match="Recipients 'to' must be a non-empty list of email strings",
        ):
            await gmail_send_email("not_a_list", "Subject", "Body")

        # Test with list containing non-strings
        with pytest.raises(
            ValueError,
            match="Recipients 'to' must be a non-empty list of email strings",
        ):
            await gmail_send_email([123, "valid@example.com"], "Subject", "Body")

        # Test with list containing empty strings
        with pytest.raises(
            ValueError,
            match="Recipients 'to' must be a non-empty list of email strings",
        ):
            await gmail_send_email(["", "valid@example.com"], "Subject", "Body")

    async def test_gmail_send_email_invalid_subject(self, mock_gmail_service):
        """Test email sending with invalid subject."""
        # Test with empty subject
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            await gmail_send_email(["recipient@example.com"], "", "Body")

        # Test with whitespace-only subject
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            await gmail_send_email(["recipient@example.com"], "   ", "Body")

    async def test_gmail_send_email_invalid_body(self, mock_gmail_service):
        """Test email sending with invalid body."""
        # Test with None body
        with pytest.raises(ValueError, match="Body cannot be None"):
            await gmail_send_email(["recipient@example.com"], "Subject", None)

        # Empty string body should be allowed
        mock_gmail_service.send_email.return_value = {"id": "sent_msg123"}
        result = await gmail_send_email(["recipient@example.com"], "Subject", "")
        assert result["id"] == "sent_msg123"

    async def test_gmail_send_email_service_error(self, mock_gmail_service):
        """Test email sending with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Invalid recipient email"}
        mock_gmail_service.send_email.return_value = error_response

        with pytest.raises(ValueError, match="Invalid recipient email"):
            await gmail_send_email(["invalid@"], "Subject", "Body")

    async def test_gmail_send_email_service_returns_none(self, mock_gmail_service):
        """Test email sending when service returns None."""
        # Mock service returning None
        mock_gmail_service.send_email.return_value = None

        with pytest.raises(ValueError, match="Failed to send email"):
            await gmail_send_email(["recipient@example.com"], "Subject", "Body")
