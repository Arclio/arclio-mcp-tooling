"""
Unit tests for Google Sheets service metadata operations (get_spreadsheet_metadata).
"""

from unittest.mock import Mock

from googleapiclient.errors import HttpError


class TestSheetsServiceMetadataOperations:
    """Test class for SheetsService metadata operations."""

    def test_get_spreadsheet_metadata_success_default_fields(self, mock_sheets_service):
        """Test successful metadata retrieval with default fields."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        mock_response = {
            "spreadsheetId": spreadsheet_id,
            "properties": {
                "title": "Test Spreadsheet",
                "locale": "en_US",
                "autoRecalc": "ON_CHANGE",
                "timeZone": "America/New_York",
            },
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1",
                        "index": 0,
                        "sheetType": "GRID",
                        "gridProperties": {"rowCount": 1000, "columnCount": 26},
                    }
                }
            ],
        }

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.return_value = mock_response

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id)

        # Assert
        assert result == mock_response

        # Verify API call with default fields (check what the actual implementation uses)
        mock_sheets_service.service.spreadsheets.return_value.get.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            fields="spreadsheetId,properties,sheets(properties(sheetId,title,index,sheetType,gridProperties))",
        )

    def test_get_spreadsheet_metadata_success_custom_fields(self, mock_sheets_service):
        """Test successful metadata retrieval with custom fields."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        custom_fields = "properties.title,sheets.properties.title"
        mock_response = {
            "properties": {"title": "Test Spreadsheet"},
            "sheets": [{"properties": {"title": "Sheet1"}}],
        }

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.return_value = mock_response

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id, fields=custom_fields)

        # Assert
        assert result == mock_response

        # Verify API call with custom fields
        mock_sheets_service.service.spreadsheets.return_value.get.assert_called_once_with(
            spreadsheetId=spreadsheet_id, fields=custom_fields
        )

    def test_get_spreadsheet_metadata_http_error(self, mock_sheets_service):
        """Test get_spreadsheet_metadata with HTTP error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        http_error = HttpError(
            resp=Mock(status=404, reason="Not Found"),
            content=b'{"error": {"message": "Spreadsheet not found"}}',
        )

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.side_effect = http_error
        mock_sheets_service.handle_api_error = Mock(
            return_value={
                "error": True,
                "error_type": "http_error",
                "message": "Spreadsheet not found",
            }
        )

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "http_error"
        mock_sheets_service.handle_api_error.assert_called_once_with("get_spreadsheet_metadata", http_error)

    def test_get_spreadsheet_metadata_unexpected_error(self, mock_sheets_service):
        """Test get_spreadsheet_metadata with unexpected error."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.side_effect = Exception("Network error")

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id)

        # Assert
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert "Network error" in result["message"]

    def test_get_spreadsheet_metadata_empty_fields(self, mock_sheets_service):
        """Test get_spreadsheet_metadata with empty fields parameter."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        mock_response = {
            "spreadsheetId": spreadsheet_id,
            "properties": {"title": "Test Spreadsheet"},
        }

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.return_value = mock_response

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id, fields="")

        # Assert
        assert result == mock_response

        # Verify API call with empty fields (implementation should pass empty string as-is)
        mock_sheets_service.service.spreadsheets.return_value.get.assert_called_once_with(
            spreadsheetId=spreadsheet_id, fields=""
        )

    def test_get_spreadsheet_metadata_minimal_response(self, mock_sheets_service):
        """Test get_spreadsheet_metadata with minimal API response."""
        # Arrange
        spreadsheet_id = "test_spreadsheet_id"
        mock_response = {
            "spreadsheetId": spreadsheet_id
            # Minimal response with just the ID
        }

        mock_sheets_service.service.spreadsheets.return_value.get.return_value.execute.return_value = mock_response

        # Act
        result = mock_sheets_service.get_spreadsheet_metadata(spreadsheet_id)

        # Assert
        assert result == mock_response
        assert result["spreadsheetId"] == spreadsheet_id
