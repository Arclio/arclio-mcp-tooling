"""Test drive service write operations (upload and delete)."""

import base64
from unittest.mock import ANY, MagicMock, patch

import pytest
from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveWriteOperations:
    """Test write operations in DriveService."""

    @pytest.fixture
    def mock_drive_service(self):
        """Create a DriveService instance with mocked dependencies."""
        with (
            patch("google_workspace_mcp.auth.gauth.get_credentials"),
            patch("googleapiclient.discovery.build") as mock_build,
        ):
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            drive_service = DriveService()
            # Directly set the service to bypass lazy loading
            drive_service._service = mock_service
            return drive_service

    @patch("mimetypes.guess_type")
    def test_upload_file_content_success(self, mock_guess_type, mock_drive_service):
        """Test successful file upload from content."""
        # Setup test data
        filename = "test.txt"
        content = "Hello, World!"
        content_base64 = base64.b64encode(content.encode()).decode()
        mock_guess_type.return_value = ("text/plain", None)

        # Mock the API response
        mock_file_metadata = {
            "id": "uploaded_file_id",
            "name": "test.txt",
            "mimeType": "text/plain",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            mock_file_metadata
        )

        # Call the method
        result = mock_drive_service.upload_file_content(filename, content_base64)

        # Verify MIME type detection
        mock_guess_type.assert_called_once_with(filename)

        # Verify API call with ANY media_body
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "test.txt"},
            media_body=ANY,  # Check that some media body was passed
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )

        # Verify result
        assert result == mock_file_metadata

    def test_upload_file_content_invalid_base64(self, mock_drive_service):
        """Test upload_file_content with invalid base64 content."""
        # Setup test data
        filename = "test.txt"
        invalid_content_base64 = "invalid base64 content!"

        # Call the method
        result = mock_drive_service.upload_file_content(
            filename, invalid_content_base64
        )

        # Verify no API call was made
        mock_drive_service.service.files.return_value.create.assert_not_called()

        # Verify error response
        assert result["error"] is True
        assert result["error_type"] == "invalid_content"
        assert result["message"] == "Invalid base64 encoded content provided."
        assert result["operation"] == "upload_file_content"

    @patch("mimetypes.guess_type")
    def test_upload_file_content_unknown_mime_type(
        self, mock_guess_type, mock_drive_service
    ):
        """Test upload_file_content with unknown MIME type."""
        # Setup test data
        filename = "unknown.bin"
        content = b"\x00\x01\x02\x03"  # Binary content
        content_base64 = base64.b64encode(content).decode()
        mock_guess_type.return_value = (None, None)

        # Mock the API response
        mock_file_metadata = {
            "id": "uploaded_file_id",
            "name": "unknown.bin",
            "mimeType": "application/octet-stream",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            mock_file_metadata
        )

        # Call the method
        result = mock_drive_service.upload_file_content(filename, content_base64)

        # Verify API call with ANY media_body and correct fallback mime
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "unknown.bin"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )
        # Verify result
        assert result == mock_file_metadata

    @patch("mimetypes.guess_type")
    def test_upload_file_content_api_error(self, mock_guess_type, mock_drive_service):
        """Test upload_file_content when API call fails."""
        # Setup test data
        filename = "test.txt"
        content = "Hello, World!"
        content_base64 = base64.b64encode(content.encode()).decode()
        mock_guess_type.return_value = ("text/plain", None)

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Insufficient permissions"}}'
        )

        # Setup the create().execute() mock to raise the error
        mock_drive_service.service.files.return_value.create.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error_return = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Insufficient permissions",
            "operation": "upload_file_content",
        }
        mock_drive_service.handle_api_error = MagicMock(
            return_value=expected_error_return
        )

        # Call the method
        result = mock_drive_service.upload_file_content(filename, content_base64)

        # Verify API call was attempted
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "test.txt"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )
        mock_drive_service.service.files.return_value.create.return_value.execute.assert_called_once()

        # Verify error handling was called correctly
        mock_drive_service.handle_api_error.assert_called_once_with(
            "upload_file_content", http_error
        )
        # Verify the final result is what handle_api_error returned
        assert result == expected_error_return

    def test_delete_file_success(self, mock_drive_service):
        """Test successful file deletion."""
        # Setup file_id
        file_id = "file_to_delete_id"

        # Mock the API call
        mock_drive_service.service.files.return_value.delete.return_value.execute.return_value = (
            None  # Delete typically returns empty response
        )

        # Call the method
        result = mock_drive_service.delete_file(file_id)

        # Verify API call
        mock_drive_service.service.files.return_value.delete.assert_called_once_with(
            fileId=file_id
        )

        # Verify result
        assert result["success"] is True
        assert f"File {file_id} deleted successfully" in result["message"]

    def test_delete_file_api_error(self, mock_drive_service):
        """Test delete_file when API call fails."""
        # Setup file_id
        file_id = "nonexistent_file_id"

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "File not found"}}')

        # Setup the mock to raise the error
        mock_drive_service.service.files.return_value.delete.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "File not found",
            "operation": "delete_file",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_drive_service.delete_file(file_id)

        # Verify error handling
        mock_drive_service.handle_api_error.assert_called_once_with(
            "delete_file", http_error
        )
        assert result == expected_error

    def test_delete_file_empty_id(self, mock_drive_service):
        """Test delete_file with an empty file ID."""
        # Call the method with empty file_id
        result = mock_drive_service.delete_file("")

        # Verify no API call was made
        mock_drive_service.service.files.return_value.delete.assert_not_called()

        # Verify error response
        assert result["success"] is False
        assert "File ID cannot be empty" in result["message"]
