"""
Gmail service test fixtures.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.gmail import GmailService


@pytest.fixture
def mock_gmail_credentials():
    """Mock gmail credentials for testing."""
    with patch("google_workspace_mcp.auth.gauth.get_credentials"):
        yield


@pytest.fixture
def mock_gmail_service():
    """Create a GmailService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        gmail_service = GmailService()
        # Replace the private service attribute with a mock
        gmail_service._service = MagicMock()
        return gmail_service


@pytest.fixture
def sample_email_message():
    """Create a sample email message for testing."""
    return {
        "id": "test_message_id",
        "threadId": "test_thread_id",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "This is a test email message snippet...",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
            ]
        },
    }
