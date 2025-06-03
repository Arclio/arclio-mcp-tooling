"""
Unit tests for Calendar get_event_details operations.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestCalendarGetEventDetails:
    """Tests for Calendar get_event_details operations."""

    def test_get_event_details_success(self, mock_calendar_service):
        """Test successful event details retrieval."""
        # Test data
        event_id = "event123"
        calendar_id = "primary"

        # Mock API response
        mock_event_response = {
            "id": "event123",
            "summary": "Test Event",
            "description": "Test event description",
            "start": {"dateTime": "2024-01-01T10:00:00Z"},
            "end": {"dateTime": "2024-01-01T11:00:00Z"},
            "location": "Test Location",
            "attendees": [{"email": "attendee@example.com"}],
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_event_response)
        mock_calendar_service.service.events.return_value.get.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_calendar_service.get_event_details(event_id, calendar_id)

        # Verify API call
        mock_calendar_service.service.events.return_value.get.assert_called_once_with(
            calendarId=calendar_id, eventId=event_id
        )

        # Verify result
        assert result == mock_event_response
        assert result["id"] == "event123"
        assert result["summary"] == "Test Event"

    def test_get_event_details_with_default_calendar(self, mock_calendar_service):
        """Test event details retrieval with default calendar."""
        # Test data
        event_id = "event456"

        # Mock API response
        mock_event_response = {"id": "event456", "summary": "Another Event"}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_event_response)
        mock_calendar_service.service.events.return_value.get.return_value.execute = (
            mock_execute
        )

        # Call the method without calendar_id (should use default 'primary')
        result = mock_calendar_service.get_event_details(event_id)

        # Verify API call with default calendar_id
        mock_calendar_service.service.events.return_value.get.assert_called_once_with(
            calendarId="primary", eventId=event_id
        )

        # Verify result
        assert result == mock_event_response

    def test_get_event_details_event_not_found(self, mock_calendar_service):
        """Test event details retrieval when event is not found."""
        # Test data
        event_id = "nonexistent_event"
        calendar_id = "primary"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Event not found"}}')

        # Setup the mock to raise the error
        mock_calendar_service.service.events.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Event not found",
            "operation": "get_event_details",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_calendar_service.get_event_details(event_id, calendar_id)

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with(
            "get_event_details", http_error
        )
        assert result == expected_error

    def test_get_event_details_invalid_calendar(self, mock_calendar_service):
        """Test event details retrieval with invalid calendar."""
        # Test data
        event_id = "event123"
        calendar_id = "invalid_calendar"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Calendar not found"}}'
        )

        # Setup the mock to raise the error
        mock_calendar_service.service.events.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Calendar not found",
            "operation": "get_event_details",
        }
        mock_calendar_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_calendar_service.get_event_details(event_id, calendar_id)

        # Verify error handling
        mock_calendar_service.handle_api_error.assert_called_once_with(
            "get_event_details", http_error
        )
        assert result == expected_error
