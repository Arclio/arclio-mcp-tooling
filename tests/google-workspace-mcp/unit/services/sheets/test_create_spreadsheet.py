"""
Unit tests for SheetsService create_spreadsheet method.
"""

from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class TestSheetsCreateSpreadsheet:
    """Tests for SheetsService create_spreadsheet method."""

    def test_create_spreadsheet_success(self, mock_sheets_service):
        """Test successful spreadsheet creation."""
        # Test data
        title = "Test Spreadsheet"
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "properties": {"title": "Test Spreadsheet"},
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/test_sheet_123/edit",
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify API call
        expected_body = {"properties": {"title": title}}
        mock_sheets_service.service.spreadsheets.return_value.create.assert_called_once_with(
            body=expected_body
        )

        # Verify result
        expected_result = {
            "spreadsheet_id": "test_sheet_123",
            "title": "Test Spreadsheet",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/test_sheet_123/edit",
        }
        assert result == expected_result

    def test_create_spreadsheet_empty_title(self, mock_sheets_service):
        """Test creating spreadsheet with empty title still works (API allows it)."""
        # Test data
        title = ""
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            "properties": {"title": ""},
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/test_sheet_123/edit",
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify API call
        expected_body = {"properties": {"title": title}}
        mock_sheets_service.service.spreadsheets.return_value.create.assert_called_once_with(
            body=expected_body
        )

        # Verify result
        expected_result = {
            "spreadsheet_id": "test_sheet_123",
            "title": "",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/test_sheet_123/edit",
        }
        assert result == expected_result

    def test_create_spreadsheet_http_error(self, mock_sheets_service):
        """Test create spreadsheet with HTTP error."""
        # Test data
        title = "Failed Spreadsheet"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Forbidden"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Permission denied"}}'
        )

        # Setup the mock to raise the error
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.side_effect = (
            http_error
        )

        # Mock the handle_api_error method
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "create_spreadsheet",
        }
        mock_sheets_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify error handling
        mock_sheets_service.handle_api_error.assert_called_once_with(
            "create_spreadsheet", http_error
        )
        assert result == expected_error

    def test_create_spreadsheet_unexpected_error(self, mock_sheets_service):
        """Test create spreadsheet with unexpected error."""
        # Test data
        title = "Error Spreadsheet"

        # Setup the mock to raise an unexpected error
        unexpected_error = Exception("Network timeout")
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.side_effect = (
            unexpected_error
        )

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify result contains error
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "unexpected_service_error"
        assert result["message"] == "Network timeout"
        assert result["operation"] == "create_spreadsheet"

    def test_create_spreadsheet_missing_fields_in_response(self, mock_sheets_service):
        """Test create spreadsheet when API response is missing expected fields."""
        # Test data
        title = "Test Spreadsheet"
        mock_response = {}  # Empty response

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify result handles missing fields gracefully
        expected_result = {
            "spreadsheet_id": None,  # Missing from response
            "title": None,  # Missing from response
            "spreadsheet_url": None,  # Missing from response
        }
        assert result == expected_result

    def test_create_spreadsheet_partial_response(self, mock_sheets_service):
        """Test create spreadsheet with partial API response."""
        # Test data
        title = "Test Spreadsheet"
        mock_response = {
            "spreadsheetId": "test_sheet_123",
            # Missing properties and spreadsheetUrl
        }

        # Setup mocks
        mock_sheets_service.service.spreadsheets.return_value.create.return_value.execute.return_value = (
            mock_response
        )

        # Call the method
        result = mock_sheets_service.create_spreadsheet(title)

        # Verify result handles partial response
        expected_result = {
            "spreadsheet_id": "test_sheet_123",
            "title": None,  # Missing properties.title
            "spreadsheet_url": None,  # Missing spreadsheetUrl
        }
        assert result == expected_result
