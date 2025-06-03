"""
Unit tests for Calendar create_calendar_event and delete_calendar_event tools.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.calendar import (
    create_calendar_event,
    delete_calendar_event,
)

pytestmark = pytest.mark.anyio


# --- Fixture --- #


@pytest.fixture
def mock_calendar_service():
    """Patch CalendarService for tool tests."""
    with patch(
        "google_workspace_mcp.tools.calendar.CalendarService"
    ) as mock_service_class:
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        # Hypothetical error tracking for boolean returns
        mock_service.last_error = None
        yield mock_service


# --- Tests for create_calendar_event --- #


class TestCreateCalendarEvent:
    """Tests for the create_calendar_event tool function."""

    async def test_create_event_success(self, mock_calendar_service):
        """Test create_calendar_event successful case."""
        mock_service_response = {
            "id": "event123",
            "summary": "Meeting with Team",
            "start": {"dateTime": "2024-06-01T10:00:00Z"},
            "end": {"dateTime": "2024-06-01T11:00:00Z"},
            "htmlLink": "https://calendar.google.com/event?eid=...",
        }
        mock_calendar_service.create_event.return_value = mock_service_response

        args = {
            "summary": "Meeting with Team",
            "start_time": "2024-06-01T10:00:00Z",
            "end_time": "2024-06-01T11:00:00Z",
            "calendar_id": "team_cal@example.com",
            "attendees": ["member1@example.com"],
            "location": "Board Room",
            "description": "Discuss project status",
            "send_notifications": False,
            "timezone": "America/New_York",
        }
        result = await create_calendar_event(**args)

        mock_calendar_service.create_event.assert_called_once_with(
            summary="Meeting with Team",
            start_time="2024-06-01T10:00:00Z",
            end_time="2024-06-01T11:00:00Z",
            location="Board Room",
            description="Discuss project status",
            attendees=["member1@example.com"],
            send_notifications=False,
            timezone="America/New_York",
            calendar_id="team_cal@example.com",
        )
        assert result == mock_service_response

    async def test_create_event_service_error(self, mock_calendar_service):
        """Test create_calendar_event when the service returns an error."""
        mock_calendar_service.create_event.return_value = {
            "error": True,
            "message": "API Error: Invalid time range",
        }

        args = {
            "summary": "Bad Meeting",
            "start_time": "2024-06-01T11:00:00Z",  # End before start
            "end_time": "2024-06-01T10:00:00Z",
        }
        with pytest.raises(ValueError, match="API Error: Invalid time range"):
            await create_calendar_event(**args)

    async def test_create_event_missing_args(self):
        """Test create_calendar_event with missing required arguments."""
        base_args = {
            "summary": "Meeting",
            "start_time": "2024-06-01T10:00:00Z",
            "end_time": "2024-06-01T11:00:00Z",
        }

        for key in ["summary", "start_time", "end_time"]:
            args = base_args.copy()
            args[key] = ""
            with pytest.raises(
                ValueError, match="Summary, start_time, and end_time are required"
            ):
                await create_calendar_event(**args)


# --- Tests for delete_calendar_event --- #


class TestDeleteCalendarEvent:
    """Tests for the delete_calendar_event tool function."""

    async def test_delete_event_success(self, mock_calendar_service):
        """Test delete_calendar_event successful case."""
        mock_calendar_service.delete_event.return_value = True

        args = {
            "event_id": "event_to_delete_123",
            "calendar_id": "cal_abc",
            "send_notifications": False,
        }
        result = await delete_calendar_event(**args)

        mock_calendar_service.delete_event.assert_called_once_with(
            event_id="event_to_delete_123",
            send_notifications=False,
            calendar_id="cal_abc",
        )
        assert result == {
            "message": "Event with ID 'event_to_delete_123' deleted successfully from calendar 'cal_abc'.",
            "success": True,
        }

    async def test_delete_event_service_failure_no_error_info(
        self, mock_calendar_service
    ):
        """Test delete_calendar_event when service returns False without error info."""
        mock_calendar_service.delete_event.return_value = False
        mock_calendar_service.last_error = None  # Ensure no specific error info

        args = {"event_id": "event_fail"}
        with pytest.raises(ValueError, match="Failed to delete calendar event"):
            await delete_calendar_event(**args)

    async def test_delete_event_service_failure_with_error_info(
        self, mock_calendar_service
    ):
        """Test delete_calendar_event when service returns False with specific error."""
        mock_calendar_service.delete_event.return_value = False
        mock_calendar_service.last_error = {
            "error": True,
            "message": "API: Event not found",
        }

        args = {"event_id": "event_fail_api"}
        with pytest.raises(ValueError, match="API: Event not found"):
            await delete_calendar_event(**args)

    async def test_delete_event_missing_args(self):
        """Test delete_calendar_event with missing required arguments."""
        args_no_event = {"event_id": ""}
        with pytest.raises(ValueError, match="Event ID is required"):
            await delete_calendar_event(**args_no_event)
