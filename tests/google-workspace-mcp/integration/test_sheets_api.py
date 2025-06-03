"""
Integration tests for Google Sheets API functionality.

These tests require valid Google API credentials and will make actual API calls.
They should be run cautiously to avoid unwanted side effects on real accounts.
"""

import os
import uuid
from contextlib import suppress
from datetime import datetime

import pytest
from google_workspace_mcp.services.sheets_service import SheetsService
from googleapiclient.discovery import build

# Skip integration tests if environment flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "0") != "1",
    reason="Integration tests are disabled. Set RUN_INTEGRATION_TESTS=1 to enable.",
)


class TestSheetsIntegration:
    """Integration tests for Google Sheets API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up the SheetsService for each test."""
        # Check if credentials are available
        for var in [
            "GOOGLE_WORKSPACE_CLIENT_ID",
            "GOOGLE_WORKSPACE_CLIENT_SECRET",
            "GOOGLE_WORKSPACE_REFRESH_TOKEN",
        ]:
            if not os.environ.get(var):
                pytest.skip(f"Environment variable {var} not set")

        self.service = SheetsService()

        # Generate a unique identifier for test spreadsheets
        self.test_id = f"test-{uuid.uuid4().hex[:8]}"

    def test_create_spreadsheet_integration(self):
        """Test creating a spreadsheet with the actual API."""
        # Generate unique spreadsheet title
        spreadsheet_title = f"Integration Test Spreadsheet {self.test_id}"

        # Create the spreadsheet
        result = self.service.create_spreadsheet(title=spreadsheet_title)

        # Verify response structure
        assert isinstance(result, dict)
        assert "spreadsheet_id" in result
        assert "title" in result
        assert "spreadsheet_url" in result

        # Verify the spreadsheet was created with correct title
        assert result["title"] == spreadsheet_title
        assert result["spreadsheet_id"] is not None
        assert "docs.google.com/spreadsheets" in result["spreadsheet_url"]

        # Store spreadsheet ID for potential cleanup and further tests
        spreadsheet_id = result["spreadsheet_id"]
        print(f"Created test spreadsheet: {result['spreadsheet_url']}")

        # Note: Unlike Google Docs, Google Sheets doesn't provide a direct delete method via Sheets API.
        # Created spreadsheets will remain in the account unless manually deleted or moved to trash via Drive API.

        return spreadsheet_id

    def test_read_range_empty_spreadsheet_integration(self):
        """Test reading from an empty spreadsheet with the actual API."""
        # First create a spreadsheet to read from
        spreadsheet_title = f"Read Test Spreadsheet {self.test_id}"
        create_result = self.service.create_spreadsheet(title=spreadsheet_title)

        assert isinstance(create_result, dict)
        assert "spreadsheet_id" in create_result
        spreadsheet_id = create_result["spreadsheet_id"]

        # Try to read from an empty range
        read_result = self.service.read_range(
            spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:C3"
        )

        # Verify response structure
        assert isinstance(read_result, dict)
        assert "spreadsheet_id" in read_result
        assert "range_requested" in read_result
        assert "range_returned" in read_result
        assert "major_dimension" in read_result
        assert "values" in read_result

        # Verify the data
        assert read_result["spreadsheet_id"] == spreadsheet_id
        assert read_result["range_requested"] == "Sheet1!A1:C3"
        assert read_result["major_dimension"] == "ROWS"
        assert read_result["values"] == []  # Empty spreadsheet should have no values

    def test_read_range_nonexistent_spreadsheet_integration(self):
        """Test reading from a nonexistent spreadsheet."""
        # Use a clearly fake spreadsheet ID
        fake_spreadsheet_id = "nonexistent_sheet_12345"

        # Attempt to read from it
        result = self.service.read_range(
            spreadsheet_id=fake_spreadsheet_id, range_a1="Sheet1!A1:B2"
        )

        # Should return an error dictionary
        assert isinstance(result, dict)
        assert result.get("error") is True
        assert "operation" in result
        assert result["operation"] == "read_range"

    def test_create_and_read_workflow_integration(self):
        """Test a complete workflow of creating a spreadsheet and reading from it."""
        # Create a spreadsheet
        spreadsheet_title = f"Workflow Test Spreadsheet {self.test_id}"
        create_result = self.service.create_spreadsheet(title=spreadsheet_title)
        spreadsheet_id = create_result["spreadsheet_id"]

        # Note: Writing data to the spreadsheet would require additional API calls
        # For now, we'll just test reading from the empty spreadsheet

        # Read from different ranges
        ranges_to_test = [
            "A1:B2",  # Simple range
            "Sheet1!A1:C5",  # Full sheet notation
            "A1",  # Single cell
        ]

        for range_a1 in ranges_to_test:
            read_result = self.service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1=range_a1
            )

            # Each read should succeed (even if empty)
            assert isinstance(read_result, dict)
            assert "values" in read_result
            assert read_result.get("error") is not True
            assert read_result["spreadsheet_id"] == spreadsheet_id
            assert read_result["range_requested"] == range_a1

        print(
            f"Workflow completed successfully. Spreadsheet link: {create_result['spreadsheet_url']}"
        )

    def test_read_range_invalid_range_integration(self):
        """Test reading with an invalid range notation."""
        # First create a valid spreadsheet
        spreadsheet_title = f"Invalid Range Test Spreadsheet {self.test_id}"
        create_result = self.service.create_spreadsheet(title=spreadsheet_title)
        spreadsheet_id = create_result["spreadsheet_id"]

        # Try to read with an invalid range
        invalid_range = "InvalidSheet!A1:B2"
        result = self.service.read_range(
            spreadsheet_id=spreadsheet_id, range_a1=invalid_range
        )

        # Should return an error dictionary
        assert isinstance(result, dict)
        assert result.get("error") is True
        assert "operation" in result
        assert result["operation"] == "read_range"

    def test_create_spreadsheet_empty_title_integration(self):
        """Test creating a spreadsheet with empty title (should still work)."""
        # Create spreadsheet with empty title - Google Sheets API allows this
        result = self.service.create_spreadsheet(title="")

        # Verify it still works
        assert isinstance(result, dict)
        assert "spreadsheet_id" in result
        assert result["spreadsheet_id"] is not None
        assert result["title"] == ""  # Empty title should be preserved

        print(f"Created spreadsheet with empty title: {result['spreadsheet_url']}")

    def test_read_range_different_notations_integration(self):
        """Test reading ranges with different A1 notation formats."""
        # Create a spreadsheet
        spreadsheet_title = f"Range Notation Test Spreadsheet {self.test_id}"
        create_result = self.service.create_spreadsheet(title=spreadsheet_title)
        spreadsheet_id = create_result["spreadsheet_id"]

        # Test different valid A1 notations
        valid_ranges = [
            "A1:B2",
            "Sheet1!A1:B2",
            "A1",
            "Sheet1!A1",
            "A:A",  # Entire column
            "1:1",  # Entire row
        ]

        for range_a1 in valid_ranges:
            result = self.service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1=range_a1
            )

            # Each should succeed
            assert isinstance(result, dict)
            assert result.get("error") is not True
            assert "values" in result
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["range_requested"] == range_a1

            print(
                f"Successfully read range '{range_a1}', returned range: '{result.get('range_returned')}'"
            )

        print(
            f"All range notations tested successfully for: {create_result['spreadsheet_url']}"
        )

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_read_range_integration(self, sheets_service):
        """Integration test for read_range method."""
        # First create a spreadsheet for testing
        title = f"Test Read Range - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # Write some test data first using Google Sheets API directly
            test_values = [
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "San Francisco"],
            ]

            # Use the service directly to write data (bypassing our write_range for this test)
            sheets_service.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1:C3",
                valueInputOption="USER_ENTERED",
                body={"values": test_values},
            ).execute()

            # Now test reading the data
            result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:C3"
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["values"] == test_values
            assert result["range_returned"] == "Sheet1!A1:C3"

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                sheets_service.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={"requests": [{"deleteSheet": {"sheetId": 0}}]},
                ).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_write_range_integration(self, sheets_service):
        """Integration test for write_range method."""
        # Create a spreadsheet for testing
        title = f"Test Write Range - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # Test data to write
            test_values = [
                ["Product", "Price", "Stock"],
                ["Laptop", 999.99, 50],
                ["Mouse", 25.50, 100],
                ["Keyboard", 75.00, 30],
            ]

            # Test writing data
            result = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!A1:C4",
                values=test_values,
                value_input_option="USER_ENTERED",
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["updated_range"] == "Sheet1!A1:C4"
            assert result["updated_cells"] == 12
            assert result["updated_rows"] == 4
            assert result["updated_columns"] == 3

            # Verify the data was written correctly by reading it back
            read_result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:C4"
            )

            # Convert numbers back for comparison since they come back as strings
            expected_values = [
                ["Product", "Price", "Stock"],
                ["Laptop", "999.99", "50"],
                ["Mouse", "25.5", "100"],
                ["Keyboard", "75", "30"],
            ]

            assert read_result["values"] == expected_values

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_append_rows_integration(self, sheets_service):
        """Integration test for append_rows method."""
        # Create a spreadsheet for testing
        title = f"Test Append Rows - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # First write some initial data
            initial_values = [["Name", "Score"], ["Alice", 100], ["Bob", 90]]

            write_result = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!A1:B3",
                values=initial_values,
            )
            assert write_result is not None

            # Now append more rows
            append_values = [["Charlie", 85], ["Diana", 95]]

            result = sheets_service.append_rows(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1",
                values=append_values,
                value_input_option="USER_ENTERED",
                insert_data_option="INSERT_ROWS",
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["table_range_updated"] is not None
            assert result["updates"] is not None

            # Verify the data was appended correctly by reading the entire range
            read_result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:B5"
            )

            expected_values = [
                ["Name", "Score"],
                ["Alice", "100"],
                ["Bob", "90"],
                ["Charlie", "85"],
                ["Diana", "95"],
            ]

            assert read_result["values"] == expected_values

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_clear_range_integration(self, sheets_service):
        """Integration test for clear_range method."""
        # Create a spreadsheet for testing
        title = f"Test Clear Range - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # First write some test data
            test_values = [
                ["Item", "Quantity", "Price"],
                ["Apple", 10, 1.50],
                ["Banana", 20, 0.75],
                ["Orange", 15, 2.00],
            ]

            write_result = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!A1:C4",
                values=test_values,
            )
            assert write_result is not None

            # Verify data was written
            read_result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:C4"
            )
            assert len(read_result["values"]) == 4

            # Now clear a portion of the data
            result = sheets_service.clear_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!B2:C4",  # Clear quantity and price for data rows
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["cleared_range"] == "Sheet1!B2:C4"

            # Verify the data was cleared correctly by reading it back
            read_result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:C4"
            )

            # Should have headers and first column intact, but B2:C4 cleared
            expected_values = [
                ["Item", "Quantity", "Price"],
                ["Apple"],  # Row shortened because B2:C2 was cleared
                ["Banana"],  # Row shortened because B3:C3 was cleared
                ["Orange"],  # Row shortened because B4:C4 was cleared
            ]

            assert read_result["values"] == expected_values

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_write_range_raw_vs_user_entered_integration(self, sheets_service):
        """Integration test comparing RAW vs USER_ENTERED value input options."""
        # Create a spreadsheet for testing
        title = f"Test Raw vs User Entered - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # Test data with formulas
            test_values_with_formula = [
                ["Formula", "Value"],
                ["=SUM(1,2)", "3"],
                ["=10*5", "50"],
            ]

            # Test with USER_ENTERED (formulas should be evaluated)
            result_user_entered = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!A1:B3",
                values=test_values_with_formula,
                value_input_option="USER_ENTERED",
            )
            assert result_user_entered is not None

            # Read back to see if formulas were evaluated
            read_result_user = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!A1:B3"
            )

            # With USER_ENTERED, formulas should be evaluated
            assert read_result_user["values"][1][0] == "3"  # =SUM(1,2) should become 3
            assert read_result_user["values"][2][0] == "50"  # =10*5 should become 50

            # Now test with RAW (formulas should be literal text)
            result_raw = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id,
                range_a1="Sheet1!D1:E3",
                values=test_values_with_formula,
                value_input_option="RAW",
            )
            assert result_raw is not None

            # Read back to see if formulas stayed as text
            read_result_raw = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Sheet1!D1:E3"
            )

            # With RAW, formulas should stay as text
            assert (
                read_result_raw["values"][1][0] == "=SUM(1,2)"
            )  # Should stay as formula text
            assert (
                read_result_raw["values"][2][0] == "=10*5"
            )  # Should stay as formula text

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_add_sheet_integration(self, sheets_service):
        """Integration test for add_sheet method."""
        # Create a spreadsheet for testing
        title = f"Test Add Sheet - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # Add a new sheet
            sheet_title = "New Test Sheet"
            result = sheets_service.add_sheet(
                spreadsheet_id=spreadsheet_id, title=sheet_title
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["sheet_properties"] is not None
            assert result["sheet_properties"]["title"] == sheet_title
            assert "sheetId" in result["sheet_properties"]
            assert "index" in result["sheet_properties"]

            # Verify the sheet was actually added by getting metadata
            metadata_result = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            assert metadata_result is not None
            assert len(metadata_result["sheets"]) == 2  # Original + new sheet

            # Find our new sheet in the metadata
            new_sheet_found = False
            for sheet in metadata_result["sheets"]:
                if sheet["properties"]["title"] == sheet_title:
                    new_sheet_found = True
                    assert (
                        sheet["properties"]["sheetId"]
                        == result["sheet_properties"]["sheetId"]
                    )
                    break

            assert (
                new_sheet_found
            ), f"New sheet '{sheet_title}' not found in spreadsheet metadata"

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_delete_sheet_integration(self, sheets_service):
        """Integration test for delete_sheet method."""
        # Create a spreadsheet for testing
        title = f"Test Delete Sheet - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # First add a sheet to delete
            sheet_title = "Sheet to Delete"
            add_result = sheets_service.add_sheet(
                spreadsheet_id=spreadsheet_id, title=sheet_title
            )
            assert add_result is not None
            sheet_id = add_result["sheet_properties"]["sheetId"]

            # Verify we now have 2 sheets
            metadata_before = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            assert len(metadata_before["sheets"]) == 2

            # Delete the sheet
            result = sheets_service.delete_sheet(
                spreadsheet_id=spreadsheet_id, sheet_id=sheet_id
            )

            assert result is not None
            assert result["spreadsheet_id"] == spreadsheet_id
            assert result["deleted_sheet_id"] == sheet_id
            assert result["success"] is True

            # Verify the sheet was actually deleted by getting metadata
            metadata_after = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            assert metadata_after is not None
            assert len(metadata_after["sheets"]) == 1  # Back to original sheet only

            # Verify the deleted sheet is not in the metadata
            for sheet in metadata_after["sheets"]:
                assert (
                    sheet["properties"]["sheetId"] != sheet_id
                ), "Deleted sheet still found in metadata"

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_get_spreadsheet_metadata_integration(self, sheets_service):
        """Integration test for get_spreadsheet_metadata method."""
        # Create a spreadsheet for testing
        title = f"Test Metadata - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # Get metadata with default fields
            result = sheets_service.get_spreadsheet_metadata(spreadsheet_id)

            assert result is not None
            assert result["spreadsheetId"] == spreadsheet_id
            assert "properties" in result
            assert result["properties"]["title"] == title
            assert "sheets" in result
            assert len(result["sheets"]) == 1  # New spreadsheet has one default sheet

            # Verify sheet properties
            default_sheet = result["sheets"][0]["properties"]
            assert "sheetId" in default_sheet
            assert "title" in default_sheet
            assert "index" in default_sheet
            assert "sheetType" in default_sheet
            assert default_sheet["title"] == "Sheet1"  # Default sheet name
            assert default_sheet["index"] == 0
            assert default_sheet["sheetType"] == "GRID"

            # Test with custom fields
            custom_fields = "properties.title,sheets.properties.title"
            result_custom = sheets_service.get_spreadsheet_metadata(
                spreadsheet_id, fields=custom_fields
            )

            assert result_custom is not None
            assert "properties" in result_custom
            assert result_custom["properties"]["title"] == title
            assert "sheets" in result_custom
            assert "title" in result_custom["sheets"][0]["properties"]
            # Should not have other fields like sheetId when using custom fields
            assert (
                "spreadsheetId" not in result_custom
            )  # Not requested in custom fields

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()

    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests not enabled"
    )
    def test_sheet_management_workflow_integration(self, sheets_service):
        """Integration test for complete sheet management workflow."""
        # Create a spreadsheet for testing
        title = f"Test Sheet Management - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        create_result = sheets_service.create_spreadsheet(title=title)

        assert create_result is not None
        assert create_result.get("spreadsheet_id") is not None
        spreadsheet_id = create_result["spreadsheet_id"]

        try:
            # 1. Get initial metadata
            initial_metadata = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            assert len(initial_metadata["sheets"]) == 1
            initial_metadata["sheets"][0]["properties"]["sheetId"]

            # 2. Add multiple sheets
            sheet_names = ["Data", "Analysis", "Summary"]
            added_sheet_ids = []

            for sheet_name in sheet_names:
                add_result = sheets_service.add_sheet(
                    spreadsheet_id=spreadsheet_id, title=sheet_name
                )
                assert add_result is not None
                added_sheet_ids.append(add_result["sheet_properties"]["sheetId"])

            # 3. Verify all sheets were added
            metadata_after_adds = sheets_service.get_spreadsheet_metadata(
                spreadsheet_id
            )
            assert len(metadata_after_adds["sheets"]) == 4  # Original + 3 new

            # Verify all sheet names are present
            sheet_titles = [
                sheet["properties"]["title"] for sheet in metadata_after_adds["sheets"]
            ]
            assert "Sheet1" in sheet_titles  # Original sheet
            for sheet_name in sheet_names:
                assert sheet_name in sheet_titles

            # 4. Delete one of the added sheets
            sheet_to_delete_id = added_sheet_ids[1]  # Delete "Analysis" sheet
            delete_result = sheets_service.delete_sheet(
                spreadsheet_id=spreadsheet_id, sheet_id=sheet_to_delete_id
            )
            assert delete_result is not None
            assert delete_result["success"] is True

            # 5. Verify the sheet was deleted
            final_metadata = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            assert len(final_metadata["sheets"]) == 3  # Original + 2 remaining

            final_sheet_titles = [
                sheet["properties"]["title"] for sheet in final_metadata["sheets"]
            ]
            assert "Sheet1" in final_sheet_titles
            assert "Data" in final_sheet_titles
            assert "Summary" in final_sheet_titles
            assert "Analysis" not in final_sheet_titles  # Should be deleted

            # 6. Write data to one of the new sheets
            test_data = [["Name", "Value"], ["Test", 123]]
            write_result = sheets_service.write_range(
                spreadsheet_id=spreadsheet_id, range_a1="Data!A1:B2", values=test_data
            )
            assert write_result is not None

            # 7. Read back the data to verify it worked
            read_result = sheets_service.read_range(
                spreadsheet_id=spreadsheet_id, range_a1="Data!A1:B2"
            )
            assert read_result is not None
            assert read_result["values"] == [["Name", "Value"], ["Test", "123"]]

        finally:
            # Clean up: delete the test spreadsheet
            with suppress(Exception):
                drive_service = build(
                    "drive", "v3", credentials=sheets_service.service._http.credentials
                )
                drive_service.files().delete(fileId=spreadsheet_id).execute()
