"""
Unit tests for SheetsService read_range method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestSheetsReadRange:
    """Tests for SheetsService read_range method."""

    def test_read_range_success_with_data(self, mock_sheets_service):
        """Test successful range reading with data."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:C3"
        mock_response = {
            "range": "Sheet1!A1:C3",
            "majorDimension": "ROWS",
            "values": [
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "San Francisco"],
            ],
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify API call
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.assert_called_once_with(
            spreadsheetId=spreadsheet_id, range=range_a1
        )

        # Verify result
        expected_result = {
            "spreadsheet_id": spreadsheet_id,
            "range_requested": range_a1,
            "range_returned": "Sheet1!A1:C3",
            "major_dimension": "ROWS",
            "values": [
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "San Francisco"],
            ],
        }
        assert result == expected_result

    def test_read_range_success_empty_values(self, mock_sheets_service):
        """Test successful range reading but with no values (empty range)."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:C3"
        mock_response = {
            "range": "Sheet1!A1:C3",
            "majorDimension": "ROWS",
            # No 'values' field
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify result handles missing values gracefully
        expected_result = {
            "spreadsheet_id": spreadsheet_id,
            "range_requested": range_a1,
            "range_returned": "Sheet1!A1:C3",
            "major_dimension": "ROWS",
            "values": [],  # Should default to empty list
        }
        assert result == expected_result

    def test_read_range_success_different_range_notation(self, mock_sheets_service):
        """Test reading with different A1 notation formats."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "A1:B2"  # Simple notation without sheet name
        mock_response = {
            "range": "Sheet1!A1:B2",  # API might expand to include sheet name
            "majorDimension": "ROWS",
            "values": [["X", "Y"], ["1", "2"]],
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify result
        expected_result = {
            "spreadsheet_id": spreadsheet_id,
            "range_requested": range_a1,
            "range_returned": "Sheet1!A1:B2",
            "major_dimension": "ROWS",
            "values": [["X", "Y"], ["1", "2"]],
        }
        assert result == expected_result

    def test_read_range_http_error_invalid_range(self, mock_sheets_service):
        """Test read range with HTTP error due to invalid range."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "InvalidSheet!A1:C3"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid range"}}')

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid range",
            "operation": "read_range",
        }
        mock_sheets_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify error handling
        mock_sheets_service.handle_api_error.assert_called_once_with("read_range", http_error)
        assert result == expected_error

    def test_read_range_http_error_not_found(self, mock_sheets_service):
        """Test read range with HTTP error due to spreadsheet not found."""
        # Test data
        spreadsheet_id = "nonexistent_sheet"
        range_a1 = "Sheet1!A1:B2"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Spreadsheet not found"}}')

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Spreadsheet not found",
            "operation": "read_range",
        }
        mock_sheets_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify error handling
        mock_sheets_service.handle_api_error.assert_called_once_with("read_range", http_error)
        assert result == expected_error

    def test_read_range_unexpected_error(self, mock_sheets_service):
        """Test read range with unexpected error."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:B2"

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = (
            unexpected_error
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "read_range"

    def test_read_range_mixed_data_types(self, mock_sheets_service):
        """Test reading range with mixed data types (numbers, text, empty cells)."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1:D3"
        mock_response = {
            "range": "Sheet1!A1:D3",
            "majorDimension": "ROWS",
            "values": [
                ["Text", "123", "", "True"],  # Mixed types including empty cell
                ["Another", "45.67", "More text"],  # Row with fewer columns
                [],  # Empty row
            ],
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify result preserves all data types and structure
        expected_result = {
            "spreadsheet_id": spreadsheet_id,
            "range_requested": range_a1,
            "range_returned": "Sheet1!A1:D3",
            "major_dimension": "ROWS",
            "values": [
                ["Text", "123", "", "True"],
                ["Another", "45.67", "More text"],
                [],
            ],
        }
        assert result == expected_result

    def test_read_range_single_cell(self, mock_sheets_service):
        """Test reading a single cell."""
        # Test data
        spreadsheet_id = "test_sheet_123"
        range_a1 = "Sheet1!A1"
        mock_response = {
            "range": "Sheet1!A1:A1",
            "majorDimension": "ROWS",
            "values": [["Single Value"]],
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.read_range(spreadsheet_id, range_a1)

        # Verify result
        expected_result = {
            "spreadsheet_id": spreadsheet_id,
            "range_requested": range_a1,
            "range_returned": "Sheet1!A1:A1",
            "major_dimension": "ROWS",
            "values": [["Single Value"]],
        }
        assert result == expected_result
