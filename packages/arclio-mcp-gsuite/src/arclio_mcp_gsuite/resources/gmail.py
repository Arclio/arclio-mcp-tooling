"""
Google Gmail resource handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp
from arclio_mcp_gsuite.services.gmail import GmailService

logger = logging.getLogger(__name__)


# --- Gmail Resource Functions --- #


@mcp.resource("gmail://labels")
async def get_gmail_labels() -> dict[str, Any]:
    """
    List all Gmail labels for the authenticated user.

    Maps to URI: gmail://labels

    Returns:
        A dictionary containing the list of Gmail labels.
    """
    logger.info("Executing get_gmail_labels resource")

    gmail_service = GmailService()
    # This would require adding a get_labels method to GmailService
    labels = gmail_service.get_labels()

    if isinstance(labels, dict) and labels.get("error"):
        raise ValueError(labels.get("message", "Error getting Gmail labels"))

    return {"count": len(labels), "labels": labels}


@mcp.resource("gmail://unread_count")
async def get_unread_count() -> dict[str, Any]:
    """
    Get count of unread emails in the inbox.

    Maps to URI: gmail://unread_count

    Returns:
        A dictionary containing the count of unread emails.
    """
    logger.info("Executing get_unread_count resource")

    gmail_service = GmailService()
    # This would require adding a get_unread_count method to GmailService
    result = gmail_service.get_unread_count()

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error getting unread count"))

    return {"unread_count": result}
