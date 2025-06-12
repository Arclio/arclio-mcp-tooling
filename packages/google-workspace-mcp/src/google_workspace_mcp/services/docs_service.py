"""
Google Docs service implementation.
"""

import io
import logging
import urllib.parse
import urllib.request
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from google_workspace_mcp.auth import gauth
from google_workspace_mcp.services.base import BaseGoogleService

logger = logging.getLogger(__name__)


class DocsService(BaseGoogleService):
    """
    Service for interacting with the Google Docs API.
    """

    def __init__(self):
        """Initialize the Google Docs service."""
        super().__init__("docs", "v1")
        # Note: The Google Docs API client is built using 'docs', 'v1'.
        # The actual API calls will be like self.service.documents().<method>

    def create_document(self, title: str) -> dict[str, Any] | None:
        """
        Creates a new Google Document with the specified title.

        Args:
            title: The title for the new document.

        Returns:
            A dictionary containing the created document's ID and title, or an error dictionary.
        """
        try:
            logger.info(f"Creating new Google Document with title: '{title}'")
            body = {"title": title}
            document = self.service.documents().create(body=body).execute()
            # The response includes documentId, title, and other fields.
            logger.info(
                f"Successfully created document: {document.get('title')} (ID: {document.get('documentId')})"
            )
            return {
                "document_id": document.get("documentId"),
                "title": document.get("title"),
                "document_link": f"https://docs.google.com/document/d/{document.get('documentId')}/edit",
            }
        except HttpError as error:
            logger.error(f"Error creating document '{title}': {error}")
            return self.handle_api_error("create_document", error)
        except Exception as e:
            logger.exception(f"Unexpected error creating document '{title}'")
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "create_document",
            }

    def get_document_metadata(self, document_id: str) -> dict[str, Any] | None:
        """
        Retrieves metadata for a specific Google Document.

        Args:
            document_id: The ID of the Google Document.

        Returns:
            A dictionary containing document metadata (ID, title), or an error dictionary.
        """
        try:
            logger.info(f"Fetching metadata for document ID: {document_id}")
            # The 'fields' parameter can be used to specify which fields to return.
            # e.g., "documentId,title,body,revisionId,suggestionsViewMode"
            document = (
                self.service.documents()
                .get(documentId=document_id, fields="documentId,title")
                .execute()
            )
            logger.info(
                f"Successfully fetched metadata for document: {document.get('title')} (ID: {document.get('documentId')})"
            )
            return {
                "document_id": document.get("documentId"),
                "title": document.get("title"),
                "document_link": f"https://docs.google.com/document/d/{document.get('documentId')}/edit",
            }
        except HttpError as error:
            logger.error(
                f"Error fetching document metadata for ID {document_id}: {error}"
            )
            return self.handle_api_error("get_document_metadata", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error fetching document metadata for ID {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "get_document_metadata",
            }

    def get_document_content_as_markdown(
        self, document_id: str
    ) -> dict[str, Any] | None:
        """
        Retrieves the content of a Google Document as Markdown using Drive API export.

        Args:
            document_id: The ID of the Google Document (also used as Drive file ID).

        Returns:
            A dictionary with 'document_id' and 'markdown_content', or an error dictionary.
        """
        try:
            logger.info(
                f"Attempting to export document ID: {document_id} as Markdown via Drive API."
            )

            # Obtain credentials
            credentials = gauth.get_credentials()
            if not credentials:
                logger.error("Failed to obtain credentials for Drive API export.")
                return {
                    "error": True,
                    "error_type": "authentication_error",
                    "message": "Failed to obtain credentials.",
                    "operation": "get_document_content_as_markdown",
                }

            # Build a temporary Drive service client
            drive_service_client = build("drive", "v3", credentials=credentials)

            # Attempt to export as 'text/markdown'
            # Not all environments or GDoc content might support 'text/markdown' perfectly.
            # 'text/plain' is a safer fallback.
            request = drive_service_client.files().export_media(
                fileId=document_id, mimeType="text/markdown"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            content_bytes = None
            while done is False:
                status, done = downloader.next_chunk()
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            content_bytes = fh.getvalue()

            if content_bytes is None:
                raise Exception(
                    "Failed to download exported content (bytes object is None)."
                )

            markdown_content = content_bytes.decode("utf-8")
            logger.info(
                f"Successfully exported document ID: {document_id} to Markdown."
            )
            return {"document_id": document_id, "markdown_content": markdown_content}

        except HttpError as error:
            # If markdown export fails, could try 'text/plain' as fallback or just report error
            logger.warning(
                f"HTTPError exporting document {document_id} as Markdown: {error}. Falling back to text/plain might be an option if this is a common issue for certain docs."
            )
            # For now, just return the error from the attempt.
            return self.handle_api_error(
                "get_document_content_as_markdown_drive_export", error
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error exporting document {document_id} as Markdown: {e}"
            )
            return {
                "error": True,
                "error_type": "export_error",
                "message": str(e),
                "operation": "get_document_content_as_markdown",
            }

    def append_text(
        self, document_id: str, text: str, ensure_newline: bool = True
    ) -> dict[str, Any] | None:
        """
        Appends text to the end of a Google Document.

        Args:
            document_id: The ID of the Google Document.
            text: The text to append.
            ensure_newline: If True and the document is not empty, prepends a newline to the text.

        Returns:
            A dictionary indicating success or an error dictionary.
        """
        try:
            logger.info(
                f"Appending text to document ID: {document_id}. ensure_newline={ensure_newline}"
            )

            # To append at the end, we need to find the current end of the body segment.
            # Get document to find end index. Fields "body(content(endIndex))" might be enough.
            # A simpler approach for "append" is often to insert at the existing end index of the body.
            # If the document is empty, Docs API might create a paragraph.
            # If ensure_newline, and doc is not empty, prepend "\n" to text.

            document = (
                self.service.documents()
                .get(documentId=document_id, fields="body(content(endIndex,paragraph))")
                .execute()
            )
            end_index = (
                document.get("body", {}).get("content", [])[-1].get("endIndex")
                if document.get("body", {}).get("content")
                else 1
            )

            text_to_insert = text
            if (
                ensure_newline and end_index > 1
            ):  # A new doc might have an end_index of 1 for the initial implicit paragraph
                text_to_insert = "\n" + text

            requests = [
                {
                    "insertText": {
                        "location": {
                            "index": end_index
                            - 1  # Insert before the final newline of the document/body
                        },
                        "text": text_to_insert,
                    }
                }
            ]

            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            logger.info(f"Successfully appended text to document ID: {document_id}")
            return {
                "document_id": document_id,
                "success": True,
                "operation": "append_text",
            }
        except HttpError as error:
            logger.error(f"Error appending text to document {document_id}: {error}")
            return self.handle_api_error("append_text", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error appending text to document {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "append_text",
            }

    def prepend_text(
        self, document_id: str, text: str, ensure_newline: bool = True
    ) -> dict[str, Any] | None:
        """
        Prepends text to the beginning of a Google Document.

        Args:
            document_id: The ID of the Google Document.
            text: The text to prepend.
            ensure_newline: If True and the document is not empty, appends a newline to the text.

        Returns:
            A dictionary indicating success or an error dictionary.
        """
        try:
            logger.info(
                f"Prepending text to document ID: {document_id}. ensure_newline={ensure_newline}"
            )

            text_to_insert = text
            # To prepend, we generally insert at index 1 (after the initial Body segment start).
            # If ensure_newline is true, and the document isn't empty, add a newline *after* the prepended text.
            # This requires checking if the document has existing content.
            if ensure_newline:
                document = (
                    self.service.documents()
                    .get(documentId=document_id, fields="body(content(endIndex))")
                    .execute()
                )
                current_content_exists = bool(document.get("body", {}).get("content"))
                if current_content_exists:
                    text_to_insert = text + "\n"

            requests = [
                {
                    "insertText": {
                        "location": {
                            # Index 1 is typically the beginning of the document body content.
                            "index": 1
                        },
                        "text": text_to_insert,
                    }
                }
            ]

            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            logger.info(f"Successfully prepended text to document ID: {document_id}")
            return {
                "document_id": document_id,
                "success": True,
                "operation": "prepend_text",
            }
        except HttpError as error:
            logger.error(f"Error prepending text to document {document_id}: {error}")
            return self.handle_api_error("prepend_text", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error prepending text to document {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "prepend_text",
            }

    def insert_text(
        self,
        document_id: str,
        text: str,
        index: int | None = None,
        segment_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Inserts text at a specific location in a Google Document.

        Args:
            document_id: The ID of the Google Document.
            text: The text to insert.
            index: Optional. The 0-based index where the text should be inserted within the segment.
                   If None or for the main body, typically 1 for the beginning of content.
                   Behavior depends on document structure; precise indexing requires knowledge of element endIndices.
                   If inserting into an empty body, index 1 is typically used.
            segment_id: Optional. The ID of the header, footer, footnote, or inline object body.
                        If None or empty, targets the main document body.

        Returns:
            A dictionary indicating success or an error dictionary.
        """
        try:
            logger.info(
                f"Inserting text into document ID: {document_id} at index: {index}, segment: {segment_id}"
            )

            # Default to index 1 if not provided, which usually targets the start of the body content.
            # For an empty document, this effectively adds text.
            # For precise insertion into existing content, caller needs to provide a valid index.
            insert_location_index = index if index is not None else 1

            request = {
                "insertText": {
                    "location": {"index": insert_location_index},
                    "text": text,
                }
            }
            # Only add segmentId to location if it's provided
            if segment_id:
                request["insertText"]["location"]["segmentId"] = segment_id

            requests = [request]

            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            logger.info(f"Successfully inserted text into document ID: {document_id}")
            return {
                "document_id": document_id,
                "success": True,
                "operation": "insert_text",
            }
        except HttpError as error:
            logger.error(f"Error inserting text into document {document_id}: {error}")
            return self.handle_api_error("insert_text", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error inserting text into document {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "insert_text",
            }

    def batch_update(
        self, document_id: str, requests: list[dict]
    ) -> dict[str, Any] | None:
        """
        Applies a list of update requests to the specified Google Document.

        Args:
            document_id: The ID of the Google Document.
            requests: A list of Google Docs API request objects as dictionaries.
                      (e.g., InsertTextRequest, DeleteContentRangeRequest, etc.)

        Returns:
            The response from the batchUpdate API call (contains replies for each request)
            or an error dictionary.
        """
        try:
            logger.info(
                f"Executing batchUpdate for document ID: {document_id} with {len(requests)} requests."
            )
            if not requests:
                logger.warning(
                    f"batchUpdate called with no requests for document ID: {document_id}"
                )
                return {
                    "document_id": document_id,
                    "replies": [],
                    "message": "No requests provided.",
                }

            response = (
                self.service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )
            # The response object contains a list of 'replies', one for each request,
            # or it might be empty if all requests were successful without specific replies.
            # It also contains 'writeControl' and 'documentId'.
            logger.info(
                f"Successfully executed batchUpdate for document ID: {document_id}. Response contains {len(response.get('replies', []))} replies."
            )
            return {
                "document_id": response.get("documentId"),
                "replies": response.get("replies", []),
                "write_control": response.get("writeControl"),
            }
        except HttpError as error:
            logger.error(
                f"Error during batchUpdate for document {document_id}: {error}"
            )
            return self.handle_api_error("batch_update", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error during batchUpdate for document {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "batch_update",
            }

    def _validate_image_url(self, image_url: str) -> dict[str, Any] | None:
        """
        Validates an image URL for Google Docs API requirements.

        Returns None if valid, or error dict if invalid.
        """
        if not image_url or not image_url.strip():
            return {
                "error": True,
                "error_type": "validation_error",
                "message": "Image URL cannot be empty",
            }

        # Check URL length (≤ 2kB)
        if len(image_url) > 2048:
            return {
                "error": True,
                "error_type": "validation_error",
                "message": f"Image URL too long: {len(image_url)} chars (max: 2048)",
            }

        try:
            # Make HEAD request to check accessibility and get metadata
            req = urllib.request.Request(image_url, method="HEAD")
            req.add_header("User-Agent", "Google-Workspace-MCP/1.0")

            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                content_length = response.headers.get("Content-Length")

                # Check MIME type (PNG, JPEG, GIF only)
                allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif"]
                if not any(
                    allowed_type in content_type for allowed_type in allowed_types
                ):
                    return {
                        "error": True,
                        "error_type": "validation_error",
                        "message": f"Unsupported image format: {content_type}. Must be PNG, JPEG, or GIF",
                    }

                # Check file size (< 50MB)
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb >= 50:
                        return {
                            "error": True,
                            "error_type": "validation_error",
                            "message": f"Image too large: {size_mb:.1f}MB (max: 50MB)",
                        }

                return None  # Valid

        except urllib.error.HTTPError as e:
            return {
                "error": True,
                "error_type": "validation_error",
                "message": f"Image URL not accessible: HTTP {e.code} {e.reason}",
            }
        except urllib.error.URLError as e:
            return {
                "error": True,
                "error_type": "validation_error",
                "message": f"Image URL not reachable: {e.reason}",
            }
        except Exception as e:
            return {
                "error": True,
                "error_type": "validation_error",
                "message": f"Failed to validate image URL: {str(e)}",
            }

    def insert_image(
        self,
        document_id: str,
        image_url: str,
        index: int,
        width: float | None = None,
        height: float | None = None,
    ) -> dict[str, Any] | None:
        """
        Inserts an image into a Google Document from a URL at a specific index.

        Args:
            document_id: The ID of the Google Document.
            image_url: The publicly accessible URL of the image to insert.
            index: The 1-based index in the document where the image will be inserted.
            width: Optional width of the image in points (PT).
            height: Optional height of the image in points (PT).

        Returns:
            A dictionary containing the inserted image ID and success status, or an error dictionary.
        """
        try:
            logger.info(f"Inserting image into document {document_id} at index {index}")

            # Validate inputs
            if not document_id or not document_id.strip():
                raise ValueError("Document ID cannot be empty")

            if not isinstance(index, int) or index < 1:
                raise ValueError("Index must be a positive integer (1-based)")

            # Validate image URL
            validation_error = self._validate_image_url(image_url)
            if validation_error:
                return validation_error

            # Build the insert image request
            insert_request = {
                "insertInlineImage": {
                    "location": {
                        "index": index - 1  # Convert to 0-based index for API
                    },
                    "uri": image_url,
                }
            }

            # Add optional dimensions
            if width is not None or height is not None:
                insert_request["insertInlineImage"]["objectSize"] = {}
                if width is not None:
                    insert_request["insertInlineImage"]["objectSize"]["width"] = {
                        "magnitude": width,
                        "unit": "PT",
                    }
                if height is not None:
                    insert_request["insertInlineImage"]["objectSize"]["height"] = {
                        "magnitude": height,
                        "unit": "PT",
                    }

            # Execute the batch update
            result = (
                self.service.documents()
                .batchUpdate(
                    documentId=document_id, body={"requests": [insert_request]}
                )
                .execute()
            )

            # Extract the inserted image ID from the reply
            inserted_image_id = None
            if result.get("replies") and len(result["replies"]) > 0:
                reply = result["replies"][0]
                if "insertInlineImage" in reply:
                    inserted_image_id = reply["insertInlineImage"].get("objectId")

            logger.info(
                f"Successfully inserted image {inserted_image_id} into document {document_id}"
            )

            return {
                "document_id": document_id,
                "inserted_image_id": inserted_image_id,
                "success": True,
            }

        except ValueError as e:
            logger.error(f"Validation error inserting image: {e}")
            return {
                "error": True,
                "error_type": "validation_error",
                "message": str(e),
                "operation": "insert_image",
            }
        except HttpError as error:
            logger.error(f"Google Docs API error inserting image: {error}")
            return self.handle_api_error("insert_image", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error inserting image into document {document_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "insert_image",
            }
