"""
Drive tools for Google Drive operations.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.drive import DriveService

logger = logging.getLogger(__name__)


# --- Drive Tool Functions --- #


@mcp.tool(
    name="drive_search_files",
    description="Search for files in Google Drive with optional shared drive support.",
)
async def drive_search_files(
    query: str,
    page_size: int = 10,
    shared_drive_id: str | None = None,
) -> dict[str, Any]:
    """
    Search for files in Google Drive, optionally within a specific shared drive.

    Args:
        query: Search query string. Can be a simple text search or complex query with operators.
        page_size: Maximum number of files to return (1 to 1000, default 10).
        shared_drive_id: Optional shared drive ID to search within a specific shared drive.

    Returns:
        A dictionary containing a list of files or an error message.
    """
    logger.info(
        f"Executing drive_search_files with query: '{query}', page_size: {page_size}, shared_drive_id: {shared_drive_id}"
    )

    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    drive_service = DriveService()
    files = drive_service.search_files(
        query=query, page_size=page_size, shared_drive_id=shared_drive_id
    )

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(f"Search failed: {files.get('message', 'Unknown error')}")

    return {"files": files}


@mcp.tool(
    name="drive_read_file_content",
    description="Read the content of a file from Google Drive.",
)
async def drive_read_file_content(file_id: str) -> dict[str, Any]:
    """
    Read the content of a file from Google Drive.

    Args:
        file_id: The ID of the file to read.

    Returns:
        A dictionary containing the file content and metadata or an error.
    """
    logger.info(f"Executing drive_read_file_content tool with file_id: '{file_id}'")
    if not file_id or not file_id.strip():
        raise ValueError("File ID cannot be empty")

    drive_service = DriveService()
    result = drive_service.read_file_content(file_id=file_id)

    if result is None:
        raise ValueError("File not found or could not be read")

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error reading file"))

    return result


@mcp.tool(
    name="drive_upload_file",
    description="Uploads a file to Google Drive by providing its content directly.",
)
async def drive_upload_file(
    filename: str,
    content_base64: str,
    parent_folder_id: str | None = None,
    shared_drive_id: str | None = None,
) -> dict[str, Any]:
    """
    Uploads a file to Google Drive using its base64 encoded content.

    Args:
        filename: The desired name for the file in Google Drive (e.g., "report.pdf").
        content_base64: The content of the file, encoded in base64.
        parent_folder_id: Optional parent folder ID to upload the file to.
        shared_drive_id: Optional shared drive ID to upload the file to a shared drive.

    Returns:
        A dictionary containing the uploaded file metadata or an error.
    """
    logger.info(
        f"Executing drive_upload_file with filename: '{filename}', parent_folder_id: {parent_folder_id}, shared_drive_id: {shared_drive_id}"
    )
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty")
    if not content_base64 or not content_base64.strip():
        raise ValueError("File content (content_base64) cannot be empty")

    drive_service = DriveService()
    result = drive_service.upload_file_content(
        filename=filename,
        content_base64=content_base64,
        parent_folder_id=parent_folder_id,
        shared_drive_id=shared_drive_id,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error uploading file"))

    return result


@mcp.tool(
    name="drive_create_folder",
    description="Create a new folder in Google Drive.",
)
async def drive_create_folder(
    folder_name: str,
    parent_folder_id: str | None = None,
    shared_drive_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new folder in Google Drive.

    Args:
        folder_name: The name for the new folder.
        parent_folder_id: Optional parent folder ID to create the folder within.
        shared_drive_id: Optional shared drive ID to create the folder in a shared drive.

    Returns:
        A dictionary containing the created folder information.
    """
    logger.info(
        f"Executing drive_create_folder with folder_name: '{folder_name}', parent_folder_id: {parent_folder_id}, shared_drive_id: {shared_drive_id}"
    )

    if not folder_name or not folder_name.strip():
        raise ValueError("Folder name cannot be empty")

    drive_service = DriveService()
    result = drive_service.create_folder(
        folder_name=folder_name,
        parent_folder_id=parent_folder_id,
        shared_drive_id=shared_drive_id,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            f"Folder creation failed: {result.get('message', 'Unknown error')}"
        )

    return result


@mcp.tool(
    name="drive_delete_file",
    description="Delete a file from Google Drive using its file ID.",
)
async def drive_delete_file(
    file_id: str,
) -> dict[str, Any]:
    """
    Delete a file from Google Drive.

    Args:
        file_id: The ID of the file to delete.

    Returns:
        A dictionary confirming the deletion or an error.
    """
    logger.info(f"Executing drive_delete_file with file_id: '{file_id}'")
    if not file_id or not file_id.strip():
        raise ValueError("File ID cannot be empty")

    drive_service = DriveService()
    result = drive_service.delete_file(file_id=file_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error deleting file"))

    return result


@mcp.tool(
    name="drive_list_shared_drives",
    description="Lists shared drives accessible by the user.",
)
async def drive_list_shared_drives(page_size: int = 100) -> dict[str, Any]:
    """
    Lists shared drives (formerly Team Drives) that the user has access to.

    Args:
        page_size: Maximum number of shared drives to return (1 to 100, default 100).

    Returns:
        A dictionary containing a list of shared drives with their 'id' and 'name',
        or an error message.
    """
    logger.info(f"Executing drive_list_shared_drives tool with page_size: {page_size}")

    drive_service = DriveService()
    drives = drive_service.list_shared_drives(page_size=page_size)

    if isinstance(drives, dict) and drives.get("error"):
        raise ValueError(drives.get("message", "Error listing shared drives"))

    if not drives:
        return {"message": "No shared drives found or accessible."}

    return {"count": len(drives), "shared_drives": drives}
