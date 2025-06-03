"""
Unit tests for GmailService.query_emails method.
"""

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError


class TestQueryEmails:
    """Tests for the GmailService.query_emails method."""

    def test_query_emails_success(self, mock_gmail_service, sample_email_message):
        """Test successful email query with results."""
        # Mock data for the API response
        mock_messages = [{"id": "msg1", "threadId": "thread1"}]
        mock_list_response = {"messages": mock_messages}

        # Mock for list method
        mock_execute_list = MagicMock(return_value=mock_list_response)
        mock_gmail_service.service.users.return_value.messages.return_value.list.return_value.execute = mock_execute_list

        # Mock for get method (message details)
        mock_execute_get = MagicMock(return_value=sample_email_message)
        mock_gmail_service.service.users.return_value.messages.return_value.get.return_value.execute = mock_execute_get

        # Mock parse_message to return structured data
        mock_parsed_message = {
            "id": "msg1",
            "threadId": "thread1",
            "subject": "Test Subject",
            "from": "sender@example.com",
        }

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                mock_gmail_service,
                "_parse_message",
                lambda *args, **kwargs: mock_parsed_message,
            )

            # Call the method with query parameters
            result = mock_gmail_service.query_emails(query="is:unread", max_results=10)

            # Verify correct API calls
            mock_gmail_service.service.users.return_value.messages.return_value.list.assert_called_once_with(
                userId="me", maxResults=10, q="is:unread"
            )
            mock_gmail_service.service.users.return_value.messages.return_value.get.assert_called_once_with(
                userId="me", id="msg1"
            )

            # Verify the result format
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["id"] == "msg1"
            assert result[0]["subject"] == "Test Subject"
            assert result[0]["from"] == "sender@example.com"

    def test_query_emails_empty_results(self, mock_gmail_service):
        """Test email query with no matching emails."""
        # Mock an empty result
        mock_list_response = {}  # No messages key

        # Setup the execute mock
        mock_execute = MagicMock(return_value=mock_list_response)
        mock_gmail_service.service.users.return_value.messages.return_value.list.return_value.execute = mock_execute

        # Call the method
        result = mock_gmail_service.query_emails(query="nonexistent", max_results=10)

        # Verify the result is an empty list
        assert isinstance(result, list)
        assert len(result) == 0

    def test_query_emails_pagination(self, mock_gmail_service):
        """Test email query with pagination."""
        # Setup mock responses for multiple pages
        page1_messages = [{"id": "msg1", "threadId": "thread1"}]
        page2_messages = [{"id": "msg2", "threadId": "thread1"}]

        page1_response = {"messages": page1_messages, "nextPageToken": "page2_token"}
        page2_response = {"messages": page2_messages}

        # Setup mock to use the side effects
        mock_gmail_service.service.users.return_value.messages.return_value.list.return_value.execute.side_effect = [
            page1_response,
            page2_response,
        ]

        # Mock get method to return message details
        mock_gmail_service.service.users.return_value.messages.return_value.get.return_value.execute.side_effect = [
            {"id": "msg1", "payload": {"headers": []}},
            {"id": "msg2", "payload": {"headers": []}},
        ]

        # Mock parse_message
        parsed_messages = [
            {"id": "msg1", "subject": "Message 1"},
            {"id": "msg2", "subject": "Message 2"},
        ]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                mock_gmail_service,
                "_parse_message",
                lambda txt, **kwargs: (parsed_messages[0] if txt["id"] == "msg1" else parsed_messages[1]),
            )

            # Call the method with max_results=2
            result = mock_gmail_service.query_emails(query="test", max_results=2)

            # Verify pagination was handled correctly
            assert len(result) == 2
            assert result[0]["id"] == "msg1"
            assert result[1]["id"] == "msg2"

    def test_query_emails_api_error(self, mock_gmail_service):
        """Test email query with API error."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission Denied"}}')

        # Setup the side_effect to raise the error
        mock_gmail_service.service.users.return_value.messages.return_value.list.return_value.execute.side_effect = http_error

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission Denied",
            "operation": "query_emails",
        }
        mock_gmail_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_gmail_service.query_emails(query="test")

        # Verify error handling
        mock_gmail_service.handle_api_error.assert_called_once_with("query_emails", http_error)
        assert result == expected_error
