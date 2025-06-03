"""
Unit tests for Drive drive_create_folder tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_create_folder

pytestmark = pytest.mark.anyio


class TestDriveCreateFolderTool:
    """Tests for the drive_create_folder tool function."""

    @pytest.fixture
    def mock_drive_service_for_tool(self):
        """Patch DriveService for tool tests."""
        with patch("google_workspace_mcp.tools.drive.DriveService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            yield mock_service_instance

    async def test_tool_create_folder_success(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool successful folder creation."""
        mock_folder_response = {
            "id": "folder123",
            "name": "My New Folder",
            "parents": ["root"],
            "webViewLink": "https://drive.google.com/drive/folders/folder123",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service_for_tool.create_folder.return_value = mock_folder_response

        result = await drive_create_folder(folder_name="My New Folder")

        assert result == mock_folder_response
        mock_drive_service_for_tool.create_folder.assert_called_once_with(
            folder_name="My New Folder", parent_folder_id=None, shared_drive_id=None
        )

    async def test_tool_create_folder_with_parent(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool with parent folder."""
        mock_folder_response = {
            "id": "folder456",
            "name": "Sub Folder",
            "parents": ["parent123"],
            "webViewLink": "https://drive.google.com/drive/folders/folder456",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service_for_tool.create_folder.return_value = mock_folder_response

        result = await drive_create_folder(folder_name="Sub Folder", parent_folder_id="parent123")

        assert result == mock_folder_response
        mock_drive_service_for_tool.create_folder.assert_called_once_with(
            folder_name="Sub Folder", parent_folder_id="parent123", shared_drive_id=None
        )

    async def test_tool_create_folder_in_shared_drive(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool in shared drive."""
        mock_folder_response = {
            "id": "folder789",
            "name": "Shared Folder",
            "parents": ["shared_drive123"],
            "webViewLink": "https://drive.google.com/drive/folders/folder789",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service_for_tool.create_folder.return_value = mock_folder_response

        result = await drive_create_folder(folder_name="Shared Folder", shared_drive_id="shared_drive123")

        assert result == mock_folder_response
        mock_drive_service_for_tool.create_folder.assert_called_once_with(
            folder_name="Shared Folder",
            parent_folder_id=None,
            shared_drive_id="shared_drive123",
        )

    async def test_tool_create_folder_with_all_parameters(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool with both parent and shared drive."""
        mock_folder_response = {
            "id": "folder999",
            "name": "Complex Folder",
            "parents": ["parent456"],
            "webViewLink": "https://drive.google.com/drive/folders/folder999",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service_for_tool.create_folder.return_value = mock_folder_response

        result = await drive_create_folder(
            folder_name="Complex Folder",
            parent_folder_id="parent456",
            shared_drive_id="shared_drive123",
        )

        assert result == mock_folder_response
        mock_drive_service_for_tool.create_folder.assert_called_once_with(
            folder_name="Complex Folder",
            parent_folder_id="parent456",
            shared_drive_id="shared_drive123",
        )

    async def test_tool_create_folder_empty_name(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool with empty folder name."""
        with pytest.raises(ValueError, match="Folder name cannot be empty"):
            await drive_create_folder(folder_name="")

    async def test_tool_create_folder_whitespace_name(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool with whitespace-only folder name."""
        with pytest.raises(ValueError, match="Folder name cannot be empty"):
            await drive_create_folder(folder_name="   ")

    async def test_tool_create_folder_service_error(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool when service returns an error."""
        error_response = {
            "error": True,
            "message": "Insufficient permissions to create folder",
            "error_type": "permission_error",
        }
        mock_drive_service_for_tool.create_folder.return_value = error_response

        with pytest.raises(
            Exception,
            match="Folder creation failed: Insufficient permissions to create folder",
        ):
            await drive_create_folder(folder_name="Test Folder")

    async def test_tool_create_folder_service_unknown_error(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool when service returns error without message."""
        error_response = {"error": True, "error_type": "unknown"}
        mock_drive_service_for_tool.create_folder.return_value = error_response

        with pytest.raises(Exception, match="Folder creation failed: Unknown error"):
            await drive_create_folder(folder_name="Test Folder")

    async def test_tool_create_folder_default_parameters(self, mock_drive_service_for_tool):
        """Test drive_create_folder tool with default parameters."""
        mock_folder_response = {
            "id": "folder_default",
            "name": "Default Test",
            "webViewLink": "https://drive.google.com/drive/folders/folder_default",
        }
        mock_drive_service_for_tool.create_folder.return_value = mock_folder_response

        result = await drive_create_folder(folder_name="Default Test")

        # Verify default parameters
        mock_drive_service_for_tool.create_folder.assert_called_once_with(
            folder_name="Default Test", parent_folder_id=None, shared_drive_id=None
        )
        assert result == mock_folder_response
