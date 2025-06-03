"""
Unit tests for Gmail reply_gmail_email tool function.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import reply_gmail_email

pytestmark = pytest.mark.anyio


class TestReplyGmailEmail:
    """Tests for the reply_gmail_email function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a patched GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Mock get_email_by_id used internally by the tool
            def mock_get_email(email_id, parse_body):
                if email_id == "original_msg_123":
                    return {
                        "id": "original_msg_123",
                        "threadId": "thread456",
                        "from": "sender@example.com",
                        "subject": "Original Subject",
                        # Other fields needed for reply construction?
                    }
                if email_id == "not_found_id":
                    return {"error": True, "message": "Original message not found"}
                return {
                    "error": True,
                    "message": "Unknown error getting original message",
                }

            mock_service.get_email_by_id.side_effect = mock_get_email

            yield mock_service

    async def test_reply_success_draft(self, mock_gmail_service):
        """Test reply_gmail_email creating a draft successfully."""
        # Mock service response for creating the reply draft
        mock_reply_response = {
            "id": "draft789",
            "message": {"id": "reply_msg_abc", "threadId": "thread456"},
        }
        mock_gmail_service.create_reply.return_value = mock_reply_response

        args = {
            "original_message_id": "original_msg_123",
            "reply_body": "This is my reply body.",
            "user_id": "user@example.com",
            "send": False,
            "cc": ["cc_reply@example.com"],
        }

        result = await reply_gmail_email(**args)

        # Verify get_email_by_id call
        mock_gmail_service.get_email_by_id.assert_called_once_with("original_msg_123", parse_body=False)

        # Verify create_reply call
        expected_original_message = {
            "id": "original_msg_123",
            "threadId": "thread456",
            "from": "sender@example.com",
            "subject": "Original Subject",
        }
        mock_gmail_service.create_reply.assert_called_once_with(
            original_message=expected_original_message,
            reply_body="This is my reply body.",
            send=False,
            cc=["cc_reply@example.com"],
        )

        # Verify raw result
        assert result == mock_reply_response

    async def test_reply_success_send(self, mock_gmail_service):
        """Test reply_gmail_email sending successfully."""
        # Mock service response for sending the reply
        mock_reply_response = {
            "id": "sent_msg_xyz",
            "threadId": "thread456",
            "labelIds": ["SENT", "INBOX"],
        }
        mock_gmail_service.create_reply.return_value = mock_reply_response

        args = {
            "original_message_id": "original_msg_123",
            "reply_body": "This is my sent reply.",
            "user_id": "user@example.com",
            "send": True,
        }

        result = await reply_gmail_email(**args)

        # Verify get_email_by_id call
        mock_gmail_service.get_email_by_id.assert_called_once_with("original_msg_123", parse_body=False)

        # Verify create_reply call
        expected_original_message = {
            "id": "original_msg_123",
            "threadId": "thread456",
            "from": "sender@example.com",
            "subject": "Original Subject",
        }
        mock_gmail_service.create_reply.assert_called_once_with(
            original_message=expected_original_message,
            reply_body="This is my sent reply.",
            send=True,
            cc=None,  # Default cc is None
        )

        # Verify raw result
        assert result == mock_reply_response

    async def test_reply_fail_getting_original(self, mock_gmail_service):
        """Test reply_gmail_email when fetching original message fails."""
        args = {
            "original_message_id": "not_found_id",
            "reply_body": "Does not matter",
            "user_id": "user@example.com",
        }

        with pytest.raises(ValueError, match="Original message not found"):
            await reply_gmail_email(**args)

        mock_gmail_service.get_email_by_id.assert_called_once_with("not_found_id", parse_body=False)
        mock_gmail_service.create_reply.assert_not_called()

    async def test_reply_fail_creating_reply(self, mock_gmail_service):
        """Test reply_gmail_email when creating the reply fails."""
        # Simulate error during the create_reply call
        mock_gmail_service.create_reply.return_value = {
            "error": True,
            "message": "API failed to create reply draft",
        }

        args = {
            "original_message_id": "original_msg_123",
            "reply_body": "This reply will fail",
            "user_id": "user@example.com",
            "send": False,  # Trying to create draft
        }

        # Expect the specific error message from the service
        with pytest.raises(ValueError, match="API failed to create reply draft"):
            await reply_gmail_email(**args)

        mock_gmail_service.get_email_by_id.assert_called_once()
        mock_gmail_service.create_reply.assert_called_once()

    async def test_reply_missing_args(self):
        """Test reply_gmail_email with missing required arguments."""
        base_args = {
            "original_message_id": "original_msg_123",
            "reply_body": "Some reply",
            "user_id": "user@example.com",
        }

        args_missing_id = base_args.copy()
        args_missing_id["original_message_id"] = ""
        with pytest.raises(ValueError, match="Original message ID and reply body are required"):
            await reply_gmail_email(**args_missing_id)

        # Note: reply_body=None should also trigger the check
        args_missing_body = base_args.copy()
        args_missing_body["reply_body"] = None
        with pytest.raises(ValueError, match="Original message ID and reply body are required"):
            await reply_gmail_email(**args_missing_body)

    @patch("google_workspace_mcp.tools.gmail.GmailService")
    def test_patch_gmail_service(self, mock_service_class):
        """Test the patching of GmailService."""
        # This test is just to ensure the patch is working correctly
        pass
