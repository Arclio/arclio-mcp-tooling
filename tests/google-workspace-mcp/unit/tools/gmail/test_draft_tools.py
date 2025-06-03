"""
Unit tests for Gmail create_draft and delete_draft tool functions.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import create_gmail_draft, delete_gmail_draft

pytestmark = pytest.mark.anyio

# --- Tests for create_gmail_draft --- #


class TestCreateGmailDraft:
    """Tests for the create_gmail_draft function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a patched GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_create_draft_success(self, mock_gmail_service):
        """Test create_gmail_draft successful case."""
        mock_service_response = {
            "id": "draft123",
            "message": {"id": "msg456", "threadId": "thread789"},
        }
        mock_gmail_service.create_draft.return_value = mock_service_response

        args = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
            "user_id": "user@example.com",
            "cc": ["cc@example.com"],
        }
        result = await create_gmail_draft(**args)

        mock_gmail_service.create_draft.assert_called_once_with(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            cc=["cc@example.com"],
        )
        assert result == mock_service_response

    async def test_create_draft_service_error(self, mock_gmail_service):
        """Test create_gmail_draft when service returns an error."""
        mock_gmail_service.create_draft.return_value = {
            "error": True,
            "message": "Failed to create draft via API",
        }

        args = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
            "user_id": "user@example.com",
        }
        with pytest.raises(ValueError, match="Failed to create draft via API"):
            await create_gmail_draft(**args)

    @patch("google_workspace_mcp.tools.gmail.GmailService")
    async def test_create_draft_missing_args(self, mock_gmail_service):
        """Test create_gmail_draft with missing required arguments."""
        # Mock service instance to prevent real initialization
        mock_instance = MagicMock()
        mock_gmail_service.return_value = mock_instance

        base_args = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
            "user_id": "user@example.com",
        }

        # Test empty 'to' and 'subject'
        for key in ["to", "subject"]:
            args = base_args.copy()
            args[key] = ""  # Use empty string to trigger validation
            with pytest.raises(ValueError, match="Recipient .*, subject, and body are required"):
                await create_gmail_draft(**args)

        # Test body is None
        args_body_none = base_args.copy()
        args_body_none["body"] = None
        with pytest.raises(ValueError, match="Recipient .*, subject, and body are required"):
            await create_gmail_draft(**args_body_none)


# --- Tests for delete_gmail_draft --- #


class TestDeleteGmailDraft:
    """Tests for the delete_gmail_draft function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a patched GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            # Hypothetical way to capture last error if service returns bool
            mock_service.last_error = None

            def mock_delete(*args, **kwargs):
                # Simulate success/failure and store potential error info
                draft_id = args[0] if args else kwargs.get("draft_id")
                if draft_id == "fail_me":
                    mock_service.last_error = {
                        "error": True,
                        "message": "Simulated API deletion failure",
                    }
                    return False
                mock_service.last_error = None
                return True

            mock_service.delete_draft.side_effect = mock_delete
            yield mock_service

    async def test_delete_draft_success(self, mock_gmail_service):
        """Test delete_gmail_draft successful case."""
        args = {"user_id": "user@example.com", "draft_id": "draft123"}
        result = await delete_gmail_draft(**args)

        mock_gmail_service.delete_draft.assert_called_once_with(draft_id="draft123")
        assert result == {
            "message": "Draft with ID 'draft123' deleted successfully.",
            "success": True,
        }

    async def test_delete_draft_service_failure(self, mock_gmail_service):
        """Test delete_gmail_draft when the service call fails."""
        args = {
            "user_id": "user@example.com",
            "draft_id": "fail_me",
        }  # Use ID that triggers failure

        with pytest.raises(ValueError, match="Simulated API deletion failure"):
            await delete_gmail_draft(**args)

        mock_gmail_service.delete_draft.assert_called_once_with(draft_id="fail_me")

    async def test_delete_draft_missing_id(self):
        """Test delete_gmail_draft with missing draft_id."""
        args = {"user_id": "user@example.com", "draft_id": ""}
        with pytest.raises(ValueError, match="Draft ID cannot be empty"):
            await delete_gmail_draft(**args)
