"""
Google Docs tool handlers for Google Workspace MCP.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp
from google_workspace_mcp.services.docs_service import DocsService

logger = logging.getLogger(__name__)


@mcp.tool(
    name="docs_create_document",
    description="Creates a new Google Document with a specified title.",
)
async def docs_create_document(title: str) -> dict[str, Any]:
    """
    Creates a new, empty Google Document.

    Args:
        title: The title for the new Google Document.

    Returns:
        A dictionary containing the 'document_id', 'title', and 'document_link' of the created document,
        or an error message.
    """
    logger.info(f"Executing docs_create_document tool with title: '{title}'")
    if not title or not title.strip():
        raise ValueError("Document title cannot be empty.")

    docs_service = DocsService()
    result = docs_service.create_document(title=title)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating document"))

    if not result or not result.get("document_id"):
        raise ValueError(
            f"Failed to create document '{title}' or did not receive a document ID."
        )

    return result


@mcp.tool(
    name="docs_get_document_metadata",
    description="Retrieves metadata (like title and ID) for a Google Document.",
)
async def docs_get_document_metadata(document_id: str) -> dict[str, Any]:
    """
    Retrieves metadata for a specific Google Document.

    Args:
        document_id: The ID of the Google Document.

    Returns:
        A dictionary containing the document's 'document_id', 'title', and 'document_link',
        or an error message.
    """
    logger.info(
        f"Executing docs_get_document_metadata tool for document_id: '{document_id}'"
    )
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")

    docs_service = DocsService()
    result = docs_service.get_document_metadata(document_id=document_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error retrieving document metadata"))

    if not result or not result.get("document_id"):
        raise ValueError(f"Failed to retrieve metadata for document '{document_id}'.")

    return result
