"""
Unit tests for the DriveService write operations (upload_file and delete_file).
"""

from unittest.mock import ANY, MagicMock, mock_open, patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError

# from google_workspace_mcp.services.drive import DriveService # Removed unused import


class TestDriveWriteOperations:
    """Tests for the DriveService write operations (upload_file and delete_file)."""

    # Removed local mock_drive_service fixture

    @patch("builtins.open", new_callable=mock_open)
    @patch("mimetypes.guess_type")
    @patch("os.path.exists")
    def test_upload_file_success(self, mock_exists, mock_guess_type, mock_open_func, mock_drive_service):
        """Test successful file upload."""
        # Setup mocks
        file_path = "/fake/path/file.txt"
        mock_exists.return_value = True
        mock_guess_type.return_value = ("text/plain", None)

        # Mock the API response
        mock_file_metadata = {
            "id": "uploaded_file_id",
            "name": "file.txt",
            "mimeType": "text/plain",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_file_metadata

        # Call the method
        result = mock_drive_service.upload_file(file_path)

        # Verify file existence check
        mock_exists.assert_called_once_with(file_path)

        # Verify MIME type detection
        mock_guess_type.assert_called_once_with(file_path)

        # Verify open was called (by MediaFileUpload internally)
        mock_open_func.assert_called_once_with(file_path, "rb")

        # Verify API call with ANY media_body
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "file.txt"},
            media_body=ANY,  # Check that some media body was passed
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )

        # Verify result
        assert result == mock_file_metadata

    @patch("os.path.exists")
    def test_upload_file_not_found(self, mock_exists, mock_drive_service):
        """Test upload_file when the local file doesn't exist."""
        # Setup mocks
        file_path = "/fake/path/nonexistent.txt"
        mock_exists.return_value = False

        # Call the method
        result = mock_drive_service.upload_file(file_path)

        # Verify file existence check
        mock_exists.assert_called_once_with(file_path)

        # Verify no API call was made
        mock_drive_service.service.files.return_value.create.assert_not_called()

        # Verify error response
        assert result["error"] is True
        assert result["error_type"] == "local_file_error"
        assert f"Local file not found: {file_path}" == result["message"]
        assert result["operation"] == "upload_file"

    @patch("builtins.open", new_callable=mock_open)
    @patch("mimetypes.guess_type")
    @patch("os.path.exists")
    def test_upload_file_unknown_mime_type(self, mock_exists, mock_guess_type, mock_open_func, mock_drive_service):
        """Test upload_file with unknown MIME type."""
        # Setup mocks
        file_path = "/fake/path/unknown.bin"
        mock_exists.return_value = True
        mock_guess_type.return_value = (None, None)

        # Mock the API response
        mock_file_metadata = {
            "id": "uploaded_file_id",
            "name": "unknown.bin",
            "mimeType": "application/octet-stream",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = mock_file_metadata

        # Call the method
        result = mock_drive_service.upload_file(file_path)

        # Verify open was called
        mock_open_func.assert_called_once_with(file_path, "rb")

        # Verify API call with ANY media_body and correct fallback mime
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "unknown.bin"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )
        # Verify result
        assert result == mock_file_metadata

    @patch("builtins.open", new_callable=mock_open)
    @patch("mimetypes.guess_type")
    @patch("os.path.exists")
    def test_upload_file_api_error(self, mock_exists, mock_guess_type, mock_open_func, mock_drive_service):
        """Test upload_file when API call fails."""
        # Setup mocks
        file_path = "/fake/path/file.txt"
        mock_exists.return_value = True
        mock_guess_type.return_value = ("text/plain", None)

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Insufficient permissions"}}')

        # Setup the create().execute() mock to raise the error
        mock_drive_service.service.files.return_value.create.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error_return = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Insufficient permissions",
            "operation": "upload_file",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_return)

        # Call the method
        result = mock_drive_service.upload_file(file_path)

        # Verify open was called
        mock_open_func.assert_called_once_with(file_path, "rb")

        # Verify API call was attempted
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "file.txt"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink",
            supportsAllDrives=True,
        )
        mock_drive_service.service.files.return_value.create.return_value.execute.assert_called_once()

        # Verify error handling was called correctly
        mock_drive_service.handle_api_error.assert_called_once_with("upload_file", http_error)
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
        mock_drive_service.service.files.return_value.delete.assert_called_once_with(fileId=file_id)

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
        mock_drive_service.service.files.return_value.delete.return_value.execute.side_effect = http_error

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
        mock_drive_service.handle_api_error.assert_called_once_with("delete_file", http_error)
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
