"""
Unit tests for Gmail query_gmail_emails tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.gmail import query_gmail_emails

pytestmark = pytest.mark.anyio


class TestQueryGmailEmails:
    """Tests for the query_gmail_emails tool function."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Patch GmailService for tool tests."""
        with patch("google_workspace_mcp.tools.gmail.GmailService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_query_emails_success(self, mock_gmail_service):
        """Test query_gmail_emails successful case."""
        mock_service_response = [
            {"id": "msg1", "snippet": "First email snippet"},
            {"id": "msg2", "snippet": "Second email snippet"},
        ]
        mock_gmail_service.query_emails.return_value = mock_service_response

        args = {"query": "is:unread"}
        result = await query_gmail_emails(**args)

        mock_gmail_service.query_emails.assert_called_once_with(query="is:unread", max_results=100)
        assert result == {"count": 2, "emails": mock_service_response}

    async def test_query_emails_with_max_results(self, mock_gmail_service):
        """Test query_gmail_emails with custom max_results."""
        mock_service_response = [{"id": "msg1", "snippet": "Email snippet"}]
        mock_gmail_service.query_emails.return_value = mock_service_response

        args = {"query": "from:test@example.com", "max_results": 5}
        result = await query_gmail_emails(**args)

        mock_gmail_service.query_emails.assert_called_once_with(query="from:test@example.com", max_results=5)
        assert result == {"count": 1, "emails": mock_service_response}

    async def test_query_emails_no_results(self, mock_gmail_service):
        """Test query_gmail_emails when no emails are found."""
        mock_gmail_service.query_emails.return_value = []

        args = {"query": "nonexistent"}
        result = await query_gmail_emails(**args)

        mock_gmail_service.query_emails.assert_called_once_with(query="nonexistent", max_results=100)
        assert result == {"message": "No emails found for the query."}

    async def test_query_emails_service_error(self, mock_gmail_service):
        """Test query_gmail_emails when the service returns an error."""
        mock_gmail_service.query_emails.return_value = {
            "error": True,
            "message": "API Error: Invalid query",
        }

        args = {"query": "invalid:syntax"}
        with pytest.raises(ValueError, match="API Error: Invalid query"):
            await query_gmail_emails(**args)

    # No specific validation test for query needed here as empty string is allowed
