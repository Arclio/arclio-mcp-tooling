"""
Unit tests for Drive drive_list_shared_drives tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_list_shared_drives

pytestmark = pytest.mark.anyio


class TestDriveListSharedDrivesTool:
    """Tests for the drive_list_shared_drives tool function."""

    @pytest.fixture
    def mock_drive_service_for_tool(self):
        """Patch DriveService for tool tests."""
        with patch("google_workspace_mcp.tools.drive.DriveService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            yield mock_service_instance

    async def test_tool_list_shared_drives_success(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool with successful response."""
        mock_drives_data = [
            {"id": "drive1", "name": "Shared Drive Alpha"},
            {"id": "drive2", "name": "Shared Drive Beta"},
        ]
        mock_drive_service_for_tool.list_shared_drives.return_value = mock_drives_data

        result = await drive_list_shared_drives(page_size=50)

        mock_drive_service_for_tool.list_shared_drives.assert_called_once_with(page_size=50)
        assert result == {"count": 2, "shared_drives": mock_drives_data}

    async def test_tool_list_shared_drives_default_page_size(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool with default page size."""
        mock_drives_data = [
            {"id": "drive1", "name": "Shared Drive Alpha"},
        ]
        mock_drive_service_for_tool.list_shared_drives.return_value = mock_drives_data

        result = await drive_list_shared_drives()

        mock_drive_service_for_tool.list_shared_drives.assert_called_once_with(page_size=100)
        assert result == {"count": 1, "shared_drives": mock_drives_data}

    async def test_tool_list_shared_drives_no_results(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool with no shared drives found."""
        mock_drive_service_for_tool.list_shared_drives.return_value = []
        result = await drive_list_shared_drives()
        assert result == {"message": "No shared drives found or accessible."}

    async def test_tool_list_shared_drives_service_error(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool when service returns error."""
        mock_drive_service_for_tool.list_shared_drives.return_value = {
            "error": True,
            "message": "Service connection failed",
        }
        with pytest.raises(ValueError, match="Service connection failed"):
            await drive_list_shared_drives()

    async def test_tool_list_shared_drives_service_error_no_message(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool when service returns error without message."""
        mock_drive_service_for_tool.list_shared_drives.return_value = {
            "error": True,
        }
        with pytest.raises(ValueError, match="Error listing shared drives"):
            await drive_list_shared_drives()

    async def test_tool_list_shared_drives_custom_page_size(self, mock_drive_service_for_tool):
        """Test drive_list_shared_drives tool with custom page size values."""
        mock_drives_data = [{"id": "drive1", "name": "Test Drive"}]
        mock_drive_service_for_tool.list_shared_drives.return_value = mock_drives_data

        # Test with small page size
        result = await drive_list_shared_drives(page_size=1)
        mock_drive_service_for_tool.list_shared_drives.assert_called_with(page_size=1)
        assert result == {"count": 1, "shared_drives": mock_drives_data}

        # Test with large page size
        await drive_list_shared_drives(page_size=100)
        mock_drive_service_for_tool.list_shared_drives.assert_called_with(page_size=100)
