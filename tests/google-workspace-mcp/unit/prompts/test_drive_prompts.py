"""Unit tests for Drive prompts."""

import pytest
from google_workspace_mcp.prompts.drive import suggest_drive_outline
from mcp.server.fastmcp.prompts.base import UserMessage

pytestmark = pytest.mark.anyio


class TestSuggestDriveOutlinePrompt:
    """Tests for the suggest_drive_outline prompt."""

    async def test_suggest_outline_success(self):
        """Test successful generation of the outline suggestion prompt."""
        topic = "Quarterly Business Review"
        args = {"topic": topic}

        messages = await suggest_drive_outline(**args)

        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        assert messages[0].role == "user"
        expected_content = (
            f"Please suggest a standard document outline (sections and subsections) for a document about: {topic}"
        )
        # Assuming content is stored directly in TextContent
        assert messages[0].content.text == expected_content

    async def test_suggest_outline_empty_topic(self):
        """Test with an empty topic."""
        topic = ""
        args = {"topic": topic}

        messages = await suggest_drive_outline(**args)

        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_content = (
            f"Please suggest a standard document outline (sections and subsections) for a document about: {topic}"
        )
        assert messages[0].content.text == expected_content
