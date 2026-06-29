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
    def test_upload_file_content_private(self, mock_guess_type, mock_drive_service):
        """Upload with share=False creates the file and does not share it."""
        filename = "test.txt"
        content_base64 = base64.b64encode(b"Hello, World!").decode()
        mock_guess_type.return_value = ("text/plain", None)

        mock_file_metadata = {
            "id": "uploaded_file_id",
            "name": "test.txt",
            "mimeType": "text/plain",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            mock_file_metadata
        )

        result = mock_drive_service.upload_file_content(
            filename, content_base64, share=False
        )

        mock_guess_type.assert_called_once_with(filename)
        # Now requests webContentLink in the fields, and does NOT share.
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "test.txt"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink,webContentLink,resourceKey",
            supportsAllDrives=True,
        )
        mock_drive_service.service.permissions.return_value.create.assert_not_called()
        # Even a private (share=False) upload now carries a download_url for the
        # binary file (text/plain here).
        assert result["id"] == "uploaded_file_id"
        assert (
            result["download_url"]
            == "https://drive.usercontent.google.com/download?id=uploaded_file_id"
            "&export=download&confirm=t"
        )

    @patch("mimetypes.guess_type")
    def test_upload_file_content_shared_when_requested(
        self, mock_guess_type, mock_drive_service
    ):
        """Upload with share=True grants anyone-with-link and returns webContentLink."""
        filename = "image.png"
        content_base64 = base64.b64encode(b"\x89PNG fake bytes").decode()
        mock_guess_type.return_value = ("image/png", None)

        created = {"id": "fid", "name": "image.png", "mimeType": "image/png"}
        refreshed = {
            **created,
            "webContentLink": "https://drive.google.com/uc?id=fid",
            "webViewLink": "https://drive.google.com/file/d/fid/view",
        }
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            created
        )
        mock_drive_service.service.files.return_value.get.return_value.execute.return_value = (
            refreshed
        )

        result = mock_drive_service.upload_file_content(
            filename, content_base64, share=True
        )

        # An anyone/reader permission was created on the new file.
        mock_drive_service.service.permissions.return_value.create.assert_called_once_with(
            fileId="fid",
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        )
        # Result is the refreshed metadata with the direct-download URL + flag.
        assert result["webContentLink"] == "https://drive.google.com/uc?id=fid"
        assert result["shared"] is True

    @patch("mimetypes.guess_type")
    def test_upload_share_failure_is_soft(self, mock_guess_type, mock_drive_service):
        """If sharing fails, the upload still returns the file, flagged unshared."""
        mock_guess_type.return_value = ("image/png", None)
        created = {"id": "fid", "name": "image.png", "mimeType": "image/png"}
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            created
        )
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_drive_service.service.permissions.return_value.create.return_value.execute.side_effect = HttpError(
            resp, b'{"error": {"message": "insufficient permissions"}}'
        )

        result = mock_drive_service.upload_file_content(
            "image.png", base64.b64encode(b"x").decode(), share=True
        )

        assert result["id"] == "fid"
        assert result["shared"] is False
        # 403 -> policy-specific message, and the upload is NOT lost.
        assert "policy" in result["share_error"].lower()
        assert "webContentLink" in result  # key guaranteed present

    @patch("mimetypes.guess_type")
    def test_upload_refetch_failure_keeps_file_shared(
        self, mock_guess_type, mock_drive_service
    ):
        """If the post-share re-fetch fails, the file is still returned shared."""
        mock_guess_type.return_value = ("image/png", None)
        created = {"id": "fid", "name": "image.png", "mimeType": "image/png"}
        mock_drive_service.service.files.return_value.create.return_value.execute.return_value = (
            created
        )
        # Permission grant succeeds...
        mock_drive_service.service.permissions.return_value.create.return_value.execute.return_value = {}
        # ...but the metadata re-fetch raises.
        mock_drive_service.service.files.return_value.get.return_value.execute.side_effect = Exception(
            "transient"
        )

        result = mock_drive_service.upload_file_content(
            "image.png", base64.b64encode(b"x").decode(), share=True
        )

        # Upload + share both succeeded; only the link refresh was missed.
        assert result["id"] == "fid"
        assert result["shared"] is True
        assert "share_error" not in result

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

    def test_upload_file_content_empty_decoded_bytes(self, mock_drive_service):
        """An empty base64 string decodes to 0 bytes and must be rejected."""
        result = mock_drive_service.upload_file_content("empty.txt", "")

        mock_drive_service.service.files.return_value.create.assert_not_called()
        assert result["error"] is True
        assert result["error_type"] == "invalid_content"
        assert "empty" in result["message"].lower()

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

        # Call the method (share=False keeps this focused on mime fallback)
        result = mock_drive_service.upload_file_content(
            filename, content_base64, share=False
        )

        # Verify API call with ANY media_body and correct fallback mime
        mock_drive_service.service.files.return_value.create.assert_called_once_with(
            body={"name": "unknown.bin"},
            media_body=ANY,
            fields="id,name,mimeType,modifiedTime,size,webViewLink,webContentLink,resourceKey",
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
            fields="id,name,mimeType,modifiedTime,size,webViewLink,webContentLink,resourceKey",
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
