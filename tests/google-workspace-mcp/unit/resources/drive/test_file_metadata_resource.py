"""
Unit tests for Drive file metadata resource.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.resources.drive import get_drive_file_metadata

pytestmark = pytest.mark.anyio


class TestDriveFileMetadataResource:
    """Tests for the get_drive_file_metadata resource function."""

    @pytest.fixture
    def mock_drive_service_for_resource(self):
        """Patch DriveService for resource tests."""
        with patch("google_workspace_mcp.resources.drive.DriveService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            yield mock_service_instance

    async def test_resource_get_file_metadata_success(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource successful metadata retrieval."""
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
        mock_drive_service_for_resource.get_file_metadata.return_value = mock_metadata

        result = await get_drive_file_metadata(file_id="file123")

        assert result == mock_metadata
        mock_drive_service_for_resource.get_file_metadata.assert_called_once_with(file_id="file123")

    async def test_resource_get_file_metadata_empty_file_id(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource with empty file ID."""
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await get_drive_file_metadata(file_id="")

    async def test_resource_get_file_metadata_whitespace_file_id(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource with whitespace-only file ID."""
        with pytest.raises(ValueError, match="File ID cannot be empty"):
            await get_drive_file_metadata(file_id="   ")

    async def test_resource_get_file_metadata_service_error(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource when service returns an error."""
        error_response = {
            "error": True,
            "message": "File not found",
            "error_type": "not_found",
        }
        mock_drive_service_for_resource.get_file_metadata.return_value = error_response

        with pytest.raises(ValueError, match="File not found"):
            await get_drive_file_metadata(file_id="nonexistent")

    async def test_resource_get_file_metadata_service_unknown_error(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource when service returns error without message."""
        error_response = {"error": True, "error_type": "unknown"}
        mock_drive_service_for_resource.get_file_metadata.return_value = error_response

        with pytest.raises(ValueError, match="Error getting file metadata"):
            await get_drive_file_metadata(file_id="error_file")

    async def test_resource_get_file_metadata_comprehensive_data(self, mock_drive_service_for_resource):
        """Test get_drive_file_metadata resource with comprehensive metadata."""
        comprehensive_metadata = {
            "id": "comprehensive_file_123",
            "name": "Comprehensive Document.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size": "2048000",
            "createdTime": "2024-01-01T09:00:00.000Z",
            "modifiedTime": "2024-01-15T14:30:00.000Z",
            "webViewLink": "https://drive.google.com/file/d/comprehensive_file_123/view",
            "webContentLink": "https://drive.google.com/uc?id=comprehensive_file_123",
            "iconLink": "https://drive-thirdparty.googleusercontent.com/word_icon.png",
            "parents": ["parent_folder_789"],
            "owners": [
                {
                    "displayName": "Jane Smith",
                    "emailAddress": "jane.smith@example.com",
                    "kind": "drive#user",
                }
            ],
            "shared": True,
            "trashed": False,
            "capabilities": {"canEdit": True, "canComment": True, "canShare": True},
            "permissions": [
                {
                    "id": "permission_1",
                    "type": "user",
                    "role": "owner",
                    "emailAddress": "jane.smith@example.com",
                }
            ],
            "description": "This is a comprehensive test document",
            "starred": False,
            "explicitlyTrashed": False,
        }
        mock_drive_service_for_resource.get_file_metadata.return_value = comprehensive_metadata

        result = await get_drive_file_metadata(file_id="comprehensive_file_123")

        assert result == comprehensive_metadata
        # Verify all the rich metadata is preserved
        assert result["capabilities"]["canEdit"] is True
        assert result["owners"][0]["displayName"] == "Jane Smith"
        assert result["description"] == "This is a comprehensive test document"
