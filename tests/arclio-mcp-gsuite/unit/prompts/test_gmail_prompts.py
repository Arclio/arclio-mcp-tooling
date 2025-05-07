"""Unit tests for Gmail prompts."""

from unittest.mock import AsyncMock  # Use AsyncMock for async context methods

import pytest
from arclio_mcp_gsuite.prompts.gmail import summarize_recent_emails
from mcp.server.fastmcp.prompts.base import UserMessage
from mcp.server.fastmcp.server import Context

pytestmark = pytest.mark.anyio


class TestSummarizeRecentEmailsPrompt:
    """Tests for the summarize_recent_emails prompt."""

    # Helper to create a mock context
    def _create_mock_context(self, resource_return_value=None, raise_exception=None):
        mock_ctx = AsyncMock(spec=Context)
        if raise_exception:
            mock_ctx.read_resource.side_effect = raise_exception
        else:
            mock_ctx.read_resource.return_value = resource_return_value
        return mock_ctx

    async def test_summarize_success(self):
        """Test successful summarization when emails are found."""
        mock_email_data = {
            "count": 2,
            "emails": [
                {
                    "subject": "Meeting Follow-up",
                    "from": "colleague@example.com",
                    "snippet": "Just wanted to follow up on our meeting...",
                },
                {
                    "subject": "Project Update",
                    "from": "boss@example.com",
                    "snippet": "Quick update on the project status...",
                },
            ],
        }
        mock_ctx = self._create_mock_context(resource_return_value=mock_email_data)
        query = "is:recent"
        args = {
            "query": query,
            "user_id": "gmail_user@example.com",
            "max_emails": 2,
            "ctx": mock_ctx,
        }

        messages = await summarize_recent_emails(**args)

        mock_ctx.read_resource.assert_awaited_once_with(f"gmail://search?q={query}")
        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_context = (
            "- From: colleague@example.com\n  Subject: Meeting Follow-up\n  Snippet: Just wanted to follow up on our meeting...\n"
            "- From: boss@example.com\n  Subject: Project Update\n  Snippet: Quick update on the project status..."
        )
        expected_content = (
            f"Please summarize the key points from these recent emails:\n\n{expected_context}"
        )
        assert messages[0].content.text == expected_content

    async def test_summarize_no_emails_found(self):
        """Test summarization when the resource returns no emails."""
        mock_email_data = {"count": 0, "emails": []}
        mock_ctx = self._create_mock_context(resource_return_value=mock_email_data)
        query = "label:archive"
        args = {"query": query, "user_id": "gmail_user@example.com", "ctx": mock_ctx}

        messages = await summarize_recent_emails(**args)

        mock_ctx.read_resource.assert_awaited_once_with(f"gmail://search?q={query}")
        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_context = "No emails found matching the query."
        expected_content = (
            f"Please summarize the key points from these recent emails:\n\n{expected_context}"
        )
        assert messages[0].content.text == expected_content

    async def test_summarize_resource_returns_message(self):
        """Test summarization when resource returns a direct message (e.g., no results)."""
        mock_email_data = {"message": "No emails found matching your query."}
        mock_ctx = self._create_mock_context(resource_return_value=mock_email_data)
        query = "is:invalid"
        args = {"query": query, "user_id": "gmail_user@example.com", "ctx": mock_ctx}

        messages = await summarize_recent_emails(**args)

        mock_ctx.read_resource.assert_awaited_once_with(f"gmail://search?q={query}")
        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_context = "No emails found matching your query."
        expected_content = (
            f"Please summarize the key points from these recent emails:\n\n{expected_context}"
        )
        assert messages[0].content.text == expected_content

    async def test_summarize_resource_value_error(self):
        """Test summarization when the resource call raises ValueError."""
        error_message = "Invalid query format"
        mock_ctx = self._create_mock_context(raise_exception=ValueError(error_message))
        query = "bad:query"
        args = {"query": query, "user_id": "gmail_user@example.com", "ctx": mock_ctx}

        messages = await summarize_recent_emails(**args)

        mock_ctx.read_resource.assert_awaited_once_with(f"gmail://search?q={query}")
        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_context = f"Error: Could not fetch emails - {error_message}"
        expected_content = (
            f"Please summarize the key points from these recent emails:\n\n{expected_context}"
        )
        assert messages[0].content.text == expected_content

    async def test_summarize_resource_other_error(self):
        """Test summarization when the resource call raises an unexpected Exception."""
        mock_ctx = self._create_mock_context(raise_exception=Exception("Network Error"))
        query = "is:inbox"
        args = {"query": query, "user_id": "gmail_user@example.com", "ctx": mock_ctx}

        messages = await summarize_recent_emails(**args)

        mock_ctx.read_resource.assert_awaited_once_with(f"gmail://search?q={query}")
        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_context = "Error: An unexpected error occurred while fetching emails."
        expected_content = (
            f"Please summarize the key points from these recent emails:\n\n{expected_context}"
        )
        assert messages[0].content.text == expected_content

    async def test_summarize_no_context(self):
        """Test calling the prompt without providing context."""
        args = {
            "query": "is:important",
            "user_id": "gmail_user@example.com",
            "ctx": None,
        }
        with pytest.raises(ValueError, match=r"Context \(ctx\) is required for this prompt."):
            await summarize_recent_emails(**args)
