"""
Google Docs tool handlers for Google Workspace MCP.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp
from google_workspace_mcp.services.docs_service import DocsService

logger = logging.getLogger(__name__)


# @mcp.tool(
#     name="docs_create_document",
# )
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


# @mcp.tool(
#     name="docs_get_document_metadata",
# )
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


@mcp.tool(
    name="docs_get_content_as_markdown",
)
async def docs_get_content_as_markdown(document_id: str) -> dict[str, Any]:
    """
    Retrieves the main textual content of a Google Document, converted to Markdown.

    Args:
        document_id: The ID of the Google Document.

    Returns:
        A dictionary containing the 'document_id' and 'markdown_content',
        or an error message.
    """
    logger.info(
        f"Executing docs_get_content_as_markdown tool for document_id: '{document_id}'"
    )
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")

    docs_service = DocsService()
    result = docs_service.get_document_content_as_markdown(document_id=document_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            result.get("message", "Error retrieving document content as Markdown")
        )

    if not result or "markdown_content" not in result:
        raise ValueError(
            f"Failed to retrieve Markdown content for document '{document_id}'."
        )

    return result


# @mcp.tool(
#     name="docs_append_text",
# )
async def docs_append_text(
    document_id: str, text: str, ensure_newline: bool = True
) -> dict[str, Any]:
    """
    Appends the given text to the end of the specified Google Document.

    Args:
        document_id: The ID of the Google Document.
        text: The text to append.
        ensure_newline: If True, prepends a newline to the text before appending,
                        if the document is not empty, to ensure the new text starts on a new line. (Default: True)

    Returns:
        A dictionary indicating success or an error message.
    """
    logger.info(f"Executing docs_append_text tool for document_id: '{document_id}'")
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")
    # Text can be empty, that's fine.

    docs_service = DocsService()
    result = docs_service.append_text(
        document_id=document_id, text=text, ensure_newline=ensure_newline
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error appending text to document"))

    if not result or not result.get("success"):
        raise ValueError(f"Failed to append text to document '{document_id}'.")

    return result


# @mcp.tool(
#     name="docs_prepend_text",
# )
async def docs_prepend_text(
    document_id: str, text: str, ensure_newline: bool = True
) -> dict[str, Any]:
    """
    Prepends the given text to the beginning of the specified Google Document.

    Args:
        document_id: The ID of the Google Document.
        text: The text to prepend.
        ensure_newline: If True, appends a newline to the text after prepending,
                        if the document was not empty, to ensure existing content starts on a new line. (Default: True)

    Returns:
        A dictionary indicating success or an error message.
    """
    logger.info(f"Executing docs_prepend_text tool for document_id: '{document_id}'")
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")
    # Text can be empty, that's fine.

    docs_service = DocsService()
    result = docs_service.prepend_text(
        document_id=document_id, text=text, ensure_newline=ensure_newline
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error prepending text to document"))

    if not result or not result.get("success"):
        raise ValueError(f"Failed to prepend text to document '{document_id}'.")

    return result


# @mcp.tool(
#     name="docs_insert_text",
# )
async def docs_insert_text(
    document_id: str, text: str, index: int | None = None, segment_id: str | None = None
) -> dict[str, Any]:
    """
    Inserts the given text at a specific location within the specified Google Document.

    Args:
        document_id: The ID of the Google Document.
        text: The text to insert.
        index: Optional. The 0-based index where the text should be inserted within the segment.
               For the main body, an index of 1 typically refers to the beginning of the content.
               Consult Google Docs API documentation for details on indexing if precise placement is needed.
               If omitted, defaults to a sensible starting position (e.g., beginning of the body).
        segment_id: Optional. The ID of a specific document segment (e.g., header, footer).
                    If omitted, the text is inserted into the main document body.

    Returns:
        A dictionary indicating success or an error message.
    """
    logger.info(
        f"Executing docs_insert_text tool for document_id: '{document_id}' at index: {index}"
    )
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")
    # Text can be empty, that's a valid insertion (though perhaps not useful).

    docs_service = DocsService()
    result = docs_service.insert_text(
        document_id=document_id, text=text, index=index, segment_id=segment_id
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error inserting text into document"))

    if not result or not result.get("success"):
        raise ValueError(f"Failed to insert text into document '{document_id}'.")

    return result


# @mcp.tool(
#     name="docs_batch_update",
# )
async def docs_batch_update(document_id: str, requests: list[dict]) -> dict[str, Any]:
    """
    Applies a list of Google Docs API update requests to the specified document.
    This is an advanced tool; requests must conform to the Google Docs API format.
    See: https://developers.google.com/docs/api/reference/rest/v1/documents/request

    Args:
        document_id: The ID of the Google Document.
        requests: A list of request objects (as dictionaries) to apply.
                  Example request: {"insertText": {"location": {"index": 1}, "text": "Hello"}}

    Returns:
        A dictionary containing the API response from the batchUpdate call (includes replies for each request),
        or an error message.
    """
    logger.info(
        f"Executing docs_batch_update tool for document_id: '{document_id}' with {len(requests)} requests."
    )
    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list.")
    # Further validation of individual request structures is complex here and usually
    # left to the API, but basic check for list is good.

    docs_service = DocsService()
    result = docs_service.batch_update(document_id=document_id, requests=requests)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            result.get("message", "Error executing batch update on document")
        )

    if not result:  # Should be caught by error dict check
        raise ValueError(f"Failed to execute batch update on document '{document_id}'.")

    return result  # Return the full response which includes documentId and replies


# @mcp.tool(
#     name="docs_insert_image",
# )
async def docs_insert_image(
    document_id: str,
    image_url: str,
    index: int,
    width: float | None = None,
    height: float | None = None,
) -> dict[str, Any]:
    """
    Inserts an image into a Google Document from a URL at a specific index.

    Args:
        document_id: The ID of the Google Document.
        image_url: The publicly accessible URL of the image to insert.
        index: The 1-based index in the document where the image will be inserted.
        width: Optional width of the image in points (PT).
        height: Optional height of the image in points (PT).

    Returns:
        A dictionary containing the inserted image ID and success status, or an error message.
    """
    logger.info(
        f"Executing docs_insert_image tool for document_id: '{document_id}' at index: {index}"
    )

    if not document_id or not document_id.strip():
        raise ValueError("Document ID cannot be empty.")

    if not image_url or not image_url.strip():
        raise ValueError("Image URL cannot be empty.")

    if not isinstance(index, int) or index < 1:
        raise ValueError("Index must be a positive integer (1-based).")

    if width is not None and (not isinstance(width, int | float) or width <= 0):
        raise ValueError("Width must be a positive number.")

    if height is not None and (not isinstance(height, int | float) or height <= 0):
        raise ValueError("Height must be a positive number.")

    docs_service = DocsService()
    result = docs_service.insert_image(
        document_id=document_id,
        image_url=image_url,
        index=index,
        width=width,
        height=height,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error inserting image into document"))

    if not result or not result.get("success"):
        raise ValueError(f"Failed to insert image into document '{document_id}'.")

    return result
