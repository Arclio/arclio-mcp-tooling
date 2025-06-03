"""
Unit tests for Calendar calendar_get_events tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.calendar import calendar_get_events

pytestmark = pytest.mark.anyio


class TestCalendarGetEventsTool:
    """Tests for the calendar_get_events tool function."""

    @pytest.fixture
    def mock_calendar_service(self):
        """Patch CalendarService for tool tests."""
        with patch("google_workspace_mcp.tools.calendar.CalendarService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_events_success(self, mock_calendar_service):
        """Test calendar_get_events successful case."""
        mock_service_response = [
            {"id": "event1", "summary": "Meeting 1"},
            {"id": "event2", "summary": "Meeting 2"},
        ]
        mock_calendar_service.get_events.return_value = mock_service_response

        args = {
            "calendar_id": "primary",
            "time_min": "2024-01-01T00:00:00Z",
            "time_max": "2024-01-01T23:59:59Z",
        }
        result = await calendar_get_events(**args)

        mock_calendar_service.get_events.assert_called_once_with(
            calendar_id="primary",
            time_min="2024-01-01T00:00:00Z",
            time_max="2024-01-01T23:59:59Z",
            max_results=250,  # Check internal default
            show_deleted=False,  # Check internal default
        )
        assert result == {"count": 2, "events": mock_service_response}

    async def test_get_events_with_optional_params(self, mock_calendar_service):
        """Test calendar_get_events with optional parameters."""
        mock_service_response = [{"id": "event1", "summary": "Meeting 1"}]
        mock_calendar_service.get_events.return_value = mock_service_response

        args = {
            "calendar_id": "team_cal",
            "time_min": "2024-01-01T00:00:00Z",
            "time_max": "2024-01-01T23:59:59Z",
            "max_results": 10,
            "show_deleted": True,
        }
        result = await calendar_get_events(**args)

        mock_calendar_service.get_events.assert_called_once_with(
            calendar_id="team_cal",
            time_min="2024-01-01T00:00:00Z",
            time_max="2024-01-01T23:59:59Z",
            max_results=10,
            show_deleted=True,
        )
        assert result == {"count": 1, "events": mock_service_response}

    async def test_get_events_no_results(self, mock_calendar_service):
        """Test calendar_get_events when no events are found."""
        mock_calendar_service.get_events.return_value = []

        args = {
            "calendar_id": "team_cal",
            "time_min": "2024-02-01T00:00:00Z",
            "time_max": "2024-02-01T23:59:59Z",
        }
        result = await calendar_get_events(**args)

        mock_calendar_service.get_events.assert_called_once_with(
            calendar_id="team_cal",
            time_min="2024-02-01T00:00:00Z",
            time_max="2024-02-01T23:59:59Z",
            max_results=250,
            show_deleted=False,
        )
        assert result == {"message": "No events found for the specified time range."}

    async def test_get_events_service_error(self, mock_calendar_service):
        """Test calendar_get_events when the service call fails."""
        mock_calendar_service.get_events.return_value = {
            "error": True,
            "message": "API Error: Calendar not found",
        }

        args = {
            "calendar_id": "invalid_cal",
            "time_min": "2024-01-01T00:00:00Z",
            "time_max": "2024-01-01T23:59:59Z",
        }
        with pytest.raises(ValueError, match="API Error: Calendar not found"):
            await calendar_get_events(**args)

    async def test_get_events_missing_params(self):
        """Test tool validation for missing parameters."""
        base_args = {
            "calendar_id": "primary",
            "time_min": "2024-01-01T00:00:00Z",
            "time_max": "2024-01-01T23:59:59Z",
        }

        for key, msg in [
            ("calendar_id", "calendar_id parameter is required"),
            ("time_min", "time_min parameter is required"),
            ("time_max", "time_max parameter is required"),
        ]:
            args = base_args.copy()
            args[key] = ""  # Use empty string to test validation
            with pytest.raises(ValueError, match=msg):
                await calendar_get_events(**args)
