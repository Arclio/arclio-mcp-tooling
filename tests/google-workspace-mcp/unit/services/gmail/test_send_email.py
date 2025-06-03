"""
Unit tests for Gmail send_email operations.
"""

from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError


class TestGmailSendEmail:
    """Tests for Gmail send_email operations."""

    def test_send_email_success(self, mock_gmail_service):
        """Test successful email sending."""
        # Test data
        to = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test email body"

        # Mock API response
        mock_sent_message = {
            "id": "sent_msg123",
            "threadId": "thread456",
            "labelIds": ["SENT"],
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_sent_message)
        mock_gmail_service.service.users.return_value.messages.return_value.send.return_value.execute = mock_execute

        # Mock MIMEText
        with patch("google_workspace_mcp.services.gmail.MIMEText") as mock_mime_text:
            mock_message = MagicMock()
            mock_message.as_bytes.return_value = b"raw message content"
            mock_mime_text.return_value = mock_message

            with patch("google_workspace_mcp.services.gmail.base64") as mock_base64:
                mock_base64.urlsafe_b64encode.return_value.decode.return_value = "encoded_message"

                # Call the method
                result = mock_gmail_service.send_email(to, subject, body)

        # Verify API call
        mock_gmail_service.service.users.return_value.messages.return_value.send.assert_called_once_with(
            userId="me", body={"raw": "encoded_message"}
        )

        # Verify result
        assert result == mock_sent_message
        assert result["id"] == "sent_msg123"

    def test_send_email_with_cc_and_bcc(self, mock_gmail_service):
        """Test email sending with CC and BCC recipients."""
        # Test data
        to = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test email body"
        cc = ["cc@example.com"]
        bcc = ["bcc@example.com"]

        # Mock API response
        mock_sent_message = {"id": "sent_msg123"}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_sent_message)
        mock_gmail_service.service.users.return_value.messages.return_value.send.return_value.execute = mock_execute

        # Mock MIMEText
        with patch("google_workspace_mcp.services.gmail.MIMEText") as mock_mime_text:
            mock_message = MagicMock()
            mock_message.as_bytes.return_value = b"raw message content"
            mock_mime_text.return_value = mock_message

            with patch("google_workspace_mcp.services.gmail.base64") as mock_base64:
                mock_base64.urlsafe_b64encode.return_value.decode.return_value = "encoded_message"

                # Call the method
                result = mock_gmail_service.send_email(to, subject, body, cc=cc, bcc=bcc)

        # Verify MIME headers were set
        mock_message.__setitem__.assert_any_call("To", "recipient@example.com")
        mock_message.__setitem__.assert_any_call("Subject", "Test Subject")
        mock_message.__setitem__.assert_any_call("Cc", "cc@example.com")
        mock_message.__setitem__.assert_any_call("Bcc", "bcc@example.com")

        # Verify result
        assert result == mock_sent_message

    def test_send_email_empty_to_list(self, mock_gmail_service):
        """Test email sending with empty 'to' list."""
        # Test data
        to = []
        subject = "Test Subject"
        body = "Test email body"

        # Call the method
        result = mock_gmail_service.send_email(to, subject, body)

        # Verify error response
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "Recipient list 'to' cannot be empty" in result["message"]
        assert result["operation"] == "send_email"

    def test_send_email_none_to_list(self, mock_gmail_service):
        """Test email sending with None 'to' list."""
        # Test data
        to = None
        subject = "Test Subject"
        body = "Test email body"

        # Call the method
        result = mock_gmail_service.send_email(to, subject, body)

        # Verify error response
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "Recipient list 'to' cannot be empty" in result["message"]

    def test_send_email_api_error(self, mock_gmail_service):
        """Test email sending with API error."""
        # Test data
        to = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test email body"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid recipient"}}')

        # Setup the mock to raise the error
        mock_gmail_service.service.users.return_value.messages.return_value.send.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid recipient",
            "operation": "send_email",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Mock MIMEText to avoid the error happening before API call
        with (
            patch("google_workspace_mcp.services.gmail.MIMEText"),
            patch("google_workspace_mcp.services.gmail.base64"),
        ):
            # Call the method
            result = mock_gmail_service.send_email(to, subject, body)

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with("send_email", http_error)
        assert result == expected_error
