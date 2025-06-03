"""
Unit tests for Drive gdrive_read_file tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import gdrive_read_file

pytestmark = pytest.mark.anyio


class TestGdriveReadFileTool:
    """Tests for the gdrive_read_file tool function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Patch DriveService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.drive.DriveService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_read_success_text(self, mock_drive_service):
        """Test gdrive_read_file successful text file read."""
        mock_service_response = {
            "mimeType": "text/plain",
            "content": "This is the file content.",
            "encoding": "utf-8",
            "filename": "myfile.txt",
        }
        mock_drive_service.read_file.return_value = mock_service_response

        args = {"file_id": "file_txt_123"}
        result = await gdrive_read_file(**args)

        mock_drive_service.read_file.assert_called_once_with(file_id="file_txt_123")
        assert result == mock_service_response

    async def test_read_success_binary(self, mock_drive_service):
        """Test gdrive_read_file successful binary file read."""
        mock_service_response = {
            "mimeType": "image/png",
            "data": "base64encodedstring",
            "encoding": "base64",
            "filename": "image.png",
        }
        mock_drive_service.read_file.return_value = mock_service_response

        args = {"file_id": "file_png_456"}
        result = await gdrive_read_file(**args)

        mock_drive_service.read_file.assert_called_once_with(file_id="file_png_456")
        assert result == mock_service_response

    async def test_read_service_error(self, mock_drive_service):
        """Test gdrive_read_file when the service call fails."""
        mock_drive_service.read_file.return_value = {
            "error": True,
            "message": "API Error: File not found",
        }

        args = {"file_id": "nonexistent_id"}
        with pytest.raises(ValueError, match="API Error: File not found"):
            await gdrive_read_file(**args)

    async def test_read_service_returns_none(self, mock_drive_service):
        """Test gdrive_read_file when the service returns None (unexpected)."""
        mock_drive_service.read_file.return_value = None

        args = {"file_id": "weird_case_id"}
        with pytest.raises(
            ValueError, match="Failed to read file with ID 'weird_case_id'"
        ):
            await gdrive_read_file(**args)

    async def test_read_empty_file_id(self):
        """Test gdrive_read_file tool validation for empty file_id."""
        args = {"file_id": ""}
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await gdrive_read_file(**args)
