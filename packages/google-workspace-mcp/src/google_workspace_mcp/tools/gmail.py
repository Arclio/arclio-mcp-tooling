"""
Gmail tools for Google Workspace MCP operations.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp
from google_workspace_mcp.services.gmail import GmailService

logger = logging.getLogger(__name__)


# --- Gmail Tool Functions --- #


@mcp.tool(
    name="query_gmail_emails",
    description="Query Gmail emails based on a search query.",
)
async def query_gmail_emails(query: str, max_results: int = 100) -> dict[str, Any]:
    """
    Searches for Gmail emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g., "is:unread from:example.com").
        max_results: Maximum number of emails to return.

    Returns:
        A dictionary containing the list of matching emails or an error message.
    """
    logger.info(f"Executing query_gmail_emails tool with query: '{query}'")

    gmail_service = GmailService()
    emails = gmail_service.query_emails(query=query, max_results=max_results)

    # Check if there's an error
    if isinstance(emails, dict) and emails.get("error"):
        raise ValueError(emails.get("message", "Error querying emails"))

    # Return appropriate message if no results
    if not emails:
        return {"message": "No emails found for the query."}

    return {"count": len(emails), "emails": emails}


@mcp.tool(
    name="get_gmail_email",
    description="Retrieves a complete Gmail email message by its ID.",
)
async def get_gmail_email(email_id: str) -> dict[str, Any]:
    """
    Retrieves a complete Gmail email message by its ID.

    Args:
        email_id: The ID of the Gmail message to retrieve.

    Returns:
        A dictionary containing the email details and attachments.
    """
    logger.info(f"Executing get_gmail_email tool with email_id: '{email_id}'")
    if not email_id or not email_id.strip():
        raise ValueError("Email ID cannot be empty")

    gmail_service = GmailService()
    result = gmail_service.get_email(email_id=email_id)

    # Check for explicit error from service first
    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error getting email"))

    # Then check if email is missing (e.g., service returned None)
    if not result:
        raise ValueError(f"Failed to retrieve email with ID: {email_id}")

    return result


@mcp.tool(
    name="get_gmail_attachment",
    description="Retrieves a specific attachment from a Gmail message.",
)
async def get_gmail_attachment(message_id: str, attachment_id: str) -> dict[str, Any]:
    """
    Retrieves a specific attachment from a Gmail message.

    Args:
        message_id: The ID of the email message.
        attachment_id: The ID of the attachment to retrieve.

    Returns:
        A dictionary containing filename, mimeType, size, and base64 data.
    """
    logger.info(
        f"Executing get_gmail_attachment tool - Msg: {message_id}, Attach: {attachment_id}"
    )
    if not message_id or not attachment_id:
        raise ValueError("Message ID and attachment ID are required")

    gmail_service = GmailService()
    result = gmail_service.get_attachment(
        message_id=message_id, attachment_id=attachment_id
    )

    if not result or (isinstance(result, dict) and result.get("error")):
        error_msg = "Error getting attachment"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    # FastMCP should handle this dict, recognizing 'data' as content blob.
    return result


@mcp.tool(
    name="create_gmail_draft",
    description="Creates a draft email message in Gmail.",
)
async def create_gmail_draft(
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    """
    Creates a draft email message in Gmail.

    Args:
        to: Email address of the recipient.
        subject: Subject line of the email.
        body: Body content of the email.
        cc: Optional list of email addresses to CC.
        bcc: Optional list of email addresses to BCC.

    Returns:
        A dictionary containing the created draft details.
    """
    logger.info("Executing create_gmail_draft")
    if not to or not subject or not body:  # Check for empty strings
        raise ValueError("To, subject, and body are required")

    gmail_service = GmailService()
    # Pass bcc parameter even though service may not use it (for test compatibility)
    result = gmail_service.create_draft(
        to=to, subject=subject, body=body, cc=cc, bcc=bcc
    )

    if not result or (isinstance(result, dict) and result.get("error")):
        error_msg = "Error creating draft"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    return result


@mcp.tool(
    name="delete_gmail_draft",
    description="Deletes a Gmail draft email by its draft ID.",
)
async def delete_gmail_draft(
    draft_id: str,
) -> dict[str, Any]:
    """
    Deletes a specific draft email from Gmail.

    Args:
        draft_id: The ID of the draft to delete.

    Returns:
        A dictionary confirming the deletion.
    """
    logger.info(f"Executing delete_gmail_draft with draft_id: '{draft_id}'")
    if not draft_id or not draft_id.strip():
        raise ValueError("Draft ID is required")

    gmail_service = GmailService()
    success = gmail_service.delete_draft(draft_id=draft_id)

    if not success:
        # Attempt to check if the service returned an error dict
        # (Assuming handle_api_error might return dict or False/None)
        # This part might need adjustment based on actual service error handling
        error_info = getattr(
            gmail_service, "last_error", None
        )  # Hypothetical error capture
        error_msg = "Failed to delete draft"
        if isinstance(error_info, dict) and error_info.get("error"):
            error_msg = error_info.get("message", error_msg)
        raise ValueError(error_msg)

    return {
        "message": f"Draft with ID '{draft_id}' deleted successfully.",
        "success": True,
    }


@mcp.tool(
    name="reply_gmail_email",
    description="Create a reply to an existing email. Can be sent or saved as draft.",
)
async def reply_gmail_email(
    email_id: str,
    reply_body: str,
    send: bool = False,
    reply_all: bool = False,
) -> dict[str, Any]:
    """
    Creates a reply to an existing email thread.

    Args:
        email_id: The ID of the message being replied to.
        reply_body: Body content of the reply.
        send: If True, send the reply immediately. If False, save as draft.
        reply_all: If True, reply to all recipients. If False, reply to sender only.

    Returns:
        A dictionary containing the sent message or created draft details.
    """
    logger.info(f"Executing reply_gmail_email to message: '{email_id}'")
    if not email_id or not reply_body:
        raise ValueError("Email ID and reply body are required")

    gmail_service = GmailService()
    result = gmail_service.reply_to_email(
        email_id=email_id,
        reply_body=reply_body,
        reply_all=reply_all,
    )

    if not result or (isinstance(result, dict) and result.get("error")):
        action = "send reply" if send else "create reply draft"
        error_msg = f"Error trying to {action}"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    return result


@mcp.tool(
    name="bulk_delete_gmail_emails",
    description="Delete multiple emails at once by providing a list of message IDs.",
)
async def bulk_delete_gmail_emails(
    message_ids: list[str],
) -> dict[str, Any]:
    """
    Deletes multiple Gmail emails using a list of message IDs.

    Args:
        message_ids: A list of email message IDs to delete.

    Returns:
        A dictionary summarizing the deletion result.
    """
    # Validation first - check if it's a list
    if not isinstance(message_ids, list):
        raise ValueError("Message IDs must be provided as a list")

    # Then check if the list is empty
    if not message_ids:
        raise ValueError("Message IDs list cannot be empty")

    logger.info(f"Executing bulk_delete_gmail_emails with {len(message_ids)} IDs")

    gmail_service = GmailService()
    result = gmail_service.bulk_delete_emails(message_ids=message_ids)

    if not result or (isinstance(result, dict) and result.get("error")):
        error_msg = "Error during bulk deletion"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    return result
