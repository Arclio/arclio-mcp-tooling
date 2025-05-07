"""Calendar related MCP Prompts."""

import logging

from mcp.server.fastmcp.prompts.base import UserMessage
from mcp.server.fastmcp.server import Context

from arclio_mcp_gsuite.app import mcp

logger = logging.getLogger(__name__)


@mcp.prompt()
async def draft_calendar_agenda(
    event_id: str,
    user_id: str,
    calendar_id: str = "primary",
    ctx: Context = None,  # Add default None for ctx
) -> list[UserMessage]:
    """Drafts a meeting agenda based on event info (currently simulated)."""
    logger.info(
        f"Executing draft_calendar_agenda prompt for event '{event_id}' on calendar '{calendar_id}'"
    )
    # TODO: Replace simulation with actual call to get event details via resource
    # try:
    #     event_details_dict = await ctx.read_resource(f"calendar://{calendar_id}/event/{event_id}")
    #     event_details = f"Meeting: {event_details_dict.get('summary', 'No Title')}\n"
    #     event_details += f"Time: {event_details_dict.get('start',{}).get('dateTime')} - {event_details_dict.get('end',{}).get('dateTime')}\n"
    #     event_details += f"Description: {event_details_dict.get('description', 'N/A')}"
    # except Exception as e:
    #     logger.warning(f"Could not get event details for {event_id}: {e}")
    #     event_details = f"Meeting: {event_id} on Calendar: {calendar_id} - Details unavailable."

    # Simulate details for now
    event_details = f"Meeting: {event_id} on Calendar: {calendar_id} - Details unavailable."

    return [
        UserMessage(
            f"Please draft a simple meeting agenda based on the following event information:\n\n{event_details}"
        )
    ]
