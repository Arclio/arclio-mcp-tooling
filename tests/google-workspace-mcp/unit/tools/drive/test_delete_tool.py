"""
Unit tests for Drive drive_delete_file tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_delete_file

pytestmark = pytest.mark.anyio


class TestDriveDeleteFile:
    """Tests for the drive_delete_file tool function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Patch DriveService for tool tests."""
        with patch("google_workspace_mcp.tools.drive.DriveService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_delete_file_success(self, mock_drive_service):
        """Test drive_delete_file with successful deletion."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "success": True,
            "message": "File file123 deleted successfully",
        }
        mock_drive_service.delete_file.return_value = mock_service_response

        # Define arguments (removed 'user_id')
        args = {"file_id": "file123"}

        # Call the function
        result = await drive_delete_file(**args)

        # Verify the service call
        mock_drive_service.delete_file.assert_called_once_with(file_id="file123")
        assert result == mock_service_response

    async def test_delete_file_service_error(self, mock_drive_service):
        """Test drive_delete_file when the service returns an error."""
        # Setup mock error response
        mock_drive_service.delete_file.return_value = {
            "error": True,
            "message": "File not found via API",
            "error_type": "http_error",
        }

        # Define arguments (removed 'user_id')
        args = {"file_id": "not_a_file"}

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="File not found via API"):
            await drive_delete_file(**args)

    async def test_delete_file_missing_id(self):
        """Test drive_delete_file with missing file_id."""
        # Define arguments (removed 'user_id')
        args = {"file_id": ""}
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await drive_delete_file(**args)
