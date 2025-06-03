"""
Drive service test fixtures.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.drive import DriveService


@pytest.fixture
def mock_drive_service():
    """Create a DriveService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        drive_service = DriveService()
        # Replace the private service attribute with a mock
        drive_service._service = MagicMock()
        return drive_service
