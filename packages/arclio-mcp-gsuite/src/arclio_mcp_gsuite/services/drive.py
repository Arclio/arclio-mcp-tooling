"""
Google Drive service implementation.
"""

import base64
import io
import logging
import mimetypes
import os
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from arclio_mcp_gsuite.services.base import BaseGoogleService

logger = logging.getLogger(__name__)


class DriveService(BaseGoogleService):
    """
    Service for interacting with Google Drive API.
    """

    def __init__(self):
        """Initialize the Drive service."""
        super().__init__("drive", "v3")

    def search_files(self, query: str, page_size: int = 10) -> list[dict[str, Any]]:
        """
        Search for files in Google Drive based on a query string.

        Args:
            query: The search query string (e.g., 'name contains \"report\"', 'My Important Document', '*')
            page_size: Maximum number of files to return

        Returns:
            List of file metadata dictionaries
        """
        try:
            formatted_query = ""

            if query == "*":
                formatted_query = "trashed = false"
            else:
                # Check if the query looks like it already has operators or specific syntax
                # More robust check considering common operators, quotes, and boolean logic
                has_operators_or_quotes = any(
                    op in query.lower()
                    for op in [
                        "contains",
                        "mimetype",
                        "modifiedtime",
                        "viewedbymetime",
                        "trashed",
                        "sharedwithme",
                        "owners",
                        "writers",
                        "readers",
                        "properties",
                        "appproperties",
                        "parents",
                        "and",
                        "or",
                        "not",
                        "=",
                        "<",
                        ">",
                    ]
                ) or any(quote in query for quote in ["'", '"'])

                if has_operators_or_quotes:
                    # Assume query is pre-formatted or complex.
                    # Append 'trashed = false' only if 'trashed' isn't already mentioned.
                    if "trashed" not in query.lower():
                        # Wrap original query in parentheses for safety when adding 'and'
                        formatted_query = f"({query}) and trashed = false"
                    else:
                        # Assume user handled trashed status explicitly or implicitly
                        formatted_query = query
                else:
                    # Treat as a simple phrase, use fullText contains
                    # Escape single quotes for the query string
                    # Google Drive API requires escaping ' as \\' within a string literal
                    escaped_query = query.replace("'", "\\\\'")
                    formatted_query = f"fullText contains '{escaped_query}' and trashed = false"

            logger.info(
                f"Searching Drive with formatted query: '{formatted_query}' and page size: {page_size}"
            )

            # Execute search
            results = (
                self.service.files()
                .list(
                    q=formatted_query,
                    pageSize=page_size,
                    fields="files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink)",
                )
                .execute()
            )

            files = results.get("files", [])
            logger.info(f"Found {len(files)} files matching query")

            # Ensure size is included for all files
            for file_info in files:
                file_info["size"] = file_info.get("size", 0)

            return files

        except Exception as e:
            return self.handle_api_error("search_files", e)

    def read_file(self, file_id: str) -> dict[str, Any] | None:
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
                self.service.files().get(fileId=file_id, fields="mimeType, name").execute()
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

    def _export_google_file(self, file_id: str, file_name: str, mime_type: str) -> dict[str, Any]:
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
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime_type)

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
        request = self.service.files().get_media(fileId=file_id)

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
        else:
            # Binary file
            content = base64.b64encode(content_bytes).decode("utf-8")
            return {"mimeType": mime_type, "content": content, "encoding": "base64"}

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

    def upload_file(self, file_path: str) -> dict[str, Any]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Path to the local file to upload

        Returns:
            Dict containing file metadata on success, or error information on failure
        """
        try:
            # Check if file exists locally
            if not os.path.exists(file_path):
                logger.error(f"Local file not found for upload: {file_path}")
                return {
                    "error": True,
                    "error_type": "local_file_error",
                    "message": f"Local file not found: {file_path}",
                    "operation": "upload_file",
                }

            file_name = os.path.basename(file_path)
            logger.info(f"Uploading file '{file_name}' from path: {file_path}")

            # Get file MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"

            file_metadata = {"name": file_name}

            media = MediaFileUpload(file_path, mimetype=mime_type)
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,name,mimeType,modifiedTime,size,webViewLink",
                )
                .execute()
            )

            logger.info(f"Successfully uploaded file with ID: {file.get('id')}")
            return file

        except HttpError as e:
            return self.handle_api_error("upload_file", e)
        except Exception as e:
            logger.error(f"Non-API error in upload_file: {str(e)}")
            return {
                "error": True,
                "error_type": "local_error",
                "message": f"Error uploading file: {str(e)}",
                "operation": "upload_file",
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
