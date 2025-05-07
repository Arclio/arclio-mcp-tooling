"""
Google Gmail tool handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp  # Import from central app module
from arclio_mcp_gsuite.services.gmail import GmailService

logger = logging.getLogger(__name__)


# --- Gmail Tool Functions --- #


@mcp.tool(
    name="query_gmail_emails",
    description="Query Gmail emails based on a search query.",
)
async def query_gmail_emails(query: str, user_id: str, max_results: int = 100) -> dict[str, Any]:
    """
    Query Gmail emails based on a search query.

    Args:
        query: Gmail search query (e.g., "is:unread from:example.com").
        user_id: The email address of the Google account (passed by Hub, required).
        max_results: Maximum number of emails to return (default: 100).

    Returns:
        A dictionary containing the list of emails found or an error message.
    """
    # user_id assumed available in context
    logger.info(f"Executing query_gmail_emails tool with query: '{query}'")
    # The underlying service call handles empty query correctly (all messages)

    gmail_service = GmailService()
    emails = gmail_service.query_emails(query=query, max_results=max_results)

    if isinstance(emails, dict) and emails.get("error"):
        raise ValueError(emails.get("message", "Error querying emails"))

    if not emails:
        return {"message": "No emails found matching your query."}

    # Return raw service result
    return {"count": len(emails), "emails": emails}


@mcp.tool(
    name="get_gmail_email",
    description="Retrieves a complete Gmail email message by its ID.",
)
async def get_gmail_email(email_id: str, user_id: str) -> dict[str, Any]:
    """
    Retrieves a complete Gmail email message by its ID.

    Args:
        email_id: The ID of the Gmail message to retrieve.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary containing the email details and attachments.
    """
    # user_id assumed available in context
    logger.info(f"Executing get_gmail_email tool with email_id: '{email_id}'")
    if not email_id or not email_id.strip():
        raise ValueError("Email ID cannot be empty")

    gmail_service = GmailService()
    email, attachments = gmail_service.get_email_with_attachments(email_id)

    # Check for explicit error from service first
    if isinstance(email, dict) and email.get("error"):
        raise ValueError(email.get("message", "Error getting email"))

    # Then check if email is missing (e.g., service returned None)
    if not email:
        raise ValueError(f"Failed to retrieve email with ID: {email_id}")

    # Combine email data and attachment info if successful
    # Combine email data and attachment info
    email["attachments"] = attachments
    return email


@mcp.tool(
    name="get_gmail_attachment",
    description="Retrieves a specific attachment from a Gmail message.",
)
async def get_gmail_attachment(message_id: str, attachment_id: str, user_id: str) -> dict[str, Any]:
    """
    Retrieves a specific attachment from a Gmail message.

    Args:
        message_id: The ID of the email message.
        attachment_id: The ID of the attachment to retrieve.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary containing filename, mimeType, size, and base64 data.
    """
    # user_id assumed available in context
    logger.info(f"Executing get_gmail_attachment tool - Msg: {message_id}, Attach: {attachment_id}")
    if not message_id or not attachment_id:
        raise ValueError("Message ID and Attachment ID cannot be empty")

    gmail_service = GmailService()
    result = gmail_service.get_attachment(message_id=message_id, attachment_id=attachment_id)

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
    user_id: str,
    cc: list[str] | None = None,
) -> dict[str, Any]:
    """
    Creates a draft email message in Gmail.

    Args:
        to: Email address of the recipient.
        subject: Subject line of the email.
        body: Body content of the email.
        user_id: The email address of the Google account (passed by Hub, required).
        cc: Optional list of email addresses to CC.

    Returns:
        A dictionary containing the created draft details.
    """
    logger.info(f"Executing create_gmail_draft for user {user_id}")
    if not to or not subject or body is None:  # Body can be empty string
        raise ValueError("Recipient (to), subject, and body are required")

    gmail_service = GmailService()
    # TODO: Pass user_id if needed
    result = gmail_service.create_draft(to=to, subject=subject, body=body, cc=cc)

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
    user_id: str,
) -> dict[str, Any]:
    """
    Deletes a specific draft email from Gmail.

    Args:
        draft_id: The ID of the draft to delete.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary confirming the deletion.
    """
    logger.info(f"Executing delete_gmail_draft for user {user_id} with draft_id: '{draft_id}'")
    if not draft_id or not draft_id.strip():
        raise ValueError("Draft ID cannot be empty")

    gmail_service = GmailService()
    # TODO: Pass user_id if needed
    success = gmail_service.delete_draft(draft_id=draft_id)

    if not success:
        # Attempt to check if the service returned an error dict
        # (Assuming handle_api_error might return dict or False/None)
        # This part might need adjustment based on actual service error handling
        error_info = getattr(gmail_service, "last_error", None)  # Hypothetical error capture
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
    original_message_id: str,
    reply_body: str,
    user_id: str,
    send: bool = False,
    cc: list[str] | None = None,
) -> dict[str, Any]:
    """
    Creates a reply to an existing email thread.

    Args:
        original_message_id: The ID of the message being replied to.
        reply_body: Body content of the reply.
        user_id: The email address of the Google account (passed by Hub, required).
        send: If True, send the reply immediately. If False, save as draft.
        cc: Optional list of email addresses to CC.

    Returns:
        A dictionary containing the sent message or created draft details.
    """
    logger.info(
        f"Executing reply_gmail_email for user {user_id} to message: '{original_message_id}'"
    )
    if not original_message_id or reply_body is None:
        raise ValueError("Original message ID and reply body are required")

    gmail_service = GmailService()
    # TODO: Pass user_id if needed

    # First, get the original message details needed for reply headers
    original_message = gmail_service.get_email_by_id(original_message_id, parse_body=False)
    if not original_message or (
        isinstance(original_message, dict) and original_message.get("error")
    ):
        error_msg = "Failed to retrieve original message to reply to"
        if isinstance(original_message, dict):
            error_msg = original_message.get("message", error_msg)
        raise ValueError(error_msg)

    # Now create the reply
    result = gmail_service.create_reply(
        original_message=original_message,
        reply_body=reply_body,
        send=send,
        cc=cc,
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
    user_id: str,
) -> dict[str, Any]:
    """
    Deletes multiple Gmail emails using a list of message IDs.

    Args:
        message_ids: A list of email message IDs to delete.
        user_id: The email address of the Google account (passed by Hub, required).

    Returns:
        A dictionary summarizing the deletion result.
    """
    # Validation first
    if not message_ids or not isinstance(message_ids, list):
        raise ValueError("A non-empty list of message_ids is required")

    logger.info(
        f"Executing bulk_delete_gmail_emails for user {user_id} with {len(message_ids)} IDs"
    )

    gmail_service = GmailService()
    # TODO: Pass user_id if needed
    result = gmail_service.bulk_delete_emails(message_ids=message_ids)

    if not result or (isinstance(result, dict) and result.get("error")):
        error_msg = "Error during bulk deletion"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    return result
