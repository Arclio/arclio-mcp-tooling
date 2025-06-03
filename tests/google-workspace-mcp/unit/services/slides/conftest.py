"""
Shared fixtures for Slides service unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.slides import SlidesService


@pytest.fixture
def mock_slides_service():
    """Create a SlidesService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        slides_service = SlidesService()
        # Replace the private service attribute with a mock
        slides_service._service = MagicMock()
        return slides_service
