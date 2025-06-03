"""
Unit tests for the CalendarService.create_event method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestCalendarCreateEvent:
    """Tests for the CalendarService.create_event method."""

    # Removed local mock_calendar_service fixture

    def test_create_event_success(self, mock_calendar_service):
        """Test successful event creation."""
        # Test data
        summary = "New Event"
        start_time = "2023-01-01T10:00:00Z"
        end_time = "2023-01-01T11:00:00Z"
        location = "Conference Room"
        description = "Event description"
        attendees = ["attendee1@example.com", "attendee2@example.com"]
        timezone = "America/New_York"

        # Mock API response
        mock_created_event = {
            "id": "event123",
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": timezone},
            "end": {"dateTime": end_time, "timeZone": timezone},
            "attendees": [
                {"email": "attendee1@example.com"},
                {"email": "attendee2@example.com"},
            ],
            "htmlLink": "https://calendar.google.com/event?id=event123",
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_created_event)
        mock_calendar_service._service.events.return_value.insert.return_value.execute = mock_execute

        # Call the method
        result = mock_calendar_service.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            attendees=attendees,
            timezone=timezone,
        )

        # Verify API call with correct event data
        mock_calendar_service._service.events.return_value.insert.assert_called_once()
        # Extract the body from the call
        call_args = mock_calendar_service._service.events.return_value.insert.call_args
        body_arg = call_args[1]["body"]

        # Verify the event data
        assert body_arg["summary"] == summary
        assert body_arg["location"] == location
        assert body_arg["description"] == description
        assert body_arg["start"]["dateTime"] == start_time
        assert body_arg["start"]["timeZone"] == timezone
        assert body_arg["end"]["dateTime"] == end_time
        assert body_arg["end"]["timeZone"] == timezone
        assert len(body_arg["attendees"]) == 2
        assert body_arg["attendees"][0]["email"] == attendees[0]

        # Verify the result
        assert result == mock_created_event

    def test_create_event_minimal(self, mock_calendar_service):
        """Test event creation with minimal required fields."""
        # Test data - only required fields
        summary = "Minimal Event"
        start_time = "2023-01-01T10:00:00Z"
        end_time = "2023-01-01T11:00:00Z"

        # Mock API response
        mock_created_event = {
            "id": "event123",
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_created_event)
        mock_calendar_service._service.events.return_value.insert.return_value.execute = mock_execute

        # Call the method with only required fields
        result = mock_calendar_service.create_event(summary=summary, start_time=start_time, end_time=end_time)

        # Verify API call
        mock_calendar_service._service.events.return_value.insert.assert_called_once()
        # Extract the body from the call
        call_args = mock_calendar_service._service.events.return_value.insert.call_args
        body_arg = call_args[1]["body"]

        # Verify only required fields are present
        assert body_arg["summary"] == summary
        assert body_arg["start"]["dateTime"] == start_time
        assert body_arg["start"]["timeZone"] == "UTC"  # Default timezone
        assert body_arg["end"]["dateTime"] == end_time
        assert "location" not in body_arg
        assert "description" not in body_arg
        assert "attendees" not in body_arg

        # Verify the result
        assert result == mock_created_event

    def test_create_event_error(self, mock_calendar_service):
        """Test event creation with API error."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid time format"}}')

        # Setup the mock to raise the error
        mock_calendar_service._service.events.return_value.insert.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid time format",
            "operation": "create_event",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method with invalid data
        result = mock_calendar_service.create_event(summary="Test Event", start_time="invalid-time", end_time="invalid-time")

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with("create_event", http_error)
        assert result == expected_error
