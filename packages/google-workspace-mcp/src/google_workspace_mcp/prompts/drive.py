"""Drive related MCP Prompts."""

import logging

from mcp.server.fastmcp.prompts.base import UserMessage

from google_workspace_mcp.app import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def suggest_drive_outline(topic: str) -> list[UserMessage]:
    """Suggests a document outline for a given topic."""
    logger.info(f"Executing suggest_drive_outline prompt for topic: {topic}")
    return [
        UserMessage(f"Please suggest a standard document outline (sections and subsections) for a document about: {topic}")
    ]
