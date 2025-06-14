"""
Unit tests for the DriveService.search_files method.
"""

from unittest.mock import MagicMock

from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveSearchFiles:
    """Tests for the DriveService.search_files method."""

    def test_search_files_success(self, mock_drive_service: DriveService):
        """Test successful file search without shared drive."""
        mock_api_response = {
            "files": [
                {"id": "file1", "name": "test file 1", "mimeType": "text/plain"},
                {"id": "file2", "name": "test file 2", "mimeType": "text/plain"},
            ]
        }
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = mock_api_response

        result = mock_drive_service.search_files(query="test", page_size=10)

        assert result == mock_api_response["files"]
        # Verify API call parameters
        mock_drive_service.service.files.return_value.list.assert_called_once()
        call_args = mock_drive_service.service.files.return_value.list.call_args[1]
        assert call_args["q"] == "test"
        assert call_args["pageSize"] == 10
        assert call_args["supportsAllDrives"] is True
        assert call_args["includeItemsFromAllDrives"] is True
        assert call_args["corpora"] == "user"
        assert "driveId" not in call_args

    def test_search_files_with_shared_drive(self, mock_drive_service: DriveService):
        """Test successful file search within a shared drive."""
        mock_api_response = {
            "files": [
                {"id": "file1", "name": "shared file 1", "mimeType": "text/plain"},
            ]
        }
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = mock_api_response

        result = mock_drive_service.search_files(query="shared", page_size=5, shared_drive_id="drive123")

        assert result == mock_api_response["files"]
        # Verify API call parameters for shared drive
        call_args = mock_drive_service.service.files.return_value.list.call_args[1]
        assert call_args["q"] == "shared"
        assert call_args["pageSize"] == 5
        assert call_args["supportsAllDrives"] is True
        assert call_args["includeItemsFromAllDrives"] is True
        assert call_args["corpora"] == "drive"
        assert call_args["driveId"] == "drive123"

    def test_search_files_empty_results(self, mock_drive_service: DriveService):
        """Test search with no results."""
        mock_api_response = {"files": []}
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = mock_api_response

        result = mock_drive_service.search_files(query="nonexistent")

        assert result == []

    def test_search_files_page_size_limits(self, mock_drive_service: DriveService):
        """Test that page_size is properly constrained."""
        mock_api_response = {"files": []}
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = mock_api_response

        # Test page_size too small
        mock_drive_service.search_files(query="test", page_size=0)
        call_args = mock_drive_service.service.files.return_value.list.call_args[1]
        assert call_args["pageSize"] == 1

        # Test page_size too large
        mock_drive_service.search_files(query="test", page_size=2000)
        call_args = mock_drive_service.service.files.return_value.list.call_args[1]
        assert call_args["pageSize"] == 1000

    def test_search_files_query_passthrough(self, mock_drive_service: DriveService):
        """Test that queries are passed through directly without modification."""
        mock_api_response = {"files": []}
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = mock_api_response

        mock_drive_service.search_files(query="John's file")

        call_args = mock_drive_service.service.files.return_value.list.call_args[1]
        assert call_args["q"] == "John's file"

    def test_search_files_http_error(self, mock_drive_service: DriveService):
        """Test search with HTTP error."""
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "File not found"}}')
        mock_drive_service.service.files.return_value.list.return_value.execute.side_effect = http_error

        expected_error_details = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "File not found",
            "operation": "search_files",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.search_files(query="test")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("search_files", http_error)

    def test_search_files_unexpected_error(self, mock_drive_service: DriveService):
        """Test search with unexpected error."""
        exception = Exception("Unexpected error")
        mock_drive_service.service.files.return_value.list.return_value.execute.side_effect = exception

        expected_error_details = {
            "error": True,
            "error_type": "unexpected_service_error",
            "message": "Unexpected error",
            "operation": "search_files",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.search_files(query="test")

        assert result == expected_error_details
        mock_drive_service.handle_api_error.assert_called_once_with("search_files", exception)
