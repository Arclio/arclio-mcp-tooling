"""
Google Calendar service implementation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import pytz

from google_workspace_mcp.services.base import BaseGoogleService

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

            # max_results is the desired TOTAL. The Calendar API returns at most
            # 2500 events per request, so follow nextPageToken until we have
            # enough (previously events past the first page were silently
            # truncated).
            desired_total = max(1, max_results)

            # Prepare parameters
            params = {
                "calendarId": calendar_id,
                "timeMin": time_min,
                "singleEvents": True,
                "orderBy": "startTime",
                "showDeleted": show_deleted,
            }

            # Add optional time_max if specified
            if time_max:
                params["timeMax"] = time_max

            events: list[dict[str, Any]] = []
            page_token: str | None = None
            while len(events) < desired_total:
                params["maxResults"] = min(desired_total - len(events), 2500)
                if page_token:
                    params["pageToken"] = page_token
                events_result = self.service.events().list(**params).execute()
                events.extend(events_result.get("items", []))
                page_token = events_result.get("nextPageToken")
                if not page_token:
                    break

            events = events[:desired_total]

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
        add_meet: bool = False,
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
            add_meet: Attach a Google Meet conference to the event (default False)

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

            # Attach a Google Meet conference when requested. Creating one
            # requires a createRequest with a unique requestId plus
            # conferenceDataVersion=1 on the insert call.
            insert_kwargs: dict[str, Any] = {}
            if add_meet:
                event["conferenceData"] = {
                    "createRequest": {
                        "requestId": uuid.uuid4().hex,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }
                insert_kwargs["conferenceDataVersion"] = 1

            # Map boolean to required string for sendUpdates
            send_updates_value = "all" if send_notifications else "none"

            # Create the event
            return (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event,
                    sendUpdates=send_updates_value,
                    **insert_kwargs,
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
    ) -> bool | dict[str, Any]:
        """
        Delete a calendar event by its ID.

        Args:
            event_id: The ID of the event to delete
            send_notifications: Whether to send cancellation notifications to attendees
            calendar_id: ID of the calendar containing the event

        Returns:
            True on success, or an error dict (so the caller can surface Google's
            real message instead of a bare boolean).
        """
        try:
            # Map boolean to required string for sendUpdates
            send_updates_value = "all" if send_notifications else "none"

            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates=send_updates_value,
            ).execute()
            return True

        except Exception as e:
            return self.handle_api_error("delete_event", e)

    def get_event_details(self, event_id: str, calendar_id: str = "primary") -> dict[str, Any] | None:
        """
        Retrieves details for a specific event.

        Args:
            event_id: The ID of the event.
            calendar_id: The ID of the calendar the event belongs to. Defaults to "primary".

        Returns:
            A dictionary containing the event details or an error dictionary.
        """
        try:
            logger.info(f"Fetching details for event ID: {event_id} from calendar: {calendar_id}")
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            logger.info(f"Successfully fetched details for event: {event.get('summary')}")
            return event  # Return the full event resource as per API
        except Exception as e:
            return self.handle_api_error("get_event_details", e)
