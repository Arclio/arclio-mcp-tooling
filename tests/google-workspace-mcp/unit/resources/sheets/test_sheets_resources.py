"""
Unit tests for Google Sheets resources.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.resources.sheets_resources import (
    get_specific_sheet_metadata_resource,
    get_spreadsheet_metadata_resource,
)

pytestmark = pytest.mark.anyio


class TestGetSpreadsheetMetadataResource:
    """Tests for get_spreadsheet_metadata_resource."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for resource tests."""
        with patch("google_workspace_mcp.resources.sheets_resources.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_get_spreadsheet_metadata_success(self, mock_sheets_service_instance):
        """Test successful spreadsheet metadata retrieval."""
        # Mock the service method
        mock_result = {
            "spreadsheetId": "test_sheet_123",
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
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = mock_result

        # Execute the resource
        result = await get_spreadsheet_metadata_resource(spreadsheet_id="test_sheet_123")

        # Assertions
        assert result == mock_result
        mock_sheets_service_instance.get_spreadsheet_metadata.assert_called_once_with(spreadsheet_id="test_sheet_123")

    @pytest.mark.asyncio
    async def test_get_spreadsheet_metadata_empty_id(self):
        """Test get_spreadsheet_metadata_resource with empty spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID is required in the URI path"):
            await get_spreadsheet_metadata_resource(spreadsheet_id="")

    @pytest.mark.asyncio
    async def test_get_spreadsheet_metadata_none_id(self):
        """Test get_spreadsheet_metadata_resource with None spreadsheet ID."""
        with pytest.raises(ValueError, match="Spreadsheet ID is required in the URI path"):
            await get_spreadsheet_metadata_resource(spreadsheet_id=None)

    @pytest.mark.asyncio
    async def test_get_spreadsheet_metadata_service_error(self, mock_sheets_service_instance):
        """Test get_spreadsheet_metadata_resource with service error."""
        # Mock service to return error
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = {
            "error": True,
            "message": "Spreadsheet not found",
        }

        with pytest.raises(ValueError, match="Spreadsheet not found"):
            await get_spreadsheet_metadata_resource(spreadsheet_id="nonexistent")

    @pytest.mark.asyncio
    async def test_get_spreadsheet_metadata_none_result(self, mock_sheets_service_instance):
        """Test get_spreadsheet_metadata_resource with None result."""
        # Mock service to return None
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = None

        with pytest.raises(ValueError, match="Could not retrieve metadata for spreadsheet ID"):
            await get_spreadsheet_metadata_resource(spreadsheet_id="test_sheet_123")


class TestGetSpecificSheetMetadataResource:
    """Tests for get_specific_sheet_metadata_resource."""

    @pytest.fixture
    def mock_sheets_service_instance(self):
        """Patch SheetsService for resource tests."""
        with patch("google_workspace_mcp.resources.sheets_resources.SheetsService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_by_id_success(self, mock_sheets_service_instance):
        """Test successful specific sheet metadata retrieval by sheet ID."""
        # Mock the service method
        mock_full_metadata = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1",
                        "index": 0,
                        "sheetType": "GRID",
                        "gridProperties": {"rowCount": 1000, "columnCount": 26},
                    }
                },
                {
                    "properties": {
                        "sheetId": 123456789,
                        "title": "Sheet2",
                        "index": 1,
                        "sheetType": "GRID",
                        "gridProperties": {"rowCount": 1000, "columnCount": 26},
                    }
                },
            ]
        }
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = mock_full_metadata

        # Execute the resource - search by sheet ID
        result = await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="123456789")

        # Assertions
        expected_sheet_properties = mock_full_metadata["sheets"][1]["properties"]
        assert result == expected_sheet_properties
        mock_sheets_service_instance.get_spreadsheet_metadata.assert_called_once_with(
            spreadsheet_id="test_sheet_123",
            fields="sheets(properties(sheetId,title,index,sheetType,gridProperties))",
        )

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_by_title_success(self, mock_sheets_service_instance):
        """Test successful specific sheet metadata retrieval by sheet title."""
        # Mock the service method
        mock_full_metadata = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1",
                        "index": 0,
                        "sheetType": "GRID",
                    }
                },
                {
                    "properties": {
                        "sheetId": 123456789,
                        "title": "Data Sheet",
                        "index": 1,
                        "sheetType": "GRID",
                    }
                },
            ]
        }
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = mock_full_metadata

        # Execute the resource - search by sheet title
        result = await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="Data Sheet")

        # Assertions
        expected_sheet_properties = mock_full_metadata["sheets"][1]["properties"]
        assert result == expected_sheet_properties

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_case_insensitive_title(self, mock_sheets_service_instance):
        """Test specific sheet metadata retrieval with case-insensitive title matching."""
        # Mock the service method
        mock_full_metadata = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Data Sheet",
                        "index": 0,
                        "sheetType": "GRID",
                    }
                }
            ]
        }
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = mock_full_metadata

        # Execute the resource - search by sheet title with different case
        result = await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="data sheet")

        # Assertions
        expected_sheet_properties = mock_full_metadata["sheets"][0]["properties"]
        assert result == expected_sheet_properties

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_empty_spreadsheet_id(self):
        """Test get_specific_sheet_metadata_resource with empty spreadsheet ID."""
        with pytest.raises(
            ValueError,
            match="Spreadsheet ID and sheet identifier \\(name or ID\\) are required",
        ):
            await get_specific_sheet_metadata_resource(spreadsheet_id="", sheet_identifier="Sheet1")

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_empty_sheet_identifier(self):
        """Test get_specific_sheet_metadata_resource with empty sheet identifier."""
        with pytest.raises(
            ValueError,
            match="Spreadsheet ID and sheet identifier \\(name or ID\\) are required",
        ):
            await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="")

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_service_error(self, mock_sheets_service_instance):
        """Test get_specific_sheet_metadata_resource with service error."""
        # Mock service to return error
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = {
            "error": True,
            "message": "Spreadsheet not found",
        }

        with pytest.raises(ValueError, match="Spreadsheet not found"):
            await get_specific_sheet_metadata_resource(spreadsheet_id="nonexistent", sheet_identifier="Sheet1")

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_no_sheets(self, mock_sheets_service_instance):
        """Test get_specific_sheet_metadata_resource with no sheets in metadata."""
        # Mock service to return metadata without sheets
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = {
            "spreadsheetId": "test_sheet_123",
            "properties": {"title": "Empty Spreadsheet"},
            # Missing 'sheets' key
        }

        with pytest.raises(ValueError, match="No sheets found in spreadsheet"):
            await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="Sheet1")

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_sheet_not_found(self, mock_sheets_service_instance):
        """Test get_specific_sheet_metadata_resource with sheet not found."""
        # Mock the service method
        mock_full_metadata = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1",
                        "index": 0,
                        "sheetType": "GRID",
                    }
                }
            ]
        }
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = mock_full_metadata

        with pytest.raises(ValueError, match="Sheet 'NonexistentSheet' not found in spreadsheet"):
            await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="NonexistentSheet")

    @pytest.mark.asyncio
    async def test_get_specific_sheet_metadata_none_result(self, mock_sheets_service_instance):
        """Test get_specific_sheet_metadata_resource with None result from service."""
        # Mock service to return None
        mock_sheets_service_instance.get_spreadsheet_metadata.return_value = None

        with pytest.raises(ValueError, match="No sheets found in spreadsheet"):
            await get_specific_sheet_metadata_resource(spreadsheet_id="test_sheet_123", sheet_identifier="Sheet1")
