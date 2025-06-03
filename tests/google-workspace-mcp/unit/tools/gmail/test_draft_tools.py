"""
Unit tests for Gmail create_gmail_draft and delete_gmail_draft tools.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import (
    create_gmail_draft,
    delete_gmail_draft,
    gmail_send_draft,
)

pytestmark = pytest.mark.anyio


# --- Fixture --- #


@pytest.fixture
def mock_gmail_service():
    """Patch GmailService for tool tests."""
    with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        yield mock_service


# --- Tests for create_gmail_draft --- #


class TestCreateGmailDraft:
    """Tests for the create_gmail_draft tool function."""

    async def test_create_draft_success(self, mock_gmail_service):
        """Test create_gmail_draft successful case."""
        mock_service_response = {
            "id": "draft123",
            "message": {
                "id": "msg456",
                "threadId": "thread789",
                "snippet": "Hello, this is a test...",
            },
        }
        mock_gmail_service.create_draft.return_value = mock_service_response

        args = {
            "to": "recipient@example.com",
            "subject": "Test Email",
            "body": "Hello, this is a test email.",
        }
        result = await create_gmail_draft(**args)

        mock_gmail_service.create_draft.assert_called_once_with(
            to="recipient@example.com",
            subject="Test Email",
            body="Hello, this is a test email.",
            cc=None,
            bcc=None,
        )
        assert result == mock_service_response

    async def test_create_draft_with_cc_bcc(self, mock_gmail_service):
        """Test create_gmail_draft with CC and BCC."""
        mock_service_response = {
            "id": "draft456",
            "message": {"id": "msg789", "threadId": "thread101"},
        }
        mock_gmail_service.create_draft.return_value = mock_service_response

        args = {
            "to": "recipient@example.com",
            "subject": "Test Email with CC/BCC",
            "body": "This email has CC and BCC recipients.",
            "cc": "cc@example.com",
            "bcc": "bcc@example.com",
        }
        result = await create_gmail_draft(**args)

        mock_gmail_service.create_draft.assert_called_once_with(
            to="recipient@example.com",
            subject="Test Email with CC/BCC",
            body="This email has CC and BCC recipients.",
            cc="cc@example.com",
            bcc="bcc@example.com",
        )
        assert result == mock_service_response

    async def test_create_draft_service_error(self, mock_gmail_service):
        """Test create_gmail_draft when the service returns an error."""
        mock_gmail_service.create_draft.return_value = {
            "error": True,
            "message": "API Error: Invalid recipient",
        }

        args = {
            "to": "invalid-email",
            "subject": "Test",
            "body": "Test body",
        }
        with pytest.raises(ValueError, match="API Error: Invalid recipient"):
            await create_gmail_draft(**args)

    async def test_create_draft_missing_args(self):
        """Test create_gmail_draft with missing required arguments."""
        base_args = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Test body",
        }

        for key in ["to", "subject", "body"]:
            args = base_args.copy()
            args[key] = ""
            with pytest.raises(ValueError, match="To, subject, and body are required"):
                await create_gmail_draft(**args)


# --- Tests for delete_gmail_draft --- #


class TestDeleteGmailDraft:
    """Tests for the delete_gmail_draft tool function."""

    async def test_delete_draft_success(self, mock_gmail_service):
        """Test delete_gmail_draft successful case."""
        mock_gmail_service.delete_draft.return_value = True

        args = {"draft_id": "draft123"}
        result = await delete_gmail_draft(**args)

        mock_gmail_service.delete_draft.assert_called_once_with(draft_id="draft123")
        assert result == {
            "message": "Draft with ID 'draft123' deleted successfully.",
            "success": True,
        }

    async def test_delete_draft_service_failure(self, mock_gmail_service):
        """Test delete_gmail_draft when the service call fails."""
        mock_gmail_service.delete_draft.return_value = False

        args = {"draft_id": "nonexistent"}
        with pytest.raises(ValueError, match="Failed to delete draft"):
            await delete_gmail_draft(**args)

    async def test_delete_draft_missing_id(self):
        """Test delete_gmail_draft with missing draft_id."""
        args = {"draft_id": ""}
        with pytest.raises(ValueError, match="Draft ID is required"):
            await delete_gmail_draft(**args)


# --- Tests for gmail_send_draft --- #


class TestGmailSendDraft:
    """Tests for the gmail_send_draft tool function."""

    async def test_gmail_send_draft_success(self, mock_gmail_service):
        """Test successful draft sending."""
        # Mock successful service response
        expected_result = {
            "id": "sent_msg123",
            "threadId": "thread456",
            "labelIds": ["SENT"],
        }
        mock_gmail_service.send_draft.return_value = expected_result

        # Call the tool
        result = await gmail_send_draft("draft123")

        # Verify service was called correctly
        mock_gmail_service.send_draft.assert_called_once_with(draft_id="draft123")

        # Verify result
        assert result == expected_result

    async def test_gmail_send_draft_empty_id(self, mock_gmail_service):
        """Test draft sending with empty draft ID."""
        with pytest.raises(ValueError, match="Draft ID cannot be empty"):
            await gmail_send_draft("")

        with pytest.raises(ValueError, match="Draft ID cannot be empty"):
            await gmail_send_draft("   ")

    async def test_gmail_send_draft_service_error(self, mock_gmail_service):
        """Test draft sending with service error."""
        # Mock service error response
        error_response = {"error": True, "message": "Draft not found"}
        mock_gmail_service.send_draft.return_value = error_response

        with pytest.raises(ValueError, match="Draft not found"):
            await gmail_send_draft("nonexistent_draft")

    async def test_gmail_send_draft_service_returns_none(self, mock_gmail_service):
        """Test draft sending when service returns None."""
        # Mock service returning None
        mock_gmail_service.send_draft.return_value = None

        with pytest.raises(ValueError, match="Failed to send draft"):
            await gmail_send_draft("draft123")
