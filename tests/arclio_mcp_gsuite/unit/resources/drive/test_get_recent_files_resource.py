"""
Unit tests for Drive get_recent_files resource.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.resources.drive import get_recent_files

pytestmark = pytest.mark.anyio


class TestGetRecentFilesResource:
    """Tests for the get_recent_files resource function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Patch DriveService for resource tests."""
        with patch(
            "arclio_mcp_gsuite.resources.drive.DriveService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_recent_files_success(self, mock_drive_service):
        """Test get_recent_files successful case."""
        mock_service_response = [
            {
                "id": "file1",
                "name": "Recent Doc 1.docx",
                "modifiedTime": "2023-04-27T10:00:00Z",
            },
            {
                "id": "file2",
                "name": "Recent Image.jpg",
                "modifiedTime": "2023-04-26T14:30:00Z",
            },
        ]
        mock_drive_service.search_files.return_value = mock_service_response

        result = await get_recent_files()

        mock_drive_service.search_files.assert_called_once_with(
            query="modifiedTime > 'now-7d'", page_size=10
        )
        assert result == {"count": 2, "files": mock_service_response}

    async def test_get_recent_files_no_results(self, mock_drive_service):
        """Test get_recent_files when no recent files are found."""
        mock_drive_service.search_files.return_value = []

        result = await get_recent_files()

        mock_drive_service.search_files.assert_called_once_with(
            query="modifiedTime > 'now-7d'", page_size=10
        )
        assert result == {"message": "No recent files found."}

    async def test_get_recent_files_service_error(self, mock_drive_service):
        """Test get_recent_files when the service call fails."""
        mock_drive_service.search_files.return_value = {
            "error": True,
            "message": "API Error: Failed to query recent files",
        }

        with pytest.raises(ValueError, match="API Error: Failed to query recent files"):
            await get_recent_files()
