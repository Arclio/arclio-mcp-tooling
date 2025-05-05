"""Drive related MCP Prompts."""

import logging

from mcp.server.fastmcp.prompts.base import UserMessage

from arclio_mcp_gsuite.app import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def suggest_drive_outline(topic: str, user_id: str) -> list[UserMessage]:
    """Suggests a document outline for a given topic."""
    logger.info(f"Executing suggest_drive_outline prompt for topic: {topic}")
    # user_id is available if needed for context, but not used in this simple prompt
    return [
        UserMessage(
            f"Please suggest a standard document outline (sections and subsections) for a document about: {topic}"
        )
    ]
