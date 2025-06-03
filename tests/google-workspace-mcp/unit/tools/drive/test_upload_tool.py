"""
Unit tests for Drive gdrive_upload_file tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import gdrive_upload_file

pytestmark = pytest.mark.anyio


class TestDriveUploadFile:
    """Tests for the gdrive_upload_file tool function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Patch DriveService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.drive.DriveService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_upload_file_success(self, mock_drive_service):
        """Test gdrive_upload_file with successful upload."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "id": "file123",
            "name": "file.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2024-01-01T12:00:00.000Z",
            "webViewLink": "https://drive.google.com/file/d/file123/view",
        }
        mock_drive_service.upload_file.return_value = mock_service_response

        # Define arguments (removed 'user_id')
        args = {
            "file_path": "/fake/path/to/file.txt",
        }

        # Call the function
        result = await gdrive_upload_file(**args)

        # Verify the service call
        mock_drive_service.upload_file.assert_called_once_with(
            file_path="/fake/path/to/file.txt"
        )
        assert result == mock_service_response

    async def test_upload_file_service_error(self, mock_drive_service):
        """Test gdrive_upload_file when the service returns an error."""
        # Setup mock error response
        mock_drive_service.upload_file.return_value = {
            "error": True,
            "message": "Local file not found via API",
            "error_type": "local_file_error",
        }

        # Define arguments (removed 'user_id')
        args = {"file_path": "/invalid/path"}

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="Local file not found via API"):
            await gdrive_upload_file(**args)

    async def test_upload_file_missing_path(self):
        """Test gdrive_upload_file with missing file_path."""
        # Define arguments (removed 'user_id')
        args = {"file_path": ""}
        with pytest.raises(ValueError, match="File path cannot be empty"):
            await gdrive_upload_file(**args)
