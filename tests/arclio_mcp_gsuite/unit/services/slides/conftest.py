"""
Shared fixtures for Slides service unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.services.slides import SlidesService


@pytest.fixture
def mock_slides_service():
    """Create a SlidesService with mocked service attribute."""
    with (
        patch("arclio_mcp_gsuite.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        slides_service = SlidesService()
        # Replace the service with a mock
        slides_service.service = MagicMock()
        return slides_service
