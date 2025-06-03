"""
Unit tests for the DriveService.read_file method and its helper methods.
"""

import base64
from unittest.mock import MagicMock, patch

from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveReadFile:
    """Tests for the DriveService.read_file method and its helper methods."""

    # Removed local mock_drive_service fixture

    def test_read_file_google_doc(self, mock_drive_service):
        """Test read_file_content with a Google Document."""
        # Setup file metadata for a Google Doc
        file_id = "doc123"
        file_metadata = {
            "id": file_id,
            "name": "Test Document",
            "mimeType": "application/vnd.google-apps.document",
        }

        # Setup mocks
        mock_drive_service.service.files.return_value.get.return_value.execute.return_value = file_metadata

        # Mock the export method
        expected_result = {
            "mimeType": "text/plain",
            "content": "Document content",
            "encoding": "utf-8",
        }

        with patch.object(mock_drive_service, "_export_google_file", return_value=expected_result) as mock_export:
            result = mock_drive_service.read_file_content(file_id)

        # Verify the export method was called
        mock_export.assert_called_once_with(file_id, "Test Document", "application/vnd.google-apps.document")
        assert result == expected_result

    def test_read_file_regular_file(self, mock_drive_service):
        """Test read_file_content with a regular text file."""
        # Setup file metadata for a regular file
        file_id = "text123"
        file_metadata = {"id": file_id, "name": "test.txt", "mimeType": "text/plain"}

        # Setup mocks
        mock_drive_service.service.files.return_value.get.return_value.execute.return_value = file_metadata

        # Mock the download method
        expected_result = {
            "mimeType": "text/plain",
            "content": "File content",
            "encoding": "utf-8",
        }

        with patch.object(mock_drive_service, "_download_regular_file", return_value=expected_result) as mock_download:
            result = mock_drive_service.read_file_content(file_id)

        # Verify the download method was called
        mock_download.assert_called_once_with(file_id, "test.txt", "text/plain")
        assert result == expected_result

    def test_read_file_metadata_error(self, mock_drive_service):
        """Test read_file_content when getting file metadata fails."""
        file_id = "nonexistent"

        # Create mock HTTP error
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "File Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "File not found"}}')

        # Setup the mock to raise the error
        mock_drive_service.service.files.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "File not found",
            "operation": "read_file",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_drive_service.read_file_content(file_id)

        # Verify error handling
        mock_drive_service.handle_api_error.assert_called_once_with("read_file", http_error)
        assert result == expected_error

    @patch.object(DriveService, "_download_content")
    def test_export_google_doc(self, mock_download_content, mock_drive_service):
        """Test _export_google_file with a Google Document."""
        file_id = "doc123"
        file_name = "Test Document"
        mime_type = "application/vnd.google-apps.document"
        content_bytes = b"Document content in plain text"

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify export_media was called with correct parameters
        mock_drive_service.service.files.return_value.export_media.assert_called_once_with(
            fileId=file_id, mimeType="text/markdown"
        )

        # Verify _download_content was called
        mock_download_content.assert_called_once()

        # Verify result format and content
        assert result["mimeType"] == "text/markdown"
        assert result["content"] == "Document content in plain text"
        assert result["encoding"] == "utf-8"

    @patch.object(DriveService, "_download_content")
    def test_export_google_spreadsheet(self, mock_download_content, mock_drive_service):
        """Test _export_google_file with a Google Spreadsheet."""
        file_id = "sheet123"
        file_name = "Test Spreadsheet"
        mime_type = "application/vnd.google-apps.spreadsheet"
        content_bytes = b"col1,col2\nval1,val2\n"

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify export_media was called with correct parameters
        mock_drive_service.service.files.return_value.export_media.assert_called_once_with(fileId=file_id, mimeType="text/csv")

        # Verify result format and content
        assert result["mimeType"] == "text/csv"
        assert result["content"] == "col1,col2\nval1,val2\n"
        assert result["encoding"] == "utf-8"

    @patch.object(DriveService, "_download_content")
    def test_export_google_presentation(self, mock_download_content, mock_drive_service):
        """Test _export_google_file with a Google Presentation."""
        file_id = "pres123"
        file_name = "Test Presentation"
        mime_type = "application/vnd.google-apps.presentation"
        content_bytes = b"Presentation in text format"

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify export_media was called with correct parameters
        mock_drive_service.service.files.return_value.export_media.assert_called_once_with(
            fileId=file_id, mimeType="text/plain"
        )

        # Verify result format and content
        assert result["mimeType"] == "text/plain"
        assert result["content"] == "Presentation in text format"
        assert result["encoding"] == "utf-8"

    @patch.object(DriveService, "_download_content")
    def test_export_google_drawing(self, mock_download_content, mock_drive_service):
        """Test _export_google_file with a Google Drawing."""
        file_id = "drawing123"
        file_name = "Test Drawing"
        mime_type = "application/vnd.google-apps.drawing"
        content_bytes = b"\x89PNG\r\n\x1a\n"  # Mock PNG file header

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify export_media was called with correct parameters
        mock_drive_service.service.files.return_value.export_media.assert_called_once_with(
            fileId=file_id, mimeType="image/png"
        )

        # Verify result format and content (base64 encoded)
        assert result["mimeType"] == "image/png"
        assert result["content"] == base64.b64encode(content_bytes).decode("utf-8")
        assert "encoding" not in result or result["encoding"] == "base64"

    @patch.object(DriveService, "_download_content")
    def test_export_google_doc_markdown(self, mock_download_content, mock_drive_service):
        """Test _export_google_file with a Google Document exporting as Markdown."""
        file_id = "doc123"
        file_name = "Test Document"
        mime_type = "application/vnd.google-apps.document"
        content_bytes = b"# Heading\n\nThis is markdown content."

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify export_media was called with correct parameters
        mock_drive_service.service.files.return_value.export_media.assert_called_once_with(
            fileId=file_id,
            mimeType="text/markdown",  # Assuming this is the intended export type
        )

        # Verify _download_content was called
        mock_download_content.assert_called_once()

        # Verify result format and content
        assert result["mimeType"] == "text/markdown"
        assert result["content"] == "# Heading\n\nThis is markdown content."
        assert result["encoding"] == "utf-8"

    def test_export_google_unsupported(self, mock_drive_service):
        """Test _export_google_file with an unsupported Google file type."""
        file_id = "unknown123"
        file_name = "Unknown Type"
        mime_type = "application/vnd.google-apps.unknown"

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify the error response
        assert result["error"] is True
        assert result["error_type"] == "unsupported_type"
        assert "Unsupported Google Workspace file type" in result["message"]
        assert result["operation"] == "_export_google_file"

    @patch.object(DriveService, "_download_content")
    def test_export_google_download_error(self, mock_download_content, mock_drive_service):
        """Test _export_google_file when download fails."""
        file_id = "doc123"
        file_name = "Error Document"
        mime_type = "application/vnd.google-apps.document"

        # Setup error response
        error_response = {
            "error": True,
            "error_type": "http_error",
            "status_code": 500,
            "message": "Internal Server Error",
            "operation": "_download_content",
        }
        mock_download_content.return_value = error_response

        # Call the method
        result = mock_drive_service._export_google_file(file_id, file_name, mime_type)

        # Verify the error is propagated
        assert result == error_response

    @patch.object(DriveService, "_download_content")
    def test_download_regular_utf8_text(self, mock_download_content, mock_drive_service):
        """Test _download_regular_file with UTF-8 decodable text."""
        file_id = "text123"
        mime_type = "text/plain"
        content_bytes = b"Hello, world!"

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._download_regular_file(file_id, "text.txt", mime_type)

        # Verify get_media was called with correct parameters
        mock_drive_service.service.files.return_value.get_media.assert_called_once_with(fileId=file_id)

        # Verify _download_content was called
        mock_download_content.assert_called_once()

        # Verify result format and content
        assert result["mimeType"] == mime_type
        assert result["content"] == "Hello, world!"
        assert result["encoding"] == "utf-8"

    @patch.object(DriveService, "_download_content")
    def test_download_regular_base64_fallback(self, mock_download_content, mock_drive_service):
        """Test _download_regular_file with text that requires base64 fallback."""
        file_id = "binary123"
        mime_type = "text/plain"
        content_bytes = bytes([0xFF, 0xFE, 0x00])  # Bytes that fail UTF-8 and Latin-1 decoding

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._download_regular_file(file_id, "binary.txt", mime_type)

        # Verify result format and content (base64 encoded)
        assert result["mimeType"] == mime_type
        assert result["content"] == base64.b64encode(content_bytes).decode("utf-8")
        assert result["encoding"] == "base64"

    @patch.object(DriveService, "_download_content")
    def test_download_json_file(self, mock_download_content, mock_drive_service):
        """Test _download_regular_file with a JSON file."""
        file_id = "json123"
        mime_type = "application/json"
        content_bytes = b'{"key": "value"}'

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._download_regular_file(file_id, "data.json", mime_type)

        # Verify result format and content
        assert result["mimeType"] == mime_type
        assert result["content"] == '{"key": "value"}'
        assert result["encoding"] == "utf-8"

    @patch.object(DriveService, "_download_content")
    def test_download_binary_file(self, mock_download_content, mock_drive_service):
        """Test _download_regular_file with a binary file."""
        file_id = "image123"
        mime_type = "image/png"
        content_bytes = b"\x89PNG\r\n\x1a\n"  # Mock PNG file header

        # Setup mocks
        mock_download_content.return_value = content_bytes

        # Call the method
        result = mock_drive_service._download_regular_file(file_id, "image.png", mime_type)

        # Verify result format and content (base64 encoded)
        assert result["mimeType"] == mime_type
        assert result["content"] == base64.b64encode(content_bytes).decode("utf-8")
        assert result["encoding"] == "base64"

    @patch.object(DriveService, "_download_content")
    def test_download_regular_error(self, mock_download_content, mock_drive_service):
        """Test _download_regular_file when download fails."""
        file_id = "file123"
        mime_type = "text/plain"

        # Setup error response
        error_response = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission Denied",
            "operation": "_download_content",
        }
        mock_download_content.return_value = error_response

        # Call the method
        result = mock_drive_service._download_regular_file(file_id, "error.txt", mime_type)

        # Verify the error is propagated
        assert result == error_response

    @patch("google_workspace_mcp.services.drive.io.BytesIO")
    @patch("google_workspace_mcp.services.drive.MediaIoBaseDownload")
    def test_download_content_success(self, mock_media_download_class, mock_bytesio_class, mock_drive_service):
        """Test _download_content with successful download."""
        # Setup mocks
        mock_request = MagicMock()
        mock_fh = MagicMock()
        mock_bytesio_class.return_value = mock_fh

        mock_downloader = MagicMock()
        mock_media_download_class.return_value = mock_downloader

        # Mock next_chunk to return done=True on second call
        mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]

        # Mock getvalue to return content
        mock_content = b"Downloaded content"
        mock_fh.getvalue.return_value = mock_content

        # Call the method
        result = mock_drive_service._download_content(mock_request)

        # Verify BytesIO and MediaIoBaseDownload were used correctly
        mock_bytesio_class.assert_called_once()
        mock_media_download_class.assert_called_once_with(mock_fh, mock_request)

        # Verify next_chunk was called twice
        assert mock_downloader.next_chunk.call_count == 2

        # Verify the content was retrieved
        mock_fh.getvalue.assert_called_once()

        # Verify the result
        assert result == mock_content

    @patch("google_workspace_mcp.services.drive.io.BytesIO")
    @patch("google_workspace_mcp.services.drive.MediaIoBaseDownload")
    def test_download_content_error(self, mock_media_download_class, mock_bytesio_class, mock_drive_service):
        """Test _download_content when an error occurs."""
        # Setup mocks
        mock_request = MagicMock()
        mock_fh = MagicMock()
        mock_bytesio_class.return_value = mock_fh

        mock_downloader = MagicMock()
        mock_media_download_class.return_value = mock_downloader

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.reason = "Internal Server Error"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Server Error"}}')

        # Mock next_chunk to raise an error
        mock_downloader.next_chunk.side_effect = http_error

        # Mock handle_api_error
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 500,
            "message": "Server Error",
            "operation": "_download_content",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_drive_service._download_content(mock_request)

        # Verify error handling
        mock_drive_service.handle_api_error.assert_called_once_with("download_content", http_error)
        assert result == expected_error
