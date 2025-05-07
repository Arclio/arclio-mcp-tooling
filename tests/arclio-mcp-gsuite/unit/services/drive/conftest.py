"""
Shared fixtures for Drive service unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.services.drive import DriveService


@pytest.fixture
def mock_drive_service():
    """Create a DriveService with mocked service attribute."""
    with (
        patch("arclio_mcp_gsuite.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        drive_service = DriveService()
        # Replace the service with a mock
        drive_service.service = MagicMock()
        return drive_service
