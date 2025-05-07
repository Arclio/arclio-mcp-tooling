"""
Unit tests for the DriveService.search_files method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestDriveSearchFiles:
    """Tests for the DriveService.search_files method."""

    # Removed local mock_drive_service fixture

    def test_search_files_success(self, mock_drive_service):
        """Test successful file search with results."""
        # Mock data for the API response
        mock_files = [
            {"id": "file1", "name": "test1.txt", "mimeType": "text/plain"},
            {
                "id": "file2",
                "name": "test2.pdf",
                "mimeType": "application/pdf",
                "size": "1024",
            },
        ]
        mock_response = {"files": mock_files}

        # Setup the execute mock to return our test data
        mock_execute = MagicMock(return_value=mock_response)
        mock_list = MagicMock()
        mock_list.return_value.execute = mock_execute
        mock_drive_service.service.files.return_value.list = mock_list

        # Call the method with a test query
        result = mock_drive_service.search_files(query="test query", page_size=5)

        # Verify correct API call
        mock_drive_service.service.files.return_value.list.assert_called_once_with(
            q="fullText contains 'test query' and trashed = false",
            pageSize=5,
            fields="files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink)",
        )

        # Verify result processing
        assert len(result) == 2
        assert result[0]["id"] == "file1"
        assert result[0]["name"] == "test1.txt"
        assert result[0]["size"] == 0  # Default size when not provided
        assert result[1]["id"] == "file2"
        assert result[1]["size"] == "1024"  # Preserved from input

    def test_search_files_empty_results(self, mock_drive_service):
        """Test file search with no matching files."""
        # Mock an empty result
        mock_response = {"files": []}

        # Setup the execute mock
        mock_execute = MagicMock(return_value=mock_response)
        mock_list = MagicMock()
        mock_list.return_value.execute = mock_execute
        mock_drive_service.service.files.return_value.list = mock_list

        # Call the method
        result = mock_drive_service.search_files(query="nonexistent", page_size=10)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 0

    def test_search_files_api_error(self, mock_drive_service):
        """Test file search with API error."""
        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission Denied"}}')

        # Setup the side_effect to raise the error
        mock_list = MagicMock()
        mock_list.return_value.execute.side_effect = http_error
        mock_drive_service.service.files.return_value.list = mock_list

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission Denied",
            "operation": "search_files",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_drive_service.search_files(query="test")

        # Verify error handling
        mock_drive_service.handle_api_error.assert_called_once_with("search_files", http_error)
        assert result == expected_error

    def test_search_files_unexpected_error(self, mock_drive_service):
        """Test file search with an unexpected error."""
        # Setup a generic exception
        generic_error = Exception("Unexpected failure")
        mock_list = MagicMock()
        mock_list.return_value.execute.side_effect = generic_error
        mock_drive_service.service.files.return_value.list = mock_list

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "service_error",
            "message": "Unexpected failure",
            "operation": "search_files",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_drive_service.search_files(query="test")

        # Verify error handling
        mock_drive_service.handle_api_error.assert_called_once_with("search_files", generic_error)
        assert result == expected_error
