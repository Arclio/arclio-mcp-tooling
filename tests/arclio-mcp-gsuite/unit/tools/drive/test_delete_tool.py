"""
Unit tests for the gdrive_delete_file tool function.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.drive import gdrive_delete_file

pytestmark = pytest.mark.anyio


class TestDriveDeleteFile:
    """Tests for the gdrive_delete_file function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Create a patched DriveService for tool tests."""
        with patch("arclio_mcp_gsuite.tools.drive.DriveService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_delete_file_success(self, mock_drive_service):
        """Test gdrive_delete_file with successful deletion."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "success": True,
            "message": "File file123 deleted successfully",
        }
        mock_drive_service.delete_file.return_value = mock_service_response

        # Define arguments (use 'user_id')
        args = {"user_id": "user@example.com", "file_id": "file123"}

        # Call the function
        result = await gdrive_delete_file(**args)

        # Verify service call
        mock_drive_service.delete_file.assert_called_once_with(file_id="file123")
        # Verify raw result
        assert result == mock_service_response

    async def test_delete_file_service_error(self, mock_drive_service):
        """Test gdrive_delete_file when the service returns an error."""
        # Setup mock error response
        mock_drive_service.delete_file.return_value = {
            "error": True,
            "message": "File not found via API",
            "error_type": "http_error",
        }

        # Define arguments (use 'user_id')
        args = {"user_id": "user@example.com", "file_id": "not_a_file"}

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="File not found via API"):
            await gdrive_delete_file(**args)

        # Verify service call
        mock_drive_service.delete_file.assert_called_once_with(file_id="not_a_file")

    async def test_delete_file_missing_id(self):
        """Test gdrive_delete_file with missing file_id."""
        # Define arguments (use 'user_id')
        args = {"user_id": "user@example.com", "file_id": ""}
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await gdrive_delete_file(**args)
