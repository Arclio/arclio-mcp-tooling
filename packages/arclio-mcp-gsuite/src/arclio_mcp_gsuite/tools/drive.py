"""
Google Drive tool handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp  # Import from central app module
from arclio_mcp_gsuite.services.drive import DriveService

logger = logging.getLogger(__name__)


# --- Drive Tool Functions --- #


@mcp.tool(
    name="gdrive_search",
    description="Search for files in Google Drive based on a query string.",
)
async def gdrive_search(query: str, user_id: str, page_size: int = 10) -> dict[str, Any]:
    """
    Search for files in Google Drive based on a query string.

    Args:
        query: Search query following Google Drive query language syntax.
        user_id: The email address of the Google account (passed by Hub, required).
        page_size: Maximum number of files to return (default: 10).

    Returns:
        A dictionary containing the list of files found or an error message.
    """
    # user_id is assumed to be available in the service context or passed differently
    logger.info(f"Executing gdrive_search tool with query: '{query}'")
    if not query:
        # While the API might allow empty queries, the tool implies query is required.
        # Treat empty as a bad request for this tool endpoint.
        raise ValueError("Search query parameter cannot be empty for gdrive_search")

    drive_service = DriveService()
    # TODO: Pass user_id if needed

    files = drive_service.search_files(query=query, page_size=page_size)

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(files.get("message", "Error searching Drive"))

    if not files:
        # Return empty list instead of message for tool consistency?
        # Or keep message? Keeping message for now.
        return {"message": "No files found matching your query."}

    # Return the raw list/dict from the service
    return {"count": len(files), "files": files}


@mcp.tool(
    name="gdrive_read_file",
    description="Read the content of a file from Google Drive.",
)
async def gdrive_read_file(file_id: str, user_id: str) -> dict[str, Any]:
    """
    Read the content of a file from Google Drive.

    Args:
        file_id: The ID of the file to read.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary containing the file content and metadata, or an error.
    """
    # user_id assumed available in context
    logger.info(f"Executing gdrive_read_file tool with file_id: '{file_id}'")
    if not file_id or not file_id.strip():
        # Should be caught by URI routing, but good to double-check
        raise ValueError("File ID cannot be empty")

    drive_service = DriveService()
    # TODO: Pass user_id if needed
    result = drive_service.read_file(file_id=file_id)

    if not result:
        raise ValueError(f"Failed to read file with ID '{file_id}'")

    if result.get("error"):
        raise ValueError(result.get("message", "Error reading file"))

    # FastMCP will handle formatting based on result content (mimeType, data/content)
    return result


@mcp.tool(
    name="gdrive_upload_file",
    description="Upload a local file to Google Drive. Requires a local file path.",
)
async def gdrive_upload_file(
    file_path: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Upload a local file to Google Drive.

    Args:
        file_path: Path to the local file to upload.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary containing the uploaded file metadata or an error.
    """
    logger.info(f"Executing gdrive_upload_file for user {user_id} with path: '{file_path}'")
    if not file_path or not file_path.strip():
        raise ValueError("File path cannot be empty")

    drive_service = DriveService()
    # TODO: Pass user_id if needed
    result = drive_service.upload_file(file_path=file_path)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error uploading file"))

    return result


@mcp.tool(
    name="gdrive_delete_file",
    description="Delete a file from Google Drive using its file ID.",
)
async def gdrive_delete_file(
    file_id: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Delete a file from Google Drive.

    Args:
        file_id: The ID of the file to delete.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary confirming the deletion or an error.
    """
    logger.info(f"Executing gdrive_delete_file for user {user_id} with file_id: '{file_id}'")
    if not file_id or not file_id.strip():
        raise ValueError("File ID cannot be empty")

    drive_service = DriveService()
    # TODO: Pass user_id if needed
    result = drive_service.delete_file(file_id=file_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error deleting file"))

    return result
