"""
Google Calendar tool handlers for Google Workspace MCP.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.calendar import CalendarService

logger = logging.getLogger(__name__)


# --- Calendar Tool Functions --- #


# @mcp.tool(
#     name="list_calendars",
# )
# async def list_calendars() -> dict[str, Any]:
#     """
#     Lists all calendars accessible by the user.

#     Returns:
#         A dictionary containing the list of calendars or an error message.
#     """
#     logger.info("Executing list_calendars tool")

#     calendar_service = CalendarService()
#     calendars = calendar_service.list_calendars()

#     if isinstance(calendars, dict) and calendars.get("error"):
#         raise ValueError(calendars.get("message", "Error listing calendars"))

#     if not calendars:
#         return {"message": "No calendars found."}

#     # Return raw service result
#     return {"count": len(calendars), "calendars": calendars}


# @mcp.tool(
#     name="calendar_get_events",
# )
async def calendar_get_events(
    time_min: str,
    time_max: str,
    calendar_id: str = "primary",
    max_results: int = 250,
    show_deleted: bool = False,
) -> dict[str, Any]:
    """
    Retrieve calendar events within a specified time range.

    Args:
        time_min: Start time in RFC3339 format (e.g., "2024-01-01T00:00:00Z").
        time_max: End time in RFC3339 format (e.g., "2024-01-01T23:59:59Z").
        calendar_id: ID of the calendar (defaults to 'primary').
        max_results: Maximum number of events to return (default: 250).
        show_deleted: Whether to include deleted events (default: False).

    Returns:
        A dictionary containing the list of events or an error message.
    """
    logger.info(f"Executing calendar_get_events tool on calendar '{calendar_id}' between {time_min} and {time_max}")

    if not calendar_id:
        raise ValueError("calendar_id parameter is required")
    if not time_min:
        raise ValueError("time_min parameter is required")
    if not time_max:
        raise ValueError("time_max parameter is required")

    calendar_service = CalendarService()
    events = calendar_service.get_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=max_results,
        show_deleted=show_deleted,
    )

    if isinstance(events, dict) and events.get("error"):
        raise ValueError(events.get("message", "Error getting calendar events"))

    if not events:
        return {"message": "No events found for the specified time range."}

    # Return raw service result
    return {"count": len(events), "events": events}


# @mcp.tool(
#     name="calendar_get_event_details",
# )
async def calendar_get_event_details(event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
    """
    Retrieves details for a specific event in a Google Calendar.

    Args:
        event_id: The ID of the event to retrieve.
        calendar_id: The ID of the calendar containing the event. Defaults to 'primary'.

    Returns:
        A dictionary containing the event details (summary, start, end, description, attendees, etc.),
        or an error message.
    """
    logger.info(f"Executing calendar_get_event_details tool for event_id: '{event_id}', calendar_id: '{calendar_id}'")
    if not event_id or not event_id.strip():
        raise ValueError("Event ID cannot be empty.")
    if not calendar_id or not calendar_id.strip():
        raise ValueError("Calendar ID cannot be empty.")  # Ensure calendar_id is also validated

    calendar_service = CalendarService()
    event_details = calendar_service.get_event_details(event_id=event_id, calendar_id=calendar_id)

    if isinstance(event_details, dict) and event_details.get("error"):
        raise ValueError(event_details.get("message", "Error retrieving event details"))

    if not event_details:  # Should be caught by error dict check
        raise ValueError(f"Failed to retrieve details for event '{event_id}'")

    return event_details


# @mcp.tool(
#     name="create_calendar_event",
# )
async def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    location: str | None = None,
    description: str | None = None,
    attendees: list[str] | None = None,
    send_notifications: bool = True,
    timezone: str | None = None,
) -> dict[str, Any]:
    """
    Create a new calendar event.

    Args:
        summary: Title of the event.
        start_time: Start time in RFC3339 format (e.g. 2024-12-01T10:00:00Z).
        end_time: End time in RFC3339 format (e.g. 2024-12-01T11:00:00Z).
        calendar_id: Calendar ID (defaults to "primary").
        location: Location of the event (optional).
        description: Description or notes (optional).
        attendees: List of attendee email addresses (optional).
        send_notifications: Whether to send notifications to attendees (default True).
        timezone: Timezone for the event (e.g., 'America/New_York', defaults to UTC).

    Returns:
        A dictionary containing the created event details.
    """
    logger.info(f"Executing create_calendar_event on calendar '{calendar_id}'")
    if not summary or not start_time or not end_time:
        raise ValueError("Summary, start_time, and end_time are required")

    calendar_service = CalendarService()
    result = calendar_service.create_event(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        location=location,
        description=description,
        attendees=attendees,
        send_notifications=send_notifications,
        timezone=timezone,
        calendar_id=calendar_id,
    )

    if not result or (isinstance(result, dict) and result.get("error")):
        error_msg = "Error creating calendar event"
        if isinstance(result, dict):
            error_msg = result.get("message", error_msg)
        raise ValueError(error_msg)

    return result


# @mcp.tool(
#     name="delete_calendar_event",
# )
async def delete_calendar_event(
    event_id: str,
    calendar_id: str = "primary",
    send_notifications: bool = True,
) -> dict[str, Any]:
    """
    Delete a calendar event by its ID.

    Args:
        event_id: The ID of the event to delete.
        calendar_id: Calendar ID containing the event (defaults to "primary").
        send_notifications: Whether to send cancellation notifications (default True).

    Returns:
        A dictionary confirming the deletion.
    """
    logger.info(f"Executing delete_calendar_event on calendar '{calendar_id}', event '{event_id}'")
    if not event_id:
        raise ValueError("Event ID is required")

    calendar_service = CalendarService()
    success = calendar_service.delete_event(
        event_id=event_id,
        send_notifications=send_notifications,
        calendar_id=calendar_id,
    )

    if not success:
        # Attempt to check if the service returned an error dict
        error_info = getattr(calendar_service, "last_error", None)  # Hypothetical
        error_msg = "Failed to delete calendar event"
        if isinstance(error_info, dict) and error_info.get("error"):
            error_msg = error_info.get("message", error_msg)
        raise ValueError(error_msg)

    return {
        "message": f"Event with ID '{event_id}' deleted successfully from calendar '{calendar_id}'.",
        "success": True,
    }
