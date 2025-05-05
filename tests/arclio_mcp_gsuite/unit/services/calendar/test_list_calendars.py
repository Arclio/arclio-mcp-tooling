"""
Unit tests for the CalendarService.list_calendars method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestCalendarListCalendars:
    """Tests for the CalendarService.list_calendars method."""

    # Removed local mock_calendar_service fixture

    def test_list_calendars_success(self, mock_calendar_service):
        """Test successful calendars listing."""
        # Mock data for the API response
        mock_calendars = {
            "items": [
                {
                    "kind": "calendar#calendarListEntry",
                    "id": "primary@example.com",
                    "summary": "Primary Calendar",
                    "primary": True,
                    "timeZone": "America/Los_Angeles",
                    "etag": "etag1",
                    "accessRole": "owner",
                },
                {
                    "kind": "calendar#calendarListEntry",
                    "id": "secondary@example.com",
                    "summary": "Secondary Calendar",
                    "primary": False,
                    "timeZone": "Europe/London",
                    "etag": "etag2",
                    "accessRole": "reader",
                },
            ]
        }

        # Setup execute mock to return our test data
        mock_execute = MagicMock(return_value=mock_calendars)
        mock_calendar_service.service.calendarList.return_value.list.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_calendar_service.list_calendars()

        # Verify API call
        mock_calendar_service.service.calendarList.return_value.list.assert_called_once()

        # Verify result format and content
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "primary@example.com"
        assert result[0]["summary"] == "Primary Calendar"
        assert result[0]["primary"] is True
        assert result[1]["id"] == "secondary@example.com"
        assert result[1]["summary"] == "Secondary Calendar"
        assert result[1]["primary"] is False

    def test_list_calendars_empty(self, mock_calendar_service):
        """Test listing with no calendars."""
        # Mock empty response
        mock_calendars = {"items": []}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_calendars)
        mock_calendar_service.service.calendarList.return_value.list.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_calendar_service.list_calendars()

        # Verify result is an empty list
        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_calendars_error(self, mock_calendar_service):
        """Test calendar listing with API error."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Permission Denied"}}'
        )

        # Setup the mock to raise the error
        mock_calendar_service.service.calendarList.return_value.list.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission Denied",
            "operation": "list_calendars",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_calendar_service.list_calendars()

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with(
            "list_calendars", http_error
        )
        assert result == expected_error
