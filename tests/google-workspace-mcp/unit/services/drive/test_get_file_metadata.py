"""
Unit tests for the DriveService.get_file_metadata method.
"""

from unittest.mock import MagicMock

from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveGetFileMetadata:
    """Tests for the DriveService.get_file_metadata method."""

    def test_get_file_metadata_success(self, mock_drive_service: DriveService):
        """Test successful file metadata retrieval."""
        mock_metadata = {
            "id": "file123",
            "name": "test_document.pdf",
            "mimeType": "application/pdf",
            "size": "102400",
            "createdTime": "2024-01-01T10:00:00.000Z",
            "modifiedTime": "2024-01-02T15:30:00.000Z",
            "webViewLink": "https://drive.google.com/file/d/file123/view",
            "webContentLink": "https://drive.google.com/uc?id=file123",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/icon.png",
            "parents": ["folder456"],
            "owners": [{"displayName": "John Doe", "emailAddress": "john@example.com"}],
            "shared": False,
            "trashed": False,
        }
        mock_drive_service.service.files.return_value.get.return_value.execute.return_value = mock_metadata

        result = mock_drive_service.get_file_metadata(file_id="file123")

        assert result == mock_metadata
        # Verify API call parameters
        mock_drive_service.service.files.return_value.get.assert_called_once_with(
            fileId="file123",
            fields="id, name, mimeType, size, createdTime, modifiedTime, "
            "webViewLink, webContentLink, iconLink, parents, owners, "
            "shared, trashed, capabilities, permissions, "
            "description, starred, explicitlyTrashed",
            supportsAllDrives=True,
        )

    def test_get_file_metadata_empty_file_id(self, mock_drive_service: DriveService):
        """Test file metadata retrieval with empty file ID."""
        result = mock_drive_service.get_file_metadata(file_id="")

        assert result["error"] is True
        assert result["message"] == "File ID cannot be empty"
        # Verify no API call was made
        mock_drive_service.service.files.return_value.get.assert_not_called()

    def test_get_file_metadata_none_file_id(self, mock_drive_service: DriveService):
        """Test file metadata retrieval with None file ID."""
        result = mock_drive_service.get_file_metadata(file_id=None)

        assert result["error"] is True
        assert result["message"] == "File ID cannot be empty"

    def test_get_file_metadata_http_error(self, mock_drive_service: DriveService):
        """Test file metadata retrieval with HTTP error."""
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "File not found"}}')
        mock_drive_service.service.files.return_value.get.return_value.execute.side_effect = http_error

        expected_error_details = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "File not found",
            "operation": "get_file_metadata",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.get_file_metadata(file_id="nonexistent")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("get_file_metadata", http_error)

    def test_get_file_metadata_unexpected_error(self, mock_drive_service: DriveService):
        """Test file metadata retrieval with unexpected error."""
        exception = Exception("Network error")
        mock_drive_service.service.files.return_value.get.return_value.execute.side_effect = exception

        expected_error_details = {
            "error": True,
            "error_type": "unexpected_service_error",
            "message": "Network error",
            "operation": "get_file_metadata",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.get_file_metadata(file_id="file123")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("get_file_metadata", exception)
