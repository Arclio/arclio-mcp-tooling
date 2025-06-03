"""
Slides prompts for Google Slides operations.
"""

import logging

from mcp.server.fastmcp.prompts.base import UserMessage
from mcp.server.fastmcp.server import Context

from google_workspace_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def suggest_slide_content(presentation_topic: str, slide_objective: str) -> list[UserMessage]:
    """Suggests content for a presentation slide."""
    logger.info(f"Executing suggest_slide_content prompt for topic '{presentation_topic}' and objective '{slide_objective}'")
    return [
        UserMessage(
            f"Generate content suggestions for one presentation slide.\n"
            f"Topic: {presentation_topic}\n"
            f"Objective: {slide_objective}\n"
            f"Please provide a concise Title and 3-4 bullet points."
        )
    ]


@mcp.prompt()
def create_slides_presentation(title: str, ctx: Context = None) -> list[UserMessage]:
    """Creates a new Google Slides presentation with the specified title."""
    if ctx is None:
        # Context should be automatically injected by the MCP framework
        pass

    prompt_message = UserMessage(
        role="user",
        content=f"Create a new Google Slides presentation with the title: {title}",
    )
    return [prompt_message]
