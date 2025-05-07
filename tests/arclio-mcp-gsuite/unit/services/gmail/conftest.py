"""
Shared fixtures for Gmail service tests.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_gmail_service():
    """Create a GmailService with mocked service attribute."""
    with (
        patch("arclio_mcp_gsuite.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        from arclio_mcp_gsuite.services.gmail import GmailService

        gmail_service = GmailService()
        # Replace the service with a mock
        gmail_service.service = MagicMock()
        return gmail_service


@pytest.fixture
def sample_email_message():
    """Return a sample Gmail API message response."""
    return {
        "id": "msg123",
        "threadId": "thread123",
        "historyId": "12345",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "This is an email snippet",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2023 10:00:00 +0000"},
                {"name": "Message-Id", "value": "<unique-id@example.com>"},
            ],
            "body": {
                "data": "VGhpcyBpcyB0aGUgZW1haWwgYm9keSBjb250ZW50Lg=="  # "This is the email body content."
            },
        },
    }
