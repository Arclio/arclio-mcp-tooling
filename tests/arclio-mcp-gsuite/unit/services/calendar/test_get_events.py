"""
Unit tests for the CalendarService.get_events method.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz
from googleapiclient.errors import HttpError


class TestCalendarGetEvents:
    """Tests for the CalendarService.get_events method."""

    # Removed local mock_calendar_service fixture

    def test_get_events_success(self, mock_calendar_service):
        """Test successful events retrieval."""
        # Mock data for the API response
        mock_events = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Team Meeting",
                    "description": "Weekly team sync",
                    "start": {"dateTime": "2023-01-01T10:00:00Z"},
                    "end": {"dateTime": "2023-01-01T11:00:00Z"},
                    "status": "confirmed",
                    "creator": {"email": "creator@example.com"},
                    "organizer": {"email": "organizer@example.com"},
                    "location": "Conference Room A",
                },
                {
                    "id": "event2",
                    "summary": "Lunch",
                    "start": {"dateTime": "2023-01-01T12:00:00Z"},
                    "end": {"dateTime": "2023-01-01T13:00:00Z"},
                    "status": "confirmed",
                },
            ]
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_events)
        mock_calendar_service.service.events.return_value.list.return_value.execute = mock_execute

        # Call the method with parameters
        calendar_id = "primary"
        time_min = "2023-01-01T00:00:00Z"
        time_max = "2023-01-02T00:00:00Z"
        result = mock_calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=10,
        )

        # Verify API call with correct parameters
        mock_calendar_service.service.events.return_value.list.assert_called_once_with(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
            showDeleted=False,
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[0]["summary"] == "Team Meeting"
        assert result[0]["start"] == {"dateTime": "2023-01-01T10:00:00Z"}
        assert result[0]["location"] == "Conference Room A"
        assert result[1]["id"] == "event2"
        assert result[1]["summary"] == "Lunch"

    def test_get_events_default_time_min(self, mock_calendar_service):
        """Test events retrieval with default time_min."""
        # Mock data for response
        mock_events = {"items": []}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_events)
        mock_calendar_service.service.events.return_value.list.return_value.execute = mock_execute

        # Mock datetime.now for consistent testing
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        expected_iso = mock_now.isoformat()

        with patch("arclio_mcp_gsuite.services.calendar.datetime") as mock_datetime:
            # Configure mock to return our fixed now time
            mock_datetime.now.return_value = mock_now
            # Pass through other methods
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Call get_events without specifying time_min
            mock_calendar_service.get_events(calendar_id="primary")

            # Extract the actual timeMin parameter from the call
            call_args = mock_calendar_service.service.events.return_value.list.call_args
            actual_time_min = call_args[1]["timeMin"]

            # Verify time_min was defaulted to current time
            assert actual_time_min == expected_iso

    def test_get_events_empty(self, mock_calendar_service):
        """Test events retrieval with no events."""
        # Mock empty response
        mock_events = {"items": []}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_events)
        mock_calendar_service.service.events.return_value.list.return_value.execute = mock_execute

        # Call the method
        result = mock_calendar_service.get_events()

        # Verify result is an empty list
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_events_error(self, mock_calendar_service):
        """Test events retrieval with API error."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Calendar Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Calendar not found"}}')

        # Setup the mock to raise the error
        mock_calendar_service.service.events.return_value.list.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Calendar not found",
            "operation": "get_events",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_calendar_service.get_events(calendar_id="nonexistent")

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with("get_events", http_error)
        assert result == expected_error
