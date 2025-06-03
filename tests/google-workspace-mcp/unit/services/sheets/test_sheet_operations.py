"""
Unit tests for Google Sheets service sheet operations (add_sheet, delete_sheet).
"""

from unittest.mock import Mock

from googleapiclient.errors import HttpError


class TestSheetsServiceSheetOperations:
    """Test class for SheetsService sheet operations."""

    def test_add_sheet_success(self, mock_sheets_service):
        """Test successful sheet addition."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        title = "New Sheet"
        mock_response = {
            "replies": [
                {
                    "addSheet": {
                        "properties": {
                            "sheetId": 123456789,
                            "title": "New Sheet",
                            "index": 1,
                            "sheetType": "GRID",
                        }
                    }
                }
            ]
        }

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = (
            mock_response
        )

        # Act
        result = mock_sheets_service.add_sheet(spreadsheet_id, title)

        # Assert
        assert result is not None
        assert result["spreadsheet_id"] == spreadsheet_id
        assert result["sheet_properties"]["sheetId"] == 123456789
        assert result["sheet_properties"]["title"] == "New Sheet"
        assert result["sheet_properties"]["index"] == 1

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )

    def test_add_sheet_no_replies_in_response(self, mock_sheets_service):
        """Test add_sheet when response has no replies."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        title = "New Sheet"
        mock_response = {}  # No replies

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = (
            mock_response
        )

        # Act
        result = mock_sheets_service.add_sheet(spreadsheet_id, title)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "api_response_error"
        assert "Failed to add sheet or parse response" in result["message"]

    def test_add_sheet_no_addsheet_in_reply(self, mock_sheets_service):
        """Test add_sheet when reply doesn't contain addSheet."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        title = "New Sheet"
        mock_response = {"replies": [{"someOtherReply": {}}]}

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = (
            mock_response
        )

        # Act
        result = mock_sheets_service.add_sheet(spreadsheet_id, title)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "api_response_error"

    def test_add_sheet_http_error(self, mock_sheets_service):
        """Test add_sheet with HTTP error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        title = "New Sheet"
        http_error = HttpError(
            resp=Mock(status=400, reason="Bad Request"),
            content=b'{"error": {"message": "Invalid spreadsheet ID"}}',
        )

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect = (
            http_error
        )
        mock_sheets_service.handle_api_error = Mock(
            return_value={
                "error": True,
                "error_type": "http_error",
                "message": "Invalid spreadsheet ID",
            }
        )

        # Act
        result = mock_sheets_service.add_sheet(spreadsheet_id, title)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "http_error"
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "add_sheet", http_error
        )

    def test_add_sheet_unexpected_error(self, mock_sheets_service):
        """Test add_sheet with unexpected error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        title = "New Sheet"

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect = Exception(
            "Unexpected error"
        )

        # Act
        result = mock_sheets_service.add_sheet(spreadsheet_id, title)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert "Unexpected error" in result["message"]

    def test_delete_sheet_success(self, mock_sheets_service):
        """Test successful sheet deletion."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        sheet_id = 123456789
        mock_response = {
            "spreadsheetId": spreadsheet_id,
            "replies": [{}],  # deleteSheet typically returns empty reply
        }

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = (
            mock_response
        )

        # Act
        result = mock_sheets_service.delete_sheet(spreadsheet_id, sheet_id)

        # Assert
        assert result is not None
        assert result["spreadsheet_id"] == spreadsheet_id
        assert result["deleted_sheet_id"] == sheet_id
        assert result["success"] is True

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"deleteSheet": {"sheetId": sheet_id}}]},
        )

    def test_delete_sheet_http_error(self, mock_sheets_service):
        """Test delete_sheet with HTTP error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        sheet_id = 123456789
        http_error = HttpError(
            resp=Mock(status=400, reason="Bad Request"),
            content=b'{"error": {"message": "Sheet not found"}}',
        )

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect = (
            http_error
        )
        mock_sheets_service.handle_api_error = Mock(
            return_value={
                "error": True,
                "error_type": "http_error",
                "message": "Sheet not found",
            }
        )

        # Act
        result = mock_sheets_service.delete_sheet(spreadsheet_id, sheet_id)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "http_error"
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "delete_sheet", http_error
        )

    def test_delete_sheet_unexpected_error(self, mock_sheets_service):
        """Test delete_sheet with unexpected error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        sheet_id = 123456789

        mock_sheets_service.service.spreadsheets.return_value.batchUpdate.return_value.execute.side_effect = Exception(
            "Unexpected error"
        )

        # Act
        result = mock_sheets_service.delete_sheet(spreadsheet_id, sheet_id)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert "Unexpected error" in result["message"]
