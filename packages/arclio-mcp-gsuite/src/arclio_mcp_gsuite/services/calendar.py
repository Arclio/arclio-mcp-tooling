"""
Google Calendar service implementation.
"""

import logging
from datetime import datetime
from typing import Any

import pytz

from arclio_mcp_gsuite.services.base import BaseGoogleService

logger = logging.getLogger(__name__)


class CalendarService(BaseGoogleService):
    """
    Service for interacting with Google Calendar API.
    """

    def __init__(self):
        """Initialize the Calendar service."""
        super().__init__("calendar", "v3")

    def list_calendars(self) -> list[dict[str, Any]]:
        """
        Lists all calendars accessible by the user.

        Returns:
            List of calendar objects with their metadata
        """
        try:
            calendar_list = self.service.calendarList().list().execute()

            calendars = []

            for calendar in calendar_list.get("items", []):
                if calendar.get("kind") == "calendar#calendarListEntry":
                    calendars.append(
                        {
                            "id": calendar.get("id"),
                            "summary": calendar.get("summary"),
                            "primary": calendar.get("primary", False),
                            "time_zone": calendar.get("timeZone"),
                            "etag": calendar.get("etag"),
                            "access_role": calendar.get("accessRole"),
                        }
                    )

            return calendars

        except Exception as e:
            return self.handle_api_error("list_calendars", e)

    def get_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 250,
        show_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Retrieve calendar events within a specified time range.

        Args:
            calendar_id: ID of the calendar to query
            time_min: Start time in RFC3339 format. Defaults to current time.
            time_max: End time in RFC3339 format
            max_results: Maximum number of events to return
            show_deleted: Whether to include deleted events

        Returns:
            List of calendar events
        """
        try:
            # If no time_min specified, use current time
            if not time_min:
                time_min = datetime.now(pytz.UTC).isoformat()

            # Ensure max_results is within limits
            max_results = min(max(1, max_results), 2500)

            # Prepare parameters
            params = {
                "calendarId": calendar_id,
                "timeMin": time_min,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
                "showDeleted": show_deleted,
            }

            # Add optional time_max if specified
            if time_max:
                params["timeMax"] = time_max

            # Execute the events().list() method
            events_result = self.service.events().list(**params).execute()

            # Extract the events
            events = events_result.get("items", [])

            # Process and return the events
            processed_events = []
            for event in events:
                processed_event = {
                    "id": event.get("id"),
                    "summary": event.get("summary"),
                    "description": event.get("description"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "status": event.get("status"),
                    "creator": event.get("creator"),
                    "organizer": event.get("organizer"),
                    "attendees": event.get("attendees"),
                    "location": event.get("location"),
                    "hangoutLink": event.get("hangoutLink"),
                    "conferenceData": event.get("conferenceData"),
                    "recurringEventId": event.get("recurringEventId"),
                }
                processed_events.append(processed_event)

            return processed_events

        except Exception as e:
            return self.handle_api_error("get_events", e)

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        location: str | None = None,
        description: str | None = None,
        attendees: list[str] | None = None,
        send_notifications: bool = True,
        timezone: str | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any] | None:
        """
        Create a new calendar event.

        Args:
            summary: Title of the event
            start_time: Start time in RFC3339 format
            end_time: End time in RFC3339 format
            location: Location of the event
            description: Description of the event
            attendees: List of attendee email addresses
            send_notifications: Whether to send notifications to attendees
            timezone: Timezone for the event (e.g. 'America/New_York')
            calendar_id: ID of the calendar to create the event in

        Returns:
            Created event data or None if creation fails
        """
        try:
            # Prepare event data
            event = {
                "summary": summary,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone or "UTC",
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone or "UTC",
                },
            }

            # Add optional fields if provided
            if location:
                event["location"] = location
            if description:
                event["description"] = description
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            # Map boolean to required string for sendUpdates
            send_updates_value = "all" if send_notifications else "none"

            # Create the event
            return (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event,
                    sendUpdates=send_updates_value,
                )
                .execute()
            )

        except Exception as e:
            return self.handle_api_error("create_event", e)

    def delete_event(
        self,
        event_id: str,
        send_notifications: bool = True,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Delete a calendar event by its ID.

        Args:
            event_id: The ID of the event to delete
            send_notifications: Whether to send cancellation notifications to attendees
            calendar_id: ID of the calendar containing the event

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendNotifications=send_notifications,
            ).execute()
            return True

        except Exception as e:
            self.handle_api_error("delete_event", e)
            return False
