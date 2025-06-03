"""
Unit tests for the DriveService.create_folder method.
"""

from unittest.mock import MagicMock

from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveCreateFolder:
    """Tests for the DriveService.create_folder method."""

    def test_create_folder_success_no_parent(self, mock_drive_service: DriveService):
        """Test successful folder creation without parent."""
        mock_folder_response = {
            "id": "folder123",
            "name": "My New Folder",
            "parents": ["root"],
            "webViewLink": "https://drive.google.com/drive/folders/folder123",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_folder_response

        result = mock_drive_service.create_folder(folder_name="My New Folder")

        assert result == mock_folder_response
        # Verify API call parameters
        call_args = mock_drive_service.service.files.return_value.create.call_args
        assert call_args[1]["body"]["name"] == "My New Folder"
        assert call_args[1]["body"]["mimeType"] == "application/vnd.google-apps.folder"
        assert "parents" not in call_args[1]["body"]  # No parent specified
        assert call_args[1]["supportsAllDrives"] is True
        assert call_args[1]["fields"] == "id, name, parents, webViewLink, createdTime"

    def test_create_folder_with_parent(self, mock_drive_service: DriveService):
        """Test successful folder creation with parent folder."""
        mock_folder_response = {
            "id": "folder456",
            "name": "Sub Folder",
            "parents": ["parent123"],
            "webViewLink": "https://drive.google.com/drive/folders/folder456",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_folder_response

        result = mock_drive_service.create_folder(folder_name="Sub Folder", parent_folder_id="parent123")

        assert result == mock_folder_response
        # Verify API call includes parent
        call_args = mock_drive_service.service.files.return_value.create.call_args
        assert call_args[1]["body"]["parents"] == ["parent123"]

    def test_create_folder_in_shared_drive(self, mock_drive_service: DriveService):
        """Test successful folder creation in shared drive."""
        mock_folder_response = {
            "id": "folder789",
            "name": "Shared Folder",
            "parents": ["shared_drive123"],
            "webViewLink": "https://drive.google.com/drive/folders/folder789",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_folder_response

        result = mock_drive_service.create_folder(folder_name="Shared Folder", shared_drive_id="shared_drive123")

        assert result == mock_folder_response
        # Verify API call includes shared drive as parent
        call_args = mock_drive_service.service.files.return_value.create.call_args
        assert call_args[1]["body"]["parents"] == ["shared_drive123"]

    def test_create_folder_parent_overrides_shared_drive(self, mock_drive_service: DriveService):
        """Test that parent_folder_id takes precedence over shared_drive_id."""
        mock_folder_response = {
            "id": "folder999",
            "name": "Priority Test",
            "parents": ["parent456"],
            "webViewLink": "https://drive.google.com/drive/folders/folder999",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_folder_response

        result = mock_drive_service.create_folder(
            folder_name="Priority Test",
            parent_folder_id="parent456",
            shared_drive_id="shared_drive123",  # Should be ignored
        )

        assert result == mock_folder_response
        # Verify only parent_folder_id is used, not shared_drive_id
        call_args = mock_drive_service.service.files.return_value.create.call_args
        assert call_args[1]["body"]["parents"] == ["parent456"]

    def test_create_folder_empty_name(self, mock_drive_service: DriveService):
        """Test folder creation with empty name."""
        result = mock_drive_service.create_folder(folder_name="")

        assert result["error"] is True
        assert result["message"] == "Folder name cannot be empty"
        # Verify no API call was made
        mock_drive_service.service.files.return_value.create.assert_not_called()

    def test_create_folder_whitespace_name(self, mock_drive_service: DriveService):
        """Test folder creation with whitespace-only name."""
        result = mock_drive_service.create_folder(folder_name="   ")

        assert result["error"] is True
        assert result["message"] == "Folder name cannot be empty"

    def test_create_folder_none_name(self, mock_drive_service: DriveService):
        """Test folder creation with None name."""
        result = mock_drive_service.create_folder(folder_name=None)

        assert result["error"] is True
        assert result["message"] == "Folder name cannot be empty"

    def test_create_folder_strips_whitespace(self, mock_drive_service: DriveService):
        """Test that folder names are stripped of leading/trailing whitespace."""
        mock_folder_response = {
            "id": "folder_clean",
            "name": "Clean Name",
            "webViewLink": "https://drive.google.com/drive/folders/folder_clean",
            "createdTime": "2024-01-01T10:00:00.000Z",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_folder_response

        mock_drive_service.create_folder(folder_name="  Clean Name  ")

        # Verify name was stripped
        call_args = mock_drive_service.service.files.return_value.create.call_args
        assert call_args[1]["body"]["name"] == "Clean Name"

    def test_create_folder_http_error(self, mock_drive_service: DriveService):
        """Test folder creation with HTTP error."""
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Insufficient permissions"}}')
        mock_drive_service.service.files.return_value.create.return_value.execute.side_effect = http_error

        expected_error_details = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Insufficient permissions",
            "operation": "create_folder",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.create_folder(folder_name="Test Folder")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("create_folder", http_error)

    def test_create_folder_unexpected_error(self, mock_drive_service: DriveService):
        """Test folder creation with unexpected error."""
        exception = Exception("Network timeout")
        mock_drive_service.service.files.return_value.create.return_value.execute.side_effect = exception

        expected_error_details = {
            "error": True,
            "error_type": "unexpected_service_error",
            "message": "Network timeout",
            "operation": "create_folder",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.create_folder(folder_name="Test Folder")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("create_folder", exception)
