"""
Unit tests for Gmail message parsing methods.
"""

import base64
from unittest.mock import patch

import pytest
from google_workspace_mcp.services.gmail import GmailService


class TestGmailParsingMethods:
    """Tests for Gmail message parsing methods."""

    @pytest.fixture
    def gmail_service_instance(self):
        """Create a GmailService instance for parsing tests."""
        # Mock dependencies needed just for instantiation
        with (
            patch("google_workspace_mcp.auth.gauth.get_credentials"),
            patch("googleapiclient.discovery.build"),
        ):
            return GmailService()

    def test_parse_message_basic(self, gmail_service_instance):
        """Test basic message parsing without body."""
        # Create a sample Gmail API message response
        message = {
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
            },
        }

        # Parse the message
        result = gmail_service_instance._parse_message(message, parse_body=False)

        # Check that the essential fields were extracted correctly
        assert result["id"] == "msg123"
        assert result["threadId"] == "thread123"
        assert result["snippet"] == "This is an email snippet"
        assert result["subject"] == "Test Email"
        assert result["from"] == "sender@example.com"
        assert result["to"] == "recipient@example.com"
        assert result["date"] == "Mon, 1 Jan 2023 10:00:00 +0000"
        assert result["message_id"] == "<unique-id@example.com>"

        # Body should not be present since parse_body=False
        assert "body" not in result

    def test_parse_message_with_body(self, gmail_service_instance):
        """Test message parsing with body extraction."""
        # Sample message with body content
        test_body = "This is the email body content."
        encoded_body = base64.urlsafe_b64encode(test_body.encode()).decode()

        message = {
            "id": "msg123",
            "threadId": "thread123",
            "snippet": "This is an email snippet",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "From", "value": "sender@example.com"},
                ],
                "body": {"data": encoded_body},
            },
        }

        # Mock the _extract_body method to return our test body
        with patch.object(gmail_service_instance, "_extract_body", return_value=test_body):
            # Parse the message with body
            result = gmail_service_instance._parse_message(message, parse_body=True)

            # Verify the body is included
            assert result["body"] == test_body
            assert result["mimeType"] == "text/plain"

    def test_extract_body_plain_text(self, gmail_service_instance):
        """Test body extraction from a text/plain message."""
        # Sample plain text payload
        test_body = "This is a plain text body."
        encoded_body = base64.urlsafe_b64encode(test_body.encode()).decode()

        payload = {"mimeType": "text/plain", "body": {"data": encoded_body}}

        # Extract the body
        result = gmail_service_instance._extract_body(payload)

        # Verify extraction
        assert result == test_body

    def test_extract_body_multipart(self, gmail_service_instance):
        """Test body extraction from a multipart message."""
        # Sample multipart payload with text/plain part
        test_body = "This is the plain text part."
        encoded_body = base64.urlsafe_b64encode(test_body.encode()).decode()

        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded_body}},
                {
                    "mimeType": "text/html",
                    "body": {"data": base64.urlsafe_b64encode(b"<html><body>HTML content</body></html>").decode()},
                },
            ],
        }

        # Extract the body - should prefer text/plain part
        result = gmail_service_instance._extract_body(payload)

        # Verify extraction preferring text/plain
        assert result == test_body
