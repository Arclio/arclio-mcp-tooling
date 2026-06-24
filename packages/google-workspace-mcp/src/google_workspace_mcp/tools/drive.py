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
    include_trashed: bool = False,
) -> dict[str, Any]:
    """
    Search for files in Google Drive, optionally within a specific shared drive.

    Args:
        query: Search query string. Can be a simple text search or complex query with operators.
            Note: in Drive query syntax, literal apostrophes inside quoted values must be
            escaped as \\' (e.g. name = 'John\\'s Files').
        page_size: Maximum number of files to return (1 to 1000, default 10).
        shared_drive_id: Optional shared drive ID to search within a specific shared drive.
        include_trashed: Whether to include trashed files in results (default False).

    Returns:
        A dictionary containing a list of files or an error message.
    """
    logger.info(
        f"Executing drive_search_files with query: '{query}', page_size: {page_size}, "
        f"shared_drive_id: {shared_drive_id}, include_trashed: {include_trashed}"
    )

    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    # Exclude trashed files unless explicitly requested. Only append the
    # constraint when the caller hasn't already used a trashed OPERATOR clause
    # (match "trashed=" / "trashed =", not the word inside a quoted value).
    effective_query = query.strip()
    has_trashed_clause = "trashed=" in effective_query or "trashed =" in effective_query
    if not include_trashed and not has_trashed_clause:
        effective_query = f"({effective_query}) and trashed = false"

    drive_service = DriveService()
    files = drive_service.search_files(
        query=effective_query,
        page_size=page_size,
        shared_drive_id=shared_drive_id,
        include_shared_drives=shared_drive_id is None,
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
    description=(
        "Uploads a file to Google Drive by providing its content directly. The "
        "file is private by default; pass share=true to grant 'anyone with the "
        "link → reader' so it is fetchable via its webContentLink without auth."
    ),
)
async def drive_upload_file(
    filename: str,
    content_base64: str,
    parent_folder_id: str | None = None,
    shared_drive_id: str | None = None,
    share: bool = False,
) -> dict[str, Any]:
    """
    Uploads a file to Google Drive using its base64 encoded content.

    Args:
        filename: The desired name for the file in Google Drive (e.g., "report.pdf").
        content_base64: The content of the file, encoded in base64.
        parent_folder_id: Optional parent folder ID to upload the file to.
        shared_drive_id: Optional shared drive ID to upload the file to a shared drive.
        share: When True, grant "anyone with the link → reader" so the returned
            webContentLink is fetchable without authentication. Defaults to False
            (the file stays private).

    Returns:
        A dictionary containing the uploaded file metadata (including
        webContentLink when shared) or an error.
    """
    logger.info(
        f"Executing drive_upload_file with filename: '{filename}', "
        f"parent_folder_id: {parent_folder_id}, shared_drive_id: {shared_drive_id}, "
        f"share: {share}"
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
        share=share,
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


@mcp.tool(
    name="drive_convert_xlsx_to_google_sheet",
    description=(
        "Convert an .xlsx file already in Google Drive into a native Google "
        "Sheet. Creates a new Sheet (the original .xlsx is kept) that is fully "
        "editable by the Sheets tools. Use this when you need to edit, not just "
        "read, an uploaded spreadsheet."
    ),
)
async def drive_convert_xlsx_to_google_sheet(
    source_file_id: str,
    new_name: str | None = None,
    parent_folder_id: str | None = None,
) -> dict[str, Any]:
    """
    Convert an uploaded .xlsx workbook into a native Google Sheet.

    Drive converts the file server-side, producing a new native Sheet while
    leaving the original .xlsx in place. Unlike reading an .xlsx (which only
    returns its content as CSV), the resulting Sheet can be edited with the full
    set of Sheets tools.

    Args:
        source_file_id: ID of the .xlsx file in Drive to convert.
        new_name: Optional name for the new Sheet. Defaults to the source file's
            name with any '.xlsx' extension removed.
        parent_folder_id: Optional folder for the new Sheet. Defaults to the
            source file's location.

    Returns:
        A dictionary with the new Google Sheet's metadata (id, name, mimeType,
        webViewLink), or an error message.
    """
    logger.info(
        f"Executing drive_convert_xlsx_to_google_sheet for source: {source_file_id}"
    )

    if not source_file_id or not source_file_id.strip():
        raise ValueError("source_file_id cannot be empty")

    drive_service = DriveService()
    result = drive_service.convert_xlsx_to_google_sheet(
        source_file_id=source_file_id,
        new_name=new_name,
        parent_folder_id=parent_folder_id,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            f"Conversion failed: {result.get('message', 'Unknown error')}"
        )

    return result


@mcp.tool(
    name="drive_move_file",
    description=(
        "Move a file into a target folder (removing its current parents). Use "
        "this to relocate a newly created native file out of Drive root into "
        "its intended folder so deliverables are not stranded."
    ),
)
async def drive_move_file(file_id: str, target_folder_id: str) -> dict[str, Any]:
    """
    Move a Drive file into a destination folder.

    Args:
        file_id: ID of the file to move.
        target_folder_id: ID of the destination folder.

    Returns:
        A dictionary with the file's id, name, and new parents, or an error.
    """
    logger.info(f"Executing drive_move_file: {file_id} -> {target_folder_id}")

    if not file_id or not file_id.strip():
        raise ValueError("file_id cannot be empty")
    if not target_folder_id or not target_folder_id.strip():
        raise ValueError("target_folder_id cannot be empty")

    drive_service = DriveService()
    result = drive_service.move_file(
        file_id=file_id, target_folder_id=target_folder_id
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(f"Move failed: {result.get('message', 'Unknown error')}")

    return result


@mcp.tool(
    name="drive_search_files_in_folder",
    description="Search for files or folders within a specific folder ID (or a Shared Drive ID).",
)
async def drive_search_files_in_folder(
    folder_id: str,
    query: str = "",
    page_size: int = 10,
) -> dict[str, Any]:
    """
    Search for files or folders within a specific folder ID. Trashed items are excluded.

    Works for both regular folders and Shared Drives (pass the Shared Drive's ID as folder_id).

    Args:
        folder_id: The ID of the folder or Shared Drive to search within.
        query: Optional Drive query string. If empty, returns all items in the folder.
            Example to find only sub-folders: "mimeType = 'application/vnd.google-apps.folder'".
        page_size: Maximum number of files to return (1 to 1000, default 10).

    Returns:
        A dictionary with the folder_id and a list of files/folders.
    """
    logger.info(
        f"Executing drive_search_files_in_folder with folder_id: '{folder_id}', "
        f"query: '{query}', page_size: {page_size}"
    )

    if not folder_id or not folder_id.strip():
        raise ValueError("Folder ID cannot be empty")

    folder_constraint = f"'{folder_id}' in parents and trashed = false"
    if query and query.strip():
        # `query` is a structured Drive query; pass it through verbatim (the
        # caller escapes apostrophes inside their own value strings, as with
        # drive_search_files). Escaping the whole string here would corrupt the
        # query's own quote delimiters.
        combined_query = f"{query.strip()} and {folder_constraint}"
    else:
        combined_query = folder_constraint

    drive_service = DriveService()
    files = drive_service.search_files(
        query=combined_query,
        page_size=page_size,
        include_shared_drives=True,  # folder searches may span shared drives
    )

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(
            f"Folder search failed: {files.get('message', 'Unknown error')}"
        )

    return {"folder_id": folder_id, "files": files}


@mcp.tool(
    name="drive_find_folder_by_name",
    description=(
        "Find folders by name (exact match first, then partial), auto-escaping "
        "apostrophes. Optionally also search for files inside the found folder."
    ),
)
async def drive_find_folder_by_name(
    folder_name: str,
    include_files: bool = False,
    file_query: str = "",
    page_size: int = 10,
    shared_drive_id: str | None = None,
) -> dict[str, Any]:
    """
    Find folders by name using a two-step search: exact match, then partial match.

    Automatically handles apostrophes in folder names and queries. Trashed items
    are excluded. Finds regular folders within My Drive or a Shared Drive; it does
    NOT list Shared Drives themselves (use drive_list_shared_drives for that).

    Args:
        folder_name: The folder name to search for.
        include_files: Also search for files within the first matched folder (default False).
        file_query: Optional query for files within the folder (only if include_files=True).
        page_size: Maximum number of files to return (1 to 1000, default 10).
        shared_drive_id: Optional shared drive ID to scope the search.

    Returns:
        A dictionary with folders_found and, if requested, file results.
    """
    logger.info(
        f"Executing drive_find_folder_by_name with folder_name: '{folder_name}', "
        f"include_files: {include_files}, file_query: '{file_query}', "
        f"page_size: {page_size}, shared_drive_id: {shared_drive_id}"
    )

    if not folder_name or not folder_name.strip():
        raise ValueError("Folder name cannot be empty")

    drive_service = DriveService()
    escaped_name = folder_name.strip().replace("'", "\\'")
    folder_mime = "application/vnd.google-apps.folder"

    # Step 1: exact match
    exact_query = (
        f"name = '{escaped_name}' and mimeType = '{folder_mime}' and trashed = false"
    )
    folders = drive_service.search_files(
        query=exact_query,
        page_size=5,
        shared_drive_id=shared_drive_id,
        include_shared_drives=True,
    )

    # Step 2: partial match fallback
    if not folders:
        contains_query = (
            f"name contains '{escaped_name}' and mimeType = '{folder_mime}' "
            "and trashed = false"
        )
        folders = drive_service.search_files(
            query=contains_query,
            page_size=5,
            shared_drive_id=shared_drive_id,
            include_shared_drives=True,
        )

    if isinstance(folders, dict) and folders.get("error"):
        raise ValueError(
            f"Folder search failed: {folders.get('message', 'Unknown error')}"
        )

    result: dict[str, Any] = {
        "folder_name": folder_name,
        "folders_found": folders,
        "folder_count": len(folders) if folders else 0,
    }

    if not include_files:
        return result

    if not folders:
        result["message"] = f"No folders found with name matching '{folder_name}'"
        return result

    target_folder = folders[0]
    folder_constraint = f"'{target_folder['id']}' in parents and trashed = false"

    if file_query and file_query.strip():
        clean = file_query.strip()
        if " " not in clean and ":" not in clean and "=" not in clean:
            # Bare keyword -> wrap in a full-text predicate, escaping the
            # apostrophes in the keyword value we interpolate.
            escaped = clean.replace("'", "\\'")
            wrapped = f"fullText contains '{escaped}'"
        else:
            # Already a structured query; pass through verbatim (caller escapes
            # apostrophes inside their own value strings).
            wrapped = clean
        combined_query = f"{wrapped} and {folder_constraint}"
    else:
        combined_query = folder_constraint

    files = drive_service.search_files(
        query=combined_query, page_size=page_size, include_shared_drives=True
    )

    if isinstance(files, dict) and files.get("error"):
        raise ValueError(
            f"File search in folder failed: {files.get('message', 'Unknown error')}"
        )

    result["target_folder"] = target_folder
    result["files"] = files
    result["file_count"] = len(files) if files else 0
    return result
