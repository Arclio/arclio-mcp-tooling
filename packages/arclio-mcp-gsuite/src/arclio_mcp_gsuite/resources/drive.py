"""
Google Drive resource handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp
from arclio_mcp_gsuite.services.drive import DriveService

logger = logging.getLogger(__name__)


# --- Drive Resource Functions --- #


@mcp.resource("drive://recent")
async def get_recent_files() -> dict[str, Any]:
    """
    Get recently modified files (last 7 days).

    Maps to URI: drive://recent

    Returns:
        A dictionary containing the list of recently modified files.
    """
    logger.info("Executing get_recent_files resource")

    drive_service = DriveService()
    # Using the existing search_files method with a fixed query
    query = "modifiedTime > 'now-7d'"
    files = drive_service.search_files(query=query, page_size=10)

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(files.get("message", "Error getting recent files"))

    if not files:
        return {"message": "No recent files found."}

    return {"count": len(files), "files": files}


@mcp.resource("drive://shared")
async def get_shared_files() -> dict[str, Any]:
    """
    Get files shared with the user.

    Maps to URI: drive://shared

    Returns:
        A dictionary containing the list of shared files.
    """
    logger.info("Executing get_shared_files resource")

    drive_service = DriveService()
    # Using the existing search_files method with a fixed query
    query = "sharedWithMe=true"
    files = drive_service.search_files(query=query, page_size=10)

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(files.get("message", "Error getting shared files"))

    if not files:
        return {"message": "No shared files found."}

    return {"count": len(files), "files": files}
