"""
Calendar service test fixtures.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.calendar import CalendarService


@pytest.fixture
def mock_calendar_service():
    """Create a CalendarService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        calendar_service = CalendarService()
        # Replace the private service attribute with a mock
        calendar_service._service = MagicMock()
        return calendar_service
