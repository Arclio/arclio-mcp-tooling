"""Gmail related MCP Prompts."""

import logging

# Use specific types for clarity
from mcp.server.fastmcp.prompts.base import UserMessage
from mcp.server.fastmcp.server import Context

from arclio_mcp_gsuite.app import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def summarize_recent_emails(
    query: str, user_id: str, max_emails: int = 5, ctx: Context = None
) -> list[UserMessage]:
    """Summarizes recent emails based on a query."""
    if ctx is None:
        # This should ideally not happen if context injection works,
        # but handle defensively for direct calls or tests.
        logger.error("Context (ctx) is required for summarize_recent_emails but was not provided.")
        # Return an error message or raise an exception?
        # Raising seems more appropriate for a required dependency.
        raise ValueError("Context (ctx) is required for this prompt.")

    logger.info(f"Executing summarize_recent_emails prompt for query: '{query}', max: {max_emails}")

    email_context = "No emails found or error fetching emails."
    try:
        # Construct resource URI - ensure query is URL-encoded if needed by framework
        # Assuming FastMCP handles basic encoding or query is simple enough
        resource_uri = f"gmail://search?q={query}"
        logger.debug(f"Reading resource: {resource_uri}")

        # Call the resource via context
        email_data = await ctx.read_resource(resource_uri)
        logger.debug(f"Resource returned: {email_data}")

        if email_data and isinstance(email_data, dict) and "emails" in email_data:
            emails = email_data["emails"]
            if emails:
                summary_parts = []
                for _i, email in enumerate(emails[:max_emails]):  # Limit results
                    subject = email.get("subject", "No Subject")
                    sender = email.get("from", "Unknown Sender")
                    snippet = email.get("snippet", "...")
                    summary_parts.append(
                        f"- From: {sender}\n  Subject: {subject}\n  Snippet: {snippet}"
                    )

                if summary_parts:
                    email_context = "\n".join(summary_parts)
            else:
                email_context = "No emails found matching the query."
        elif email_data and isinstance(email_data, dict) and "message" in email_data:
            # Handle case where resource returns a message like "No emails found"
            email_context = email_data["message"]

    except ValueError as ve:
        logger.error(f"ValueError calling resource for email summary: {ve}")
        email_context = f"Error: Could not fetch emails - {ve}"
    except Exception as e:
        logger.exception(f"Unexpected error calling resource for email summary: {e}")
        email_context = "Error: An unexpected error occurred while fetching emails."

    return [
        UserMessage(f"Please summarize the key points from these recent emails:\n\n{email_context}")
    ]
