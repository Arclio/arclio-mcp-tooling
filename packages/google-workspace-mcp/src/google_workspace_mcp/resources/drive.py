"""
Drive resources for Google Drive data access.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp
from google_workspace_mcp.services.drive import DriveService

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


@mcp.resource("drive://files/{file_id}/metadata")
async def get_drive_file_metadata(file_id: str) -> dict[str, Any]:
    """
    Get metadata for a specific file from Google Drive.

    Maps to URI: drive://files/{file_id}/metadata

    Args:
        file_id: The ID of the file to get metadata for

    Returns:
        A dictionary containing the file metadata.
    """
    logger.info(f"Executing get_drive_file_metadata resource for file_id: {file_id}")

    if not file_id or not file_id.strip():
        raise ValueError("File ID cannot be empty")

    drive_service = DriveService()
    metadata = drive_service.get_file_metadata(file_id=file_id)

    if isinstance(metadata, dict) and metadata.get("error"):
        raise ValueError(metadata.get("message", "Error getting file metadata"))

    return metadata
