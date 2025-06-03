"""
Unit tests for the DriveService.list_shared_drives method.
"""

from unittest.mock import MagicMock

from google_workspace_mcp.services.drive import DriveService
from googleapiclient.errors import HttpError


class TestDriveListSharedDrives:
    """Tests for the DriveService.list_shared_drives method."""

    def test_list_shared_drives_success(self, mock_drive_service: DriveService):
        """Test successful shared drives listing with results."""
        mock_api_response = {
            "drives": [
                {
                    "kind": "drive#drive",
                    "id": "drive_id_1",
                    "name": "Marketing Shared Drive",
                },
                {
                    "kind": "drive#drive",
                    "id": "drive_id_2",
                    "name": "Sales Shared Drive",
                },
            ]
        }
        mock_drive_service.service.drives.return_value.list.return_value.execute.return_value = mock_api_response

        result = mock_drive_service.list_shared_drives(page_size=10)

        mock_drive_service.service.drives.return_value.list.assert_called_once_with(
            pageSize=10, fields="drives(id, name, kind)"
        )
        assert result == [
            {"id": "drive_id_1", "name": "Marketing Shared Drive"},
            {"id": "drive_id_2", "name": "Sales Shared Drive"},
        ]
        assert len(result) == 2

    def test_list_shared_drives_empty(self, mock_drive_service: DriveService):
        """Test shared drives listing with no results."""
        mock_drive_service.service.drives.return_value.list.return_value.execute.return_value = {"drives": []}
        result = mock_drive_service.list_shared_drives()
        assert result == []

    def test_list_shared_drives_http_error(self, mock_drive_service: DriveService):
        """Test shared drives listing with HTTP error."""
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "API permission denied"}}')
        mock_drive_service.service.drives.return_value.list.return_value.execute.side_effect = http_error

        expected_error_details = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "API permission denied",
            "operation": "list_shared_drives",
        }
        mock_drive_service.handle_api_error = MagicMock(return_value=expected_error_details)

        result = mock_drive_service.list_shared_drives()
        mock_drive_service.handle_api_error.assert_called_once_with("list_shared_drives", http_error)
        assert result == expected_error_details

    def test_list_shared_drives_page_size_clamping(self, mock_drive_service: DriveService):
        """Test page size parameter clamping to valid range."""
        mock_drive_service.service.drives.return_value.list.return_value.execute.return_value = {"drives": []}

        # Test exceeds max
        mock_drive_service.list_shared_drives(page_size=200)
        args, kwargs = mock_drive_service.service.drives.return_value.list.call_args
        assert kwargs["pageSize"] == 100

        # Test below min
        mock_drive_service.list_shared_drives(page_size=0)
        args, kwargs = mock_drive_service.service.drives.return_value.list.call_args
        assert kwargs["pageSize"] == 1

    def test_list_shared_drives_filter_invalid_drives(self, mock_drive_service: DriveService):
        """Test filtering out drives with missing or invalid properties."""
        mock_api_response = {
            "drives": [
                {"kind": "drive#drive", "id": "drive_id_1", "name": "Valid Drive"},
                {"kind": "drive#drive", "id": "", "name": "Empty ID Drive"},  # Empty ID
                {"kind": "drive#drive", "id": "drive_id_3", "name": ""},  # Empty name
                {"kind": "drive#drive", "id": "drive_id_4"},  # Missing name
                {
                    "kind": "something#else",
                    "id": "drive_id_5",
                    "name": "Wrong Kind",
                },  # Wrong kind
                {
                    "kind": "drive#drive",
                    "id": "drive_id_6",
                    "name": "Another Valid Drive",
                },
            ]
        }
        mock_drive_service.service.drives.return_value.list.return_value.execute.return_value = mock_api_response

        result = mock_drive_service.list_shared_drives()

        # Only valid drives should be returned
        assert result == [
            {"id": "drive_id_1", "name": "Valid Drive"},
            {"id": "drive_id_6", "name": "Another Valid Drive"},
        ]
        assert len(result) == 2

    def test_list_shared_drives_unexpected_error(self, mock_drive_service: DriveService):
        """Test shared drives listing with unexpected error."""
        unexpected_error = ValueError("Some unexpected error")
        mock_drive_service.service.drives.return_value.list.return_value.execute.side_effect = unexpected_error

        result = mock_drive_service.list_shared_drives()

        # Should return error dict for unexpected errors
        assert result == {
            "error": True,
            "error_type": "unexpected_service_error",
            "message": "Some unexpected error",
            "operation": "list_shared_drives",
        }
