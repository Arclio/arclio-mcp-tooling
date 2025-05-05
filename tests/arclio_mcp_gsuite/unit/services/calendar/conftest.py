"""
Shared fixtures for Calendar service unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.services.calendar import CalendarService


@pytest.fixture
def mock_calendar_service():
    """Create a CalendarService with mocked service attribute."""
    with (
        patch("arclio_mcp_gsuite.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        calendar_service = CalendarService()
        # Replace the service with a mock
        calendar_service.service = MagicMock()
        return calendar_service
