"""
Unit tests for Google Sheets tools.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.sheets_tools import (
    sheets_add_sheet,
    sheets_append_rows,
    sheets_clear_range,
    sheets_create_spreadsheet,
    sheets_delete_sheet,
    sheets_read_range,
    sheets_write_range,
)

pytestmark = pytest.mark.anyio


class TestSheetsCreateSpreadsheetTool:
    """Tests for sheets_create_spreadsheet tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_create_spreadsheet_success(self, mock_sheets_service_instance):
        """Test successful sheets_create_spreadsheet tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "title": "Test Spreadsheet",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/test_sheet_123/edit",
        }
        mock_sheets_service_instance.create_spreadsheet.return_value = mock_result

        # Execute the tool
        result = await sheets_create_spreadsheet(title="Test Spreadsheet")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.create_spreadsheet.assert_called_once_with(title="Test Spreadsheet")

    @pytest.mark.asyncio
    async def test_create_spreadsheet_empty_title(self):
        """Test sheets_create_spreadsheet with empty title."""
        with pytest.raises(ValueError, match="Spreadsheet title cannot be empty"):
            await sheets_create_spreadsheet(title="")

    @pytest.mark.asyncio
    async def test_create_spreadsheet_service_error(self, mock_sheets_service_instance):
        """Test sheets_create_spreadsheet with service error."""
        # Mock service to return error
        mock_sheets_service_instance.create_spreadsheet.return_value = {
            "error": True,
            "message": "Permission denied",
        }

        with pytest.raises(ValueError, match="Permission denied"):
            await sheets_create_spreadsheet(title="Test Spreadsheet")

    @pytest.mark.asyncio
    async def test_create_spreadsheet_no_id_returned(self, mock_sheets_service_instance):
        """Test sheets_create_spreadsheet with no spreadsheet_id in result."""
        # Mock service to return result without 'spreadsheet_id' key
        mock_sheets_service_instance.create_spreadsheet.return_value = {
            "title": "Test Spreadsheet"
            # Missing 'spreadsheet_id' key
        }

        with pytest.raises(ValueError, match="Failed to create spreadsheet"):
            await sheets_create_spreadsheet(title="Test Spreadsheet")


class TestSheetsReadRangeTool:
    """Tests for sheets_read_range tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_read_range_success(self, mock_sheets_service_instance):
        """Test successful sheets_read_range tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "range_requested": "Sheet1!A1:B2",
            "range_returned": "Sheet1!A1:B2",
            "major_dimension": "ROWS",
            "values": [["Name", "Score"], ["Alice", 100]],
        }
        mock_sheets_service_instance.read_range.return_value = mock_result

        # Execute the tool
        result = await sheets_read_range(spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:B2")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.read_range.assert_called_once_with(
            spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:B2"
        )

    @pytest.mark.asyncio
    async def test_read_range_empty_spreadsheet_id(self):
        """Test sheets_read_range with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_read_range(spreadsheet_id="", range_a1="Sheet1!A1:B2")

    @pytest.mark.asyncio
    async def test_read_range_empty_range(self):
        """Test sheets_read_range with empty range."""
        with pytest.raises(ValueError, match="Range \\(A1 notation\\) cannot be empty"):
            await sheets_read_range(spreadsheet_id="test_sheet_123", range_a1="")

    @pytest.mark.asyncio
    async def test_read_range_service_error(self, mock_sheets_service_instance):
        """Test sheets_read_range with service error."""
        # Mock service to return error
        mock_sheets_service_instance.read_range.return_value = {
            "error": True,
            "message": "Spreadsheet not found",
        }

        with pytest.raises(ValueError, match="Spreadsheet not found"):
            await sheets_read_range(spreadsheet_id="nonexistent", range_a1="Sheet1!A1:B2")

    @pytest.mark.asyncio
    async def test_read_range_no_values_returned(self, mock_sheets_service_instance):
        """Test sheets_read_range with no values key in result."""
        # Mock service to return result without 'values' key
        mock_sheets_service_instance.read_range.return_value = {
            "spreadsheet_id": "test_sheet_123",
            "range_returned": "Sheet1!A1:B2",
            # Missing 'values' key
        }

        with pytest.raises(ValueError, match="Failed to read range"):
            await sheets_read_range(spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:B2")


class TestSheetsWriteRangeTool:
    """Tests for sheets_write_range tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_write_range_success(self, mock_sheets_service_instance):
        """Test successful sheets_write_range tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "updated_range": "Sheet1!A1:B2",
            "updated_rows": 2,
            "updated_columns": 2,
            "updated_cells": 4,
        }
        mock_sheets_service_instance.write_range.return_value = mock_result

        # Execute the tool
        result = await sheets_write_range(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:B2",
            values=[["Name", "Score"], ["Alice", 100]],
            value_input_option="USER_ENTERED",
        )

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.write_range.assert_called_once_with(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:B2",
            values=[["Name", "Score"], ["Alice", 100]],
            value_input_option="USER_ENTERED",
        )

    @pytest.mark.asyncio
    async def test_write_range_raw_option(self, mock_sheets_service_instance):
        """Test sheets_write_range with RAW value input option."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "updated_range": "Sheet1!A1:C1",
            "updated_cells": 3,
        }
        mock_sheets_service_instance.write_range.return_value = mock_result

        # Execute the tool
        result = await sheets_write_range(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:C1",
            values=[["=SUM(1,2)", "text", 123]],
            value_input_option="RAW",
        )

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.write_range.assert_called_once_with(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:C1",
            values=[["=SUM(1,2)", "text", 123]],
            value_input_option="RAW",
        )

    @pytest.mark.asyncio
    async def test_write_range_empty_spreadsheet_id(self):
        """Test sheets_write_range with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_write_range(spreadsheet_id="", range_a1="Sheet1!A1:B2", values=[["Name", "Score"]])

    @pytest.mark.asyncio
    async def test_write_range_empty_range(self):
        """Test sheets_write_range with empty range."""
        with pytest.raises(ValueError, match="Range \\(A1 notation\\) cannot be empty"):
            await sheets_write_range(spreadsheet_id="test_sheet_123", range_a1="", values=[["Name", "Score"]])

    @pytest.mark.asyncio
    async def test_write_range_invalid_values_format(self):
        """Test sheets_write_range with invalid values format."""
        with pytest.raises(ValueError, match="Values must be a list of lists"):
            await sheets_write_range(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1!A1:B2",
                values=["Name", "Score"],  # Should be list of lists
            )

    @pytest.mark.asyncio
    async def test_write_range_invalid_value_input_option(self):
        """Test sheets_write_range with invalid value_input_option."""
        with pytest.raises(
            ValueError,
            match="value_input_option must be either 'USER_ENTERED' or 'RAW'",
        ):
            await sheets_write_range(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1!A1:B2",
                values=[["Name", "Score"]],
                value_input_option="INVALID",
            )

    @pytest.mark.asyncio
    async def test_write_range_service_error(self, mock_sheets_service_instance):
        """Test sheets_write_range with service error."""
        # Mock service to return error
        mock_sheets_service_instance.write_range.return_value = {
            "error": True,
            "message": "Invalid range",
        }

        with pytest.raises(ValueError, match="Invalid range"):
            await sheets_write_range(
                spreadsheet_id="test_sheet_123",
                range_a1="InvalidSheet!A1:B2",
                values=[["Name", "Score"]],
            )

    @pytest.mark.asyncio
    async def test_write_range_no_updated_range(self, mock_sheets_service_instance):
        """Test sheets_write_range with no updated_range in result."""
        # Mock service to return result without 'updated_range' key
        mock_sheets_service_instance.write_range.return_value = {
            "spreadsheet_id": "test_sheet_123"
            # Missing 'updated_range' key
        }

        with pytest.raises(ValueError, match="Failed to write to range"):
            await sheets_write_range(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1!A1:B2",
                values=[["Name", "Score"]],
            )


class TestSheetsAppendRowsTool:
    """Tests for sheets_append_rows tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_append_rows_success(self, mock_sheets_service_instance):
        """Test successful sheets_append_rows tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "table_range_updated": "Sheet1!A3:B4",
            "updates": {"updatedRange": "Sheet1!A3:B4", "updatedRows": 2},
        }
        mock_sheets_service_instance.append_rows.return_value = mock_result

        # Execute the tool
        result = await sheets_append_rows(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1",
            values=[["Bob", 90], ["Charlie", 85]],
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
        )

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.append_rows.assert_called_once_with(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1",
            values=[["Bob", 90], ["Charlie", 85]],
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
        )

    @pytest.mark.asyncio
    async def test_append_rows_overwrite_option(self, mock_sheets_service_instance):
        """Test sheets_append_rows with OVERWRITE option."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "table_range_updated": "Sheet1!A1:B1",
            "updates": {"updatedRows": 1},
        }
        mock_sheets_service_instance.append_rows.return_value = mock_result

        # Execute the tool
        result = await sheets_append_rows(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:B1",
            values=[["Name", "Score"]],
            insert_data_option="OVERWRITE",
        )

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.append_rows.assert_called_once_with(
            spreadsheet_id="test_sheet_123",
            range_a1="Sheet1!A1:B1",
            values=[["Name", "Score"]],
            value_input_option="USER_ENTERED",  # Default
            insert_data_option="OVERWRITE",
        )

    @pytest.mark.asyncio
    async def test_append_rows_empty_spreadsheet_id(self):
        """Test sheets_append_rows with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_append_rows(spreadsheet_id="", range_a1="Sheet1", values=[["Name", "Score"]])

    @pytest.mark.asyncio
    async def test_append_rows_empty_range(self):
        """Test sheets_append_rows with empty range."""
        with pytest.raises(ValueError, match="Range \\(A1 notation\\) cannot be empty"):
            await sheets_append_rows(spreadsheet_id="test_sheet_123", range_a1="", values=[["Name", "Score"]])

    @pytest.mark.asyncio
    async def test_append_rows_empty_values(self):
        """Test sheets_append_rows with empty values list."""
        with pytest.raises(ValueError, match="Values list cannot be empty"):
            await sheets_append_rows(spreadsheet_id="test_sheet_123", range_a1="Sheet1", values=[])

    @pytest.mark.asyncio
    async def test_append_rows_invalid_values_format(self):
        """Test sheets_append_rows with invalid values format."""
        with pytest.raises(ValueError, match="Values must be a non-empty list of lists"):
            await sheets_append_rows(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1",
                values="invalid",  # Should be list of lists
            )

    @pytest.mark.asyncio
    async def test_append_rows_invalid_value_input_option(self):
        """Test sheets_append_rows with invalid value_input_option."""
        with pytest.raises(
            ValueError,
            match="value_input_option must be either 'USER_ENTERED' or 'RAW'",
        ):
            await sheets_append_rows(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1",
                values=[["Name", "Score"]],
                value_input_option="INVALID",
            )

    @pytest.mark.asyncio
    async def test_append_rows_invalid_insert_data_option(self):
        """Test sheets_append_rows with invalid insert_data_option."""
        with pytest.raises(
            ValueError,
            match="insert_data_option must be either 'INSERT_ROWS' or 'OVERWRITE'",
        ):
            await sheets_append_rows(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1",
                values=[["Name", "Score"]],
                insert_data_option="INVALID",
            )

    @pytest.mark.asyncio
    async def test_append_rows_service_error(self, mock_sheets_service_instance):
        """Test sheets_append_rows with service error."""
        # Mock service to return error
        mock_sheets_service_instance.append_rows.return_value = {
            "error": True,
            "message": "Permission denied",
        }

        with pytest.raises(ValueError, match="Permission denied"):
            await sheets_append_rows(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1",
                values=[["Name", "Score"]],
            )

    @pytest.mark.asyncio
    async def test_append_rows_no_result(self, mock_sheets_service_instance):
        """Test sheets_append_rows with None result."""
        # Mock service to return None
        mock_sheets_service_instance.append_rows.return_value = None

        with pytest.raises(ValueError, match="Failed to append rows"):
            await sheets_append_rows(
                spreadsheet_id="test_sheet_123",
                range_a1="Sheet1",
                values=[["Name", "Score"]],
            )


class TestSheetsClearRangeTool:
    """Tests for sheets_clear_range tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_clear_range_success(self, mock_sheets_service_instance):
        """Test successful sheets_clear_range tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "cleared_range": "Sheet1!A1:C3",
        }
        mock_sheets_service_instance.clear_range.return_value = mock_result

        # Execute the tool
        result = await sheets_clear_range(spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:C3")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.clear_range.assert_called_once_with(
            spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:C3"
        )

    @pytest.mark.asyncio
    async def test_clear_range_entire_sheet(self, mock_sheets_service_instance):
        """Test sheets_clear_range for entire sheet."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "cleared_range": "Sheet1!1:1000",
        }
        mock_sheets_service_instance.clear_range.return_value = mock_result

        # Execute the tool
        result = await sheets_clear_range(spreadsheet_id="test_sheet_123", range_a1="Sheet1")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.clear_range.assert_called_once_with(spreadsheet_id="test_sheet_123", range_a1="Sheet1")

    @pytest.mark.asyncio
    async def test_clear_range_empty_spreadsheet_id(self):
        """Test sheets_clear_range with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_clear_range(spreadsheet_id="", range_a1="Sheet1!A1:C3")

    @pytest.mark.asyncio
    async def test_clear_range_empty_range(self):
        """Test sheets_clear_range with empty range."""
        with pytest.raises(ValueError, match="Range \\(A1 notation\\) cannot be empty"):
            await sheets_clear_range(spreadsheet_id="test_sheet_123", range_a1="")

    @pytest.mark.asyncio
    async def test_clear_range_service_error(self, mock_sheets_service_instance):
        """Test sheets_clear_range with service error."""
        # Mock service to return error
        mock_sheets_service_instance.clear_range.return_value = {
            "error": True,
            "message": "Spreadsheet not found",
        }

        with pytest.raises(ValueError, match="Spreadsheet not found"):
            await sheets_clear_range(spreadsheet_id="nonexistent", range_a1="Sheet1!A1:C3")

    @pytest.mark.asyncio
    async def test_clear_range_no_cleared_range(self, mock_sheets_service_instance):
        """Test sheets_clear_range with no cleared_range in result."""
        # Mock service to return result without 'cleared_range' key
        mock_sheets_service_instance.clear_range.return_value = {
            "spreadsheet_id": "test_sheet_123"
            # Missing 'cleared_range' key
        }

        with pytest.raises(ValueError, match="Failed to clear range"):
            await sheets_clear_range(spreadsheet_id="test_sheet_123", range_a1="Sheet1!A1:C3")


class TestSheetsAddSheetTool:
    """Tests for sheets_add_sheet tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_add_sheet_success(self, mock_sheets_service_instance):
        """Test successful sheets_add_sheet tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "sheet_properties": {
                "sheetId": 123456789,
                "title": "New Sheet",
                "index": 1,
                "sheetType": "GRID",
            },
        }
        mock_sheets_service_instance.add_sheet.return_value = mock_result

        # Execute the tool
        result = await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="New Sheet")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.add_sheet.assert_called_once_with(spreadsheet_id="test_sheet_123", title="New Sheet")

    @pytest.mark.asyncio
    async def test_add_sheet_empty_spreadsheet_id(self):
        """Test sheets_add_sheet with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_add_sheet(spreadsheet_id="", title="New Sheet")

    @pytest.mark.asyncio
    async def test_add_sheet_empty_title(self):
        """Test sheets_add_sheet with empty title."""
        with pytest.raises(ValueError, match="Sheet title cannot be empty"):
            await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="")

    @pytest.mark.asyncio
    async def test_add_sheet_whitespace_title(self):
        """Test sheets_add_sheet with whitespace-only title."""
        with pytest.raises(ValueError, match="Sheet title cannot be empty"):
            await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="   ")

    @pytest.mark.asyncio
    async def test_add_sheet_service_error(self, mock_sheets_service_instance):
        """Test sheets_add_sheet with service error."""
        # Mock service to return error
        mock_sheets_service_instance.add_sheet.return_value = {
            "error": True,
            "message": "Duplicate sheet title",
        }

        with pytest.raises(ValueError, match="Duplicate sheet title"):
            await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="Existing Sheet")

    @pytest.mark.asyncio
    async def test_add_sheet_no_sheet_properties(self, mock_sheets_service_instance):
        """Test sheets_add_sheet with no sheet_properties in result."""
        # Mock service to return result without 'sheet_properties' key
        mock_sheets_service_instance.add_sheet.return_value = {
            "spreadsheet_id": "test_sheet_123"
            # Missing 'sheet_properties' key
        }

        with pytest.raises(ValueError, match="Failed to add sheet"):
            await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="New Sheet")

    @pytest.mark.asyncio
    async def test_add_sheet_none_result(self, mock_sheets_service_instance):
        """Test sheets_add_sheet with None result."""
        # Mock service to return None
        mock_sheets_service_instance.add_sheet.return_value = None

        with pytest.raises(ValueError, match="Failed to add sheet"):
            await sheets_add_sheet(spreadsheet_id="test_sheet_123", title="New Sheet")


class TestSheetsDeleteSheetTool:
    """Tests for sheets_delete_sheet tool."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for tool tests."""
        with patch("google_workspace_mcp.tools.sheets_tools.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_delete_sheet_success(self, mock_sheets_service_instance):
        """Test successful sheets_delete_sheet tool execution."""
        # Mock the service method
        mock_result = {
            "spreadsheet_id": "test_sheet_123",
            "deleted_sheet_id": 123456789,
            "success": True,
        }
        mock_sheets_service_instance.delete_sheet.return_value = mock_result

        # Execute the tool
        result = await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id=123456789)

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.delete_sheet.assert_called_once_with(spreadsheet_id="test_sheet_123", sheet_id=123456789)

    @pytest.mark.asyncio
    async def test_delete_sheet_empty_spreadsheet_id(self):
        """Test sheets_delete_sheet with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID cannot be empty"):
            await sheets_delete_sheet(spreadsheet_id="", sheet_id=123456789)

    @pytest.mark.asyncio
    async def test_delete_sheet_invalid_sheet_id_type(self):
        """Test sheets_delete_sheet with non-integer sheet ID."""
        with pytest.raises(ValueError, match="Sheet ID must be an integer"):
            await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id="invalid")

    @pytest.mark.asyncio
    async def test_delete_sheet_string_sheet_id(self):
        """Test sheets_delete_sheet with string sheet ID."""
        with pytest.raises(ValueError, match="Sheet ID must be an integer"):
            await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id="123")

    @pytest.mark.asyncio
    async def test_delete_sheet_service_error(self, mock_sheets_service_instance):
        """Test sheets_delete_sheet with service error."""
        # Mock service to return error
        mock_sheets_service_instance.delete_sheet.return_value = {
            "error": True,
            "message": "Sheet not found",
        }

        with pytest.raises(ValueError, match="Sheet not found"):
            await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id=999999999)

    @pytest.mark.asyncio
    async def test_delete_sheet_no_success_flag(self, mock_sheets_service_instance):
        """Test sheets_delete_sheet with no success flag in result."""
        # Mock service to return result without 'success' key
        mock_sheets_service_instance.delete_sheet.return_value = {
            "spreadsheet_id": "test_sheet_123",
            "deleted_sheet_id": 123456789,
            # Missing 'success' key
        }

        with pytest.raises(ValueError, match="Failed to delete sheet"):
            await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id=123456789)

    @pytest.mark.asyncio
    async def test_delete_sheet_none_result(self, mock_sheets_service_instance):
        """Test sheets_delete_sheet with None result."""
        # Mock service to return None
        mock_sheets_service_instance.delete_sheet.return_value = None

        with pytest.raises(ValueError, match="Failed to delete sheet"):
            await sheets_delete_sheet(spreadsheet_id="test_sheet_123", sheet_id=123456789)
