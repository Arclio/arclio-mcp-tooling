"""
Google Drive service implementation for file operations.
Provides comprehensive file management capabilities through Google Drive API.
"""

import base64
import binascii
import csv
import io
import logging
import mimetypes
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from google_workspace_mcp.services.base import BaseGoogleService

logger = logging.getLogger(__name__)

# Office Open XML mime types that are uploaded as opaque binaries to Drive
# (i.e. NOT native Google Workspace files). Without dedicated handling these
# fall through to a base64 dump that no downstream tool can read.
XLSX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
NATIVE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"


class DriveService(BaseGoogleService):
    """
    Service for interacting with Google Drive API.
    """

    def __init__(self):
        """Initialize the Drive service."""
        super().__init__("drive", "v3")

    def search_files(
        self, query: str, page_size: int = 10, shared_drive_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for files in Google Drive.

        Args:
            query: Search query string
            page_size: Maximum number of files to return (1-1000)
            shared_drive_id: Optional shared drive ID to search within a specific shared drive

        Returns:
            List of file metadata dictionaries (id, name, mimeType, etc.) or an error dictionary
        """
        try:
            logger.info(
                f"Searching files with query: '{query}', page_size: {page_size}, shared_drive_id: {shared_drive_id}"
            )

            # Validate and constrain page_size
            page_size = max(1, min(page_size, 1000))

            # Build list parameters with shared drive support
            list_params = {
                "q": query,  # Use the query directly without modification
                "pageSize": page_size,
                "fields": "files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }

            if shared_drive_id:
                list_params["driveId"] = shared_drive_id
                list_params["corpora"] = (
                    "drive"  # Search within the specified shared drive
                )
            else:
                list_params["corpora"] = (
                    "user"  # Default to user's files if no specific shared drive ID
                )

            results = self.service.files().list(**list_params).execute()
            files = results.get("files", [])

            logger.info(f"Found {len(files)} files matching query '{query}'")
            return files

        except Exception as e:
            return self.handle_api_error("search_files", e)

    def read_file_content(self, file_id: str) -> dict[str, Any] | None:
        """
        Read the content of a file from Google Drive.

        Args:
            file_id: The ID of the file to read

        Returns:
            Dict containing mimeType and content (possibly base64 encoded)
        """
        try:
            # Get file metadata
            file_metadata = (
                self.service.files()
                .get(fileId=file_id, fields="mimeType, name")
                .execute()
            )

            original_mime_type = file_metadata.get("mimeType")
            file_name = file_metadata.get("name", "Unknown")

            logger.info(
                f"Reading file '{file_name}' ({file_id}) with mimeType: {original_mime_type}"
            )

            # Handle Google Workspace files by exporting
            if original_mime_type.startswith("application/vnd.google-apps."):
                return self._export_google_file(file_id, file_name, original_mime_type)
            return self._download_regular_file(file_id, file_name, original_mime_type)

        except Exception as e:
            return self.handle_api_error("read_file", e)

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        """
        Get metadata information for a file from Google Drive.

        Args:
            file_id: The ID of the file to get metadata for

        Returns:
            Dict containing file metadata or error information
        """
        try:
            if not file_id:
                return {"error": True, "message": "File ID cannot be empty"}

            logger.info(f"Getting metadata for file with ID: {file_id}")

            # Retrieve file metadata with comprehensive field selection
            file_metadata = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, createdTime, modifiedTime, "
                    "webViewLink, webContentLink, iconLink, parents, owners, "
                    "shared, trashed, capabilities, permissions, "
                    "description, starred, explicitlyTrashed",
                    supportsAllDrives=True,
                )
                .execute()
            )

            logger.info(
                f"Successfully retrieved metadata for file: {file_metadata.get('name', 'Unknown')}"
            )
            return file_metadata

        except Exception as e:
            return self.handle_api_error("get_file_metadata", e)

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: str | None = None,
        shared_drive_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new folder in Google Drive.

        Args:
            folder_name: The name for the new folder
            parent_folder_id: Optional parent folder ID to create the folder within
            shared_drive_id: Optional shared drive ID to create the folder in a shared drive

        Returns:
            Dict containing the created folder information or error details
        """
        try:
            if not folder_name or not folder_name.strip():
                return {"error": True, "message": "Folder name cannot be empty"}

            logger.info(
                f"Creating folder '{folder_name}' with parent_folder_id: {parent_folder_id}, shared_drive_id: {shared_drive_id}"
            )

            # Build folder metadata
            folder_metadata = {
                "name": folder_name.strip(),
                "mimeType": "application/vnd.google-apps.folder",
            }

            # Set parent folder if specified
            if parent_folder_id:
                folder_metadata["parents"] = [parent_folder_id]
            elif shared_drive_id:
                # If shared drive is specified but no parent, set shared drive as parent
                folder_metadata["parents"] = [shared_drive_id]

            # Create the folder with shared drive support
            create_params = {
                "body": folder_metadata,
                "fields": "id, name, parents, webViewLink, createdTime",
                "supportsAllDrives": True,
            }

            if shared_drive_id:
                create_params["driveId"] = shared_drive_id

            created_folder = self.service.files().create(**create_params).execute()

            logger.info(
                f"Successfully created folder '{folder_name}' with ID: {created_folder.get('id')}"
            )
            return created_folder

        except Exception as e:
            return self.handle_api_error("create_folder", e)

    def _export_google_file(
        self, file_id: str, file_name: str, mime_type: str
    ) -> dict[str, Any]:
        """Export a Google Workspace file in an appropriate format."""
        # Determine export format
        export_mime_type = None
        if mime_type == "application/vnd.google-apps.document":
            export_mime_type = "text/markdown"  # Consistently use markdown for docs
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            export_mime_type = "text/csv"
        elif mime_type == "application/vnd.google-apps.presentation":
            export_mime_type = "text/plain"
        elif mime_type == "application/vnd.google-apps.drawing":
            export_mime_type = "image/png"

        if not export_mime_type:
            logger.warning(f"Unsupported Google Workspace type: {mime_type}")
            return {
                "error": True,
                "error_type": "unsupported_type",
                "message": f"Unsupported Google Workspace file type: {mime_type}",
                "mimeType": mime_type,
                "operation": "_export_google_file",
            }

        # Export the file
        try:
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_mime_type
            )

            content_bytes = self._download_content(request)
            if isinstance(content_bytes, dict) and content_bytes.get("error"):
                return content_bytes

            # Process the content based on MIME type
            if export_mime_type.startswith("text/"):
                try:
                    content = content_bytes.decode("utf-8")
                    return {
                        "mimeType": export_mime_type,
                        "content": content,
                        "encoding": "utf-8",
                    }
                except UnicodeDecodeError:
                    content = base64.b64encode(content_bytes).decode("utf-8")
                    return {
                        "mimeType": export_mime_type,
                        "content": content,
                        "encoding": "base64",
                    }
            else:
                content = base64.b64encode(content_bytes).decode("utf-8")
                return {
                    "mimeType": export_mime_type,
                    "content": content,
                    "encoding": "base64",
                }
        except Exception as e:
            return self.handle_api_error("_export_google_file", e)

    def _download_regular_file(
        self, file_id: str, file_name: str, mime_type: str
    ) -> dict[str, Any]:
        """Download a regular (non-Google Workspace) file."""
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)

        content_bytes = self._download_content(request)
        if isinstance(content_bytes, dict) and content_bytes.get("error"):
            return content_bytes

        # Process text files
        if mime_type.startswith("text/") or mime_type == "application/json":
            try:
                content = content_bytes.decode("utf-8")
                return {"mimeType": mime_type, "content": content, "encoding": "utf-8"}
            except UnicodeDecodeError:
                logger.warning(
                    f"UTF-8 decoding failed for file {file_id} ('{file_name}', {mime_type}). Using base64."
                )
                content = base64.b64encode(content_bytes).decode("utf-8")
                return {
                    "mimeType": mime_type,
                    "content": content,
                    "encoding": "base64",
                }

        # Uploaded (non-native) .xlsx workbooks: parse into CSV-per-sheet text so
        # the content is readable. Without this, an uploaded .xlsx is neither a
        # native Google Sheet (no export path) nor text, so it would fall through
        # to an unusable base64 dump.
        if mime_type == XLSX_MIME_TYPE:
            extracted = self._extract_xlsx_text(content_bytes, file_name)
            if extracted is not None:
                return {
                    "mimeType": "text/csv",
                    "content": extracted,
                    "encoding": "utf-8",
                    "sourceMimeType": mime_type,
                }
            logger.warning(
                f"xlsx extraction failed for '{file_name}' ({file_id}); returning base64."
            )

        # Binary file
        content = base64.b64encode(content_bytes).decode("utf-8")
        return {"mimeType": mime_type, "content": content, "encoding": "base64"}

    @staticmethod
    def _extract_xlsx_text(content_bytes: bytes, file_name: str) -> str | None:
        """Render an .xlsx workbook as CSV text, one block per sheet.

        Returns None if the workbook cannot be parsed, so the caller can fall
        back to base64. Multi-sheet workbooks are separated by a header line and
        a blank line; each sheet is emitted as standard CSV preserving rows and
        columns.
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            logger.warning("openpyxl not installed; cannot extract .xlsx text.")
            return None

        try:
            workbook = load_workbook(
                io.BytesIO(content_bytes), read_only=True, data_only=True
            )
        except Exception as e:
            logger.warning(f"Failed to open .xlsx '{file_name}': {e}")
            return None

        try:
            blocks: list[str] = []
            multi_sheet = len(workbook.sheetnames) > 1
            for sheet in workbook.worksheets:
                buffer = io.StringIO()
                writer = csv.writer(buffer, lineterminator="\n")
                for row in sheet.iter_rows(values_only=True):
                    writer.writerow(
                        ["" if cell is None else cell for cell in row]
                    )
                sheet_csv = buffer.getvalue().rstrip("\r\n")
                if multi_sheet:
                    blocks.append(f"# Sheet: {sheet.title}\n{sheet_csv}")
                else:
                    blocks.append(sheet_csv)
            return "\n\n".join(blocks)
        finally:
            workbook.close()

    def _download_content(self, request) -> bytes:
        """Download content from a request."""
        try:
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            return fh.getvalue()

        except Exception as e:
            return self.handle_api_error("download_content", e)

    def upload_file_content(
        self,
        filename: str,
        content_base64: str,
        parent_folder_id: str | None = None,
        shared_drive_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a file to Google Drive using its content.

        Args:
            filename: The name for the file in Google Drive.
            content_base64: Base64 encoded content of the file.
            parent_folder_id: Optional parent folder ID.
            shared_drive_id: Optional shared drive ID.

        Returns:
            Dict containing file metadata on success, or error information on failure.
        """
        try:
            logger.info(f"Uploading file '{filename}' from content.")

            # Decode the base64 content
            try:
                content_bytes = base64.b64decode(content_base64, validate=True)
            except (ValueError, TypeError, binascii.Error) as e:
                logger.error(f"Invalid base64 content for file '{filename}': {e}")
                return {
                    "error": True,
                    "error_type": "invalid_content",
                    "message": "Invalid base64 encoded content provided.",
                    "operation": "upload_file_content",
                }

            # Get file MIME type from filename
            mime_type, _ = mimetypes.guess_type(filename)
            if mime_type is None:
                mime_type = "application/octet-stream"

            file_metadata = {"name": filename}
            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]
            elif shared_drive_id:
                file_metadata["parents"] = [shared_drive_id]

            # Use MediaIoBaseUpload for in-memory content
            media = MediaIoBaseUpload(io.BytesIO(content_bytes), mimetype=mime_type)

            create_params = {
                "body": file_metadata,
                "media_body": media,
                "fields": "id,name,mimeType,modifiedTime,size,webViewLink",
                "supportsAllDrives": True,
            }
            if shared_drive_id:
                create_params["driveId"] = shared_drive_id

            file = self.service.files().create(**create_params).execute()

            logger.info(f"Successfully uploaded file with ID: {file.get('id')}")
            return file

        except HttpError as e:
            return self.handle_api_error("upload_file_content", e)
        except Exception as e:
            logger.error(f"Non-API error in upload_file_content: {str(e)}")
            return {
                "error": True,
                "error_type": "local_error",
                "message": f"Error uploading file from content: {str(e)}",
                "operation": "upload_file_content",
            }

    def convert_xlsx_to_google_sheet(
        self,
        source_file_id: str,
        new_name: str | None = None,
        parent_folder_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert an .xlsx file already in Drive into a native Google Sheet.

        Drive performs the conversion server-side when a file is copied with a
        Google Workspace target mimeType, so this creates a NEW native Sheet and
        leaves the original .xlsx untouched. The resulting Sheet is fully
        editable by all Sheets tools (ranges, formulas, formatting), unlike an
        uploaded .xlsx which can only be read.

        Args:
            source_file_id: ID of the .xlsx file in Drive to convert.
            new_name: Optional name for the new Sheet. Defaults to the source
                file's name (with any .xlsx extension stripped).
            parent_folder_id: Optional folder to place the new Sheet in. Defaults
                to the same parent(s) as the source file.

        Returns:
            Dict with the new Sheet's metadata (id, name, mimeType, webViewLink)
            or error information.
        """
        try:
            if not source_file_id:
                return {"error": True, "message": "source_file_id cannot be empty"}

            # Validate the source is actually an .xlsx before attempting a
            # conversion that would otherwise produce a confusing API error.
            source = (
                self.service.files()
                .get(
                    fileId=source_file_id,
                    fields="id, name, mimeType, parents",
                    supportsAllDrives=True,
                )
                .execute()
            )
            source_mime = source.get("mimeType")
            if source_mime != XLSX_MIME_TYPE:
                return {
                    "error": True,
                    "error_type": "unsupported_type",
                    "message": (
                        f"Source file is '{source_mime}', not an .xlsx workbook. "
                        "Only .xlsx files can be converted with this tool."
                    ),
                    "operation": "convert_xlsx_to_google_sheet",
                }

            if not new_name:
                source_name = source.get("name", "Converted Sheet")
                new_name = (
                    source_name[: -len(".xlsx")]
                    if source_name.lower().endswith(".xlsx")
                    else source_name
                )

            body: dict[str, Any] = {
                "name": new_name,
                "mimeType": NATIVE_SHEET_MIME_TYPE,
            }
            if parent_folder_id:
                body["parents"] = [parent_folder_id]

            logger.info(
                f"Converting .xlsx '{source_file_id}' to native Google Sheet '{new_name}'."
            )
            new_sheet = (
                self.service.files()
                .copy(
                    fileId=source_file_id,
                    body=body,
                    fields="id, name, mimeType, webViewLink, parents",
                    supportsAllDrives=True,
                )
                .execute()
            )

            logger.info(
                f"Successfully converted to Google Sheet with ID: {new_sheet.get('id')}"
            )
            return new_sheet

        except HttpError as e:
            return self.handle_api_error("convert_xlsx_to_google_sheet", e)
        except Exception as e:
            logger.error(f"Non-API error in convert_xlsx_to_google_sheet: {str(e)}")
            return {
                "error": True,
                "error_type": "local_error",
                "message": f"Error converting .xlsx to Google Sheet: {str(e)}",
                "operation": "convert_xlsx_to_google_sheet",
            }

    def delete_file(self, file_id: str) -> dict[str, Any]:
        """
        Delete a file from Google Drive.

        Args:
            file_id: The ID of the file to delete

        Returns:
            Dict containing success status or error information
        """
        try:
            if not file_id:
                return {"success": False, "message": "File ID cannot be empty"}

            logger.info(f"Deleting file with ID: {file_id}")
            self.service.files().delete(fileId=file_id).execute()

            return {"success": True, "message": f"File {file_id} deleted successfully"}

        except Exception as e:
            return self.handle_api_error("delete_file", e)

    def list_shared_drives(self, page_size: int = 100) -> list[dict[str, Any]]:
        """
        Lists the user's shared drives.

        Args:
            page_size: Maximum number of shared drives to return. Max is 100.

        Returns:
            List of shared drive metadata dictionaries (id, name) or an error dictionary.
        """
        try:
            logger.info(f"Listing shared drives with page size: {page_size}")
            # API allows pageSize up to 100 for drives.list
            actual_page_size = min(max(1, page_size), 100)

            results = (
                self.service.drives()
                .list(pageSize=actual_page_size, fields="drives(id, name, kind)")
                .execute()
            )
            drives = results.get("drives", [])

            # Filter for kind='drive#drive' just to be sure, though API should only return these
            processed_drives = [
                {"id": d.get("id"), "name": d.get("name")}
                for d in drives
                if d.get("kind") == "drive#drive" and d.get("id") and d.get("name")
            ]
            logger.info(f"Found {len(processed_drives)} shared drives.")
            return processed_drives
        except HttpError as error:
            logger.error(f"Error listing shared drives: {error}")
            return self.handle_api_error("list_shared_drives", error)
        except Exception as e:
            logger.exception("Unexpected error listing shared drives")
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "list_shared_drives",
            }
