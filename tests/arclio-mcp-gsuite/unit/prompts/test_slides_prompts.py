"""Unit tests for Slides prompts."""

import pytest
from arclio_mcp_gsuite.prompts.slides import suggest_slide_content
from mcp.server.fastmcp.prompts.base import UserMessage

pytestmark = pytest.mark.anyio


class TestSuggestSlideContentPrompt:
    """Tests for the suggest_slide_content prompt."""

    async def test_suggest_content_success(self):
        """Test successful generation of the slide content suggestion prompt."""
        topic = "AI in Healthcare"
        objective = "Introduce the benefits of AI diagnostics"
        args = {
            "presentation_topic": topic,
            "slide_objective": objective,
            "user_id": "slides_user@example.com",
        }

        messages = await suggest_slide_content(**args)

        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        assert messages[0].role == "user"
        expected_content = (
            f"Generate content suggestions for one presentation slide.\n"
            f"Topic: {topic}\n"
            f"Objective: {objective}\n"
            f"Please provide a concise Title and 3-4 bullet points."
        )
        assert messages[0].content.text == expected_content

    async def test_suggest_content_empty_args(self):
        """Test with empty topic and objective."""
        topic = ""
        objective = ""
        args = {
            "presentation_topic": topic,
            "slide_objective": objective,
            "user_id": "slides_user@example.com",
        }

        messages = await suggest_slide_content(**args)

        assert len(messages) == 1
        assert isinstance(messages[0], UserMessage)
        expected_content = (
            f"Generate content suggestions for one presentation slide.\n"
            f"Topic: {topic}\n"
            f"Objective: {objective}\n"
            f"Please provide a concise Title and 3-4 bullet points."
        )
        assert messages[0].content.text == expected_content
