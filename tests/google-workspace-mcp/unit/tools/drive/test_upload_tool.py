"""
Unit tests for Drive drive_upload_file tool.
"""

import base64
from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_upload_file

pytestmark = pytest.mark.anyio


class TestDriveUploadFile:
    """Tests for the drive_upload_file tool function."""

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
        """Test drive_upload_file with successful upload."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "id": "file123",
            "name": "test.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2024-01-01T12:00:00.000Z",
            "webViewLink": "https://drive.google.com/file/d/file123/view",
        }
        mock_drive_service.upload_file_content.return_value = mock_service_response

        # Define arguments
        content = "Hello, World!"
        content_base64 = base64.b64encode(content.encode()).decode()
        args = {
            "filename": "test.txt",
            "content_base64": content_base64,
        }

        # Call the function
        result = await drive_upload_file(**args)

        # Verify the service call
        mock_drive_service.upload_file_content.assert_called_once_with(
            filename="test.txt",
            content_base64=content_base64,
            parent_folder_id=None,
            shared_drive_id=None,
        )
        assert result == mock_service_response

    async def test_upload_file_service_error(self, mock_drive_service):
        """Test drive_upload_file when the service returns an error."""
        # Setup mock error response
        mock_drive_service.upload_file_content.return_value = {
            "error": True,
            "message": "Invalid base64 content",
            "error_type": "invalid_content",
        }

        # Define arguments
        args = {"filename": "test.txt", "content_base64": "invalid content"}

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="Invalid base64 content"):
            await drive_upload_file(**args)

    async def test_upload_file_missing_filename(self):
        """Test drive_upload_file with missing filename."""
        # Define arguments
        args = {
            "filename": "",
            "content_base64": "SGVsbG8gV29ybGQ=",  # "Hello World" in base64
        }
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            await drive_upload_file(**args)

    async def test_upload_file_missing_content(self):
        """Test drive_upload_file with missing content."""
        # Define arguments
        args = {"filename": "test.txt", "content_base64": ""}
        with pytest.raises(
            ValueError, match="File content \\(content_base64\\) cannot be empty"
        ):
            await drive_upload_file(**args)
