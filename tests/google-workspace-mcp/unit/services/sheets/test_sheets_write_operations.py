"""
Unit tests for SheetsService write operations.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestSheetsWriteRange:
    """Tests for SheetsService write_range method."""

    def test_write_range_success_user_entered(self, mock_sheets_service):
        """Test successful range write with USER_ENTERED option."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:B2"
        values = [["Name", "Score"], ["Alice", 100]]
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4,
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.write_range(
            spreadsheet_id=spreadsheet_id,
            range_a1=range_a1,
            values=values,
            value_input_option="USER_ENTERED",
        )

        # Assertions
        assert result is not None
        assert result["spreadsheet_id"] == "test_sheet_123"
        assert result["updated_range"] == "Sheet1!A1:B2"
        assert result["updated_rows"] == 2
        assert result["updated_columns"] == 2
        assert result["updated_cells"] == 4

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        )

    def test_write_range_success_raw(self, mock_sheets_service):
        """Test successful range write with RAW option."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:C1"
        values = [["=SUM(1,2)", "text", 123]]
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "updatedRange": "Sheet1!A1:C1",
            "updatedRows": 1,
            "updatedColumns": 3,
            "updatedCells": 3,
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.write_range(
            spreadsheet_id=spreadsheet_id,
            range_a1=range_a1,
            values=values,
            value_input_option="RAW",
        )

        # Assertions
        assert result is not None
        assert result["updated_range"] == "Sheet1!A1:C1"
        assert result["updated_cells"] == 3

        # Verify API call uses RAW option
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="RAW",
            body={"values": values},
        )

    def test_write_range_http_error_invalid_range(self, mock_sheets_service):
        """Test write range with HTTP error due to invalid range."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "InvalidSheet!A1:B2"
        values = [["Name", "Score"]]

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid range"}}')

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error_response = {
            "error": True,
            "error_type": "invalid_range",
            "message": "Invalid range",
            "operation": "write_range",
        }
        mock_sheets_service.handle_api_error = MagicMock(
            return_value=expected_error_response
        )

        # Execute
        result = mock_sheets_service.write_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1, values=values
        )

        # Assertions
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "invalid_range"
        assert "Invalid range" in result["message"]
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "write_range", http_error
        )

    def test_write_range_empty_values(self, mock_sheets_service):
        """Test write range with empty values list."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:A1"
        values = []  # Empty values
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "updatedRange": "Sheet1!A1:A1",
            "updatedRows": 0,
            "updatedColumns": 0,
            "updatedCells": 0,
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.write_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1, values=values
        )

        # Should still succeed with empty values
        assert result is not None
        assert result["updated_cells"] == 0


class TestSheetsAppendRows:
    """Tests for SheetsService append_rows method."""

    def test_append_rows_success_insert_rows(self, mock_sheets_service):
        """Test successful row append with INSERT_ROWS option."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1"
        values = [["Bob", 90], ["Charlie", 85]]
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "tableRange": "Sheet1!A3:B4",
            "updates": {
                "updatedRange": "Sheet1!A3:B4",
                "updatedRows": 2,
                "updatedColumns": 2,
                "updatedCells": 4,
            },
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.append_rows(
            spreadsheet_id=spreadsheet_id,
            range_a1=range_a1,
            values=values,
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
        )

        # Assertions
        assert result is not None
        assert result["spreadsheet_id"] == "test_sheet_123"
        assert result["table_range_updated"] == "Sheet1!A3:B4"
        assert result["updates"]["updatedRows"] == 2

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.append.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        )

    def test_append_rows_success_overwrite(self, mock_sheets_service):
        """Test successful row append with OVERWRITE option."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:B1"
        values = [["Name", "Score"]]
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "tableRange": "Sheet1!A1:B1",
            "updates": {
                "updatedRange": "Sheet1!A1:B1",
                "updatedRows": 1,
                "updatedColumns": 2,
                "updatedCells": 2,
            },
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.append_rows(
            spreadsheet_id=spreadsheet_id,
            range_a1=range_a1,
            values=values,
            insert_data_option="OVERWRITE",
        )

        # Assertions
        assert result is not None
        assert result["table_range_updated"] == "Sheet1!A1:B1"

        # Verify API call uses OVERWRITE option
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.append.assert_called_once_with(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",  # Default
            insertDataOption="OVERWRITE",
            body={"values": values},
        )

    def test_append_rows_http_error_permission_denied(self, mock_sheets_service):
        """Test append rows with HTTP error due to permission denied."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1"
        values = [["Data"]]

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Permission denied"}}'
        )

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error_response = {
            "error": True,
            "error_type": "permission_denied",
            "message": "Permission denied",
            "operation": "append_rows",
        }
        mock_sheets_service.handle_api_error = MagicMock(
            return_value=expected_error_response
        )

        # Execute
        result = mock_sheets_service.append_rows(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1, values=values
        )

        # Assertions
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "permission_denied"
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "append_rows", http_error
        )


class TestSheetsClearRange:
    """Tests for SheetsService clear_range method."""

    def test_clear_range_success(self, mock_sheets_service):
        """Test successful range clear."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:C3"
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "clearedRange": "Sheet1!A1:C3",
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.clear.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.clear_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1
        )

        # Assertions
        assert result is not None
        assert result["spreadsheet_id"] == "test_sheet_123"
        assert result["cleared_range"] == "Sheet1!A1:C3"

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.clear.assert_called_once_with(
            spreadsheetId=spreadsheet_id, range=range_a1, body={}
        )

    def test_clear_range_entire_sheet(self, mock_sheets_service):
        """Test clearing entire sheet."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1"  # Entire sheet
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "clearedRange": "Sheet1!1:1000",  # API might return expanded range
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.clear.return_value.execute.return_value = (
            mock_response
        )

        # Execute
        result = mock_sheets_service.clear_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1
        )

        # Assertions
        assert result is not None
        assert result["cleared_range"] == "Sheet1!1:1000"

    def test_clear_range_http_error_not_found(self, mock_sheets_service):
        """Test clear range with HTTP error due to spreadsheet not found."""
        # Test data
        spreadsheet_id = "nonexistent_sheet"
        range_a1 = "Sheet1!A1:B2"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Spreadsheet not found"}}'
        )

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.clear.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error_response = {
            "error": True,
            "error_type": "not_found",
            "message": "Spreadsheet not found",
            "operation": "clear_range",
        }
        mock_sheets_service.handle_api_error = MagicMock(
            return_value=expected_error_response
        )

        # Execute
        result = mock_sheets_service.clear_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1
        )

        # Assertions
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "not_found"
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "clear_range", http_error
        )

    def test_clear_range_unexpected_exception(self, mock_sheets_service):
        """Test clear range with unexpected exception."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:B2"

        # Setup the mock to raise an unexpected exception
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.clear.return_value.execute.side_effect = ValueError(
            "Unexpected error"
        )

        # Execute
        result = mock_sheets_service.clear_range(
            spreadsheet_id=spreadsheet_id, range_a1=range_a1
        )

        # Assertions
        assert result is not None
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["operation"] == "clear_range"
        assert "Unexpected error" in result["message"]
