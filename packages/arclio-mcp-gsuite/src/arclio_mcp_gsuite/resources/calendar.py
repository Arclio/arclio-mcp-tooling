"""
Google Calendar resource handlers for MCP-GSuite.
"""

import logging
from typing import Any

from arclio_mcp_gsuite.app import mcp
from arclio_mcp_gsuite.services.calendar import CalendarService

logger = logging.getLogger(__name__)


# --- Calendar Resource Functions --- #


@mcp.resource("calendar://list")
async def list_calendars() -> dict[str, Any]:
    """
    Lists all calendars accessible by the user.

    Maps to URI: calendar://list

    Args:
        # user_id is passed implicitly via context.

    Returns:
        A dictionary containing the list of calendars or an error message.
    """
    # user_id assumed available in context
    logger.info("Executing list_calendars resource")

    calendar_service = CalendarService()
    calendars = calendar_service.list_calendars()

    if isinstance(calendars, dict) and calendars.get("error"):
        raise ValueError(calendars.get("message", "Error listing calendars"))

    if not calendars:
        return {"message": "No calendars found."}

    # Return raw service result
    return {"count": len(calendars), "calendars": calendars}


# Keep the existing list_calendars resource


@mcp.resource("calendar://today")
async def get_today_events() -> dict[str, Any]:
    """
    Get all events for today.

    Maps to URI: calendar://today

    Returns:
        A dictionary containing the list of today's events.
    """
    logger.info("Executing get_today_events resource")

    from datetime import datetime, timedelta

    import pytz

    calendar_service = CalendarService()

    # Get today's start and end time in RFC3339 format
    now = datetime.now(pytz.UTC)
    start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=pytz.UTC)
    end_of_day = start_of_day + timedelta(days=1)

    time_min = start_of_day.isoformat()
    time_max = end_of_day.isoformat()

    events = calendar_service.get_events(
        calendar_id="primary", time_min=time_min, time_max=time_max, max_results=50
    )

    if isinstance(events, dict) and events.get("error"):
        raise ValueError(events.get("message", "Error getting today's events"))

    if not events:
        return {"message": "No events found for today."}

    return {"count": len(events), "events": events}
