"""
Google Docs service implementation.
"""

import logging
from typing import Any

from googleapiclient.errors import HttpError

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
