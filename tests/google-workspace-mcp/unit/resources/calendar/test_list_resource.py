"""
Unit tests for Calendar list_calendars resource.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.resources.calendar import list_calendars

pytestmark = pytest.mark.anyio


class TestListCalendarsResource:
    """Tests for the list_calendars resource function."""

    @pytest.fixture
    def mock_calendar_service(self):
        """Patch CalendarService for resource tests."""
        with patch("google_workspace_mcp.resources.calendar.CalendarService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_list_calendars_success(self, mock_calendar_service):
        """Test list_calendars successful case."""
        mock_service_response = [
            {"id": "primary", "summary": "user@example.com"},
            {"id": "cal_id_2", "summary": "Team Calendar"},
        ]
        mock_calendar_service.list_calendars.return_value = mock_service_response

        args = {}
        result = await list_calendars(**args)

        mock_calendar_service.list_calendars.assert_called_once_with()
        assert result == {"count": 2, "calendars": mock_service_response}

    async def test_list_calendars_no_results(self, mock_calendar_service):
        """Test list_calendars when no calendars are found."""
        mock_calendar_service.list_calendars.return_value = []

        args = {}
        result = await list_calendars(**args)

        mock_calendar_service.list_calendars.assert_called_once_with()
        assert result == {"message": "No calendars found."}

    async def test_list_calendars_service_error(self, mock_calendar_service):
        """Test list_calendars when the service call fails."""
        mock_calendar_service.list_calendars.return_value = {
            "error": True,
            "message": "API Error: Could not fetch calendars",
        }

        args = {}
        with pytest.raises(ValueError, match="API Error: Could not fetch calendars"):
            await list_calendars(**args)
