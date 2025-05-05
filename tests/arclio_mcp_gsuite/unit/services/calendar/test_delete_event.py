"""
Unit tests for the CalendarService.delete_event method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestCalendarDeleteEvent:
    """Tests for the CalendarService.delete_event method."""

    # Removed local mock_calendar_service fixture

    def test_delete_event_success(self, mock_calendar_service):
        """Test successful event deletion."""
        # Test data
        event_id = "event_to_delete"
        calendar_id = "primary"

        # Mock successful deletion (typically returns None)
        mock_execute = MagicMock(return_value=None)
        mock_calendar_service.service.events.return_value.delete.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_calendar_service.delete_event(
            event_id=event_id, calendar_id=calendar_id
        )

        # Verify API call
        mock_calendar_service.service.events.return_value.delete.assert_called_once_with(
            calendarId=calendar_id, eventId=event_id, sendNotifications=True
        )

        # Verify result is True for success
        assert result is True

    def test_delete_event_notifications_false(self, mock_calendar_service):
        """Test event deletion with notifications disabled."""
        # Test data
        event_id = "event123"
        send_notifications = False

        # Call the method
        mock_calendar_service.delete_event(
            event_id=event_id, send_notifications=send_notifications
        )

        # Verify notifications parameter was passed correctly
        mock_calendar_service.service.events.return_value.delete.assert_called_once_with(
            calendarId="primary", eventId=event_id, sendNotifications=False  # Default
        )

    def test_delete_event_error(self, mock_calendar_service):
        """Test event deletion with API error."""
        # Test data
        event_id = "nonexistent_event"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Event not found"}}')

        # Setup the mock to raise the error
        mock_calendar_service.service.events.return_value.delete.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Event not found",
            "operation": "delete_event",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_calendar_service.delete_event(event_id)

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with(
            "delete_event", http_error
        )

        # For event deletion, the method returns False on error
        assert result is False
