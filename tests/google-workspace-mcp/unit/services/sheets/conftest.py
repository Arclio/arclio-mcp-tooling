"""
Fixtures for Google Sheets service tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.services.sheets_service import SheetsService


@pytest.fixture
def mock_sheets_service():
    """Create a SheetsService with mocked service attribute."""
    with (
        patch("google_workspace_mcp.auth.gauth.get_credentials"),
        patch("googleapiclient.discovery.build"),
    ):
        sheets_service = SheetsService()
        # Replace the private service attribute with a mock
        sheets_service._service = MagicMock()
        return sheets_service
