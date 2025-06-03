"""
Unit tests for Drive drive_read_file_content tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_read_file_content

pytestmark = pytest.mark.anyio


class TestDriveReadFileContentTool:
    """Tests for the drive_read_file_content tool function."""

    @pytest.fixture
    def mock_drive_service_for_tool(self):
        """Patch DriveService for tool tests."""
        with patch("google_workspace_mcp.tools.drive.DriveService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            yield mock_service_instance

    async def test_tool_read_file_content_successful_text_file_read(self, mock_drive_service_for_tool):
        """Test drive_read_file_content successful text file read."""
        mock_file_content = {
            "content": "This is the file content",
            "mimeType": "text/plain",
            "name": "test.txt",
        }
        mock_drive_service_for_tool.read_file_content.return_value = mock_file_content

        args = {"file_id": "valid_file_id_123"}
        result = await drive_read_file_content(**args)

        assert result == mock_file_content
        mock_drive_service_for_tool.read_file_content.assert_called_once_with(file_id="valid_file_id_123")

    async def test_tool_read_file_content_successful_binary_file_read(self, mock_drive_service_for_tool):
        """Test drive_read_file_content successful binary file read."""
        mock_file_content = {
            "data": "base64encodeddata",
            "mimeType": "application/pdf",
            "name": "document.pdf",
        }
        mock_drive_service_for_tool.read_file_content.return_value = mock_file_content

        args = {"file_id": "pdf_file_id_456"}
        result = await drive_read_file_content(**args)

        assert result == mock_file_content
        mock_drive_service_for_tool.read_file_content.assert_called_once_with(file_id="pdf_file_id_456")

    async def test_tool_read_file_content_when_service_call_fails(self, mock_drive_service_for_tool):
        """Test drive_read_file_content when the service call fails."""
        error_response = {"error": True, "message": "File not found"}
        mock_drive_service_for_tool.read_file_content.return_value = error_response

        args = {"file_id": "nonexistent_file_id"}
        with pytest.raises(ValueError, match="File not found"):
            await drive_read_file_content(**args)

    async def test_tool_read_file_content_when_service_returns_none(self, mock_drive_service_for_tool):
        """Test drive_read_file_content when the service returns None (unexpected)."""
        mock_drive_service_for_tool.read_file_content.return_value = None

        args = {"file_id": "some_file_id"}
        with pytest.raises(ValueError, match="File not found or could not be read"):
            await drive_read_file_content(**args)

    async def test_tool_read_file_content_validation_for_empty_file_id(self, mock_drive_service_for_tool):
        """Test drive_read_file_content tool validation for empty file_id."""
        args = {"file_id": ""}
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await drive_read_file_content(**args)

    async def test_tool_read_file_content_whitespace_file_id(self, mock_drive_service_for_tool):
        """Test drive_read_file_content tool validation for whitespace-only file_id."""
        args = {"file_id": "   "}
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await drive_read_file_content(**args)

    async def test_tool_read_file_content_error_without_message(self, mock_drive_service_for_tool):
        """Test drive_read_file_content when service returns error without message."""
        error_response = {"error": True, "error_type": "unknown"}
        mock_drive_service_for_tool.read_file_content.return_value = error_response

        args = {"file_id": "error_file_id"}
        with pytest.raises(ValueError, match="Error reading file"):
            await drive_read_file_content(**args)
