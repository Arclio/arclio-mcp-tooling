"""
Unit tests for Gmail query_gmail_emails tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.gmail import query_gmail_emails

pytestmark = pytest.mark.anyio


class TestQueryGmailEmailsTool:
    """Tests for the query_gmail_emails tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("arclio_mcp_gsuite.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_query_success(self, mock_gmail_service):
        """Test query_gmail_emails successful case."""
        mock_service_response = [
            {"id": "msg1", "subject": "Hello"},
            {"id": "msg2", "subject": "Meeting"},
        ]
        mock_gmail_service.query_emails.return_value = mock_service_response

        args = {"query": "is:unread", "user_id": "test@example.com"}
        result = await query_gmail_emails(**args)

        mock_gmail_service.query_emails.assert_called_once_with(
            query="is:unread",
            max_results=100,  # Check internal default
        )
        assert result == {"count": 2, "emails": mock_service_response}

    async def test_query_empty_query_success(self, mock_gmail_service):
        """Test query_gmail_emails with an empty query (should return all/recent)."""
        mock_service_response = [
            {"id": "msg1", "subject": "Recent Email 1"},
            {"id": "msg2", "subject": "Recent Email 2"},
        ]
        mock_gmail_service.query_emails.return_value = mock_service_response

        args = {"query": "", "user_id": "test@example.com"}
        result = await query_gmail_emails(**args)

        # Service handles empty query, tool passes it through
        mock_gmail_service.query_emails.assert_called_once_with(query="", max_results=100)
        assert result == {"count": 2, "emails": mock_service_response}

    async def test_query_no_results(self, mock_gmail_service):
        """Test query_gmail_emails when no emails match."""
        mock_gmail_service.query_emails.return_value = []

        args = {"query": "from:noone@example.com", "user_id": "test@example.com"}
        result = await query_gmail_emails(**args)

        mock_gmail_service.query_emails.assert_called_once_with(
            query="from:noone@example.com", max_results=100
        )
        assert result == {"message": "No emails found matching your query."}

    async def test_query_service_error(self, mock_gmail_service):
        """Test query_gmail_emails when the service call fails."""
        mock_gmail_service.query_emails.return_value = {
            "error": True,
            "message": "API Error: Invalid query",
        }

        args = {"query": "bad:query:", "user_id": "test@example.com"}
        with pytest.raises(ValueError, match="API Error: Invalid query"):
            await query_gmail_emails(**args)

    # No specific validation test for query needed here as empty string is allowed
