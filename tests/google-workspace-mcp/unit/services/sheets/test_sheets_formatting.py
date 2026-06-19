"""
Unit tests for SheetsService formatting methods (format_cells, freeze,
set_column_width, merge_cells) and the A1/hex/grid-range helpers.

These let generation emit a single presentable native Sheet (read by
sheets_read_range downstream) instead of a separate styled .xlsx.
"""

import pytest
from google_workspace_mcp.services.sheets_service import SheetsService


@pytest.fixture
def sheets_service(mock_sheets_service):
    """Alias the shared conftest fixture under this module's name."""
    return mock_sheets_service


def _batch_requests(sheets_service):
    """Return the requests list passed to the last batchUpdate call."""
    _, kwargs = sheets_service.service.spreadsheets.return_value.batchUpdate.call_args
    return kwargs["body"]["requests"]


class TestHelpers:
    def test_col_to_index(self):
        assert SheetsService._col_to_index("A") == 0
        assert SheetsService._col_to_index("Z") == 25
        assert SheetsService._col_to_index("AA") == 26
        assert SheetsService._col_to_index("AB") == 27

    def test_hex_to_color(self):
        assert SheetsService._hex_to_color("#FFFFFF") == {
            "red": 1.0,
            "green": 1.0,
            "blue": 1.0,
        }
        black = SheetsService._hex_to_color("000000")
        assert black == {"red": 0.0, "green": 0.0, "blue": 0.0}

    def test_hex_to_color_rejects_bad_length(self):
        with pytest.raises(ValueError):
            SheetsService._hex_to_color("ABC")

    def test_a1_to_grid_range_full(self):
        grid = SheetsService._a1_to_grid_range(7, "A1:M5")
        assert grid == {
            "sheetId": 7,
            "startRowIndex": 0,
            "startColumnIndex": 0,
            "endRowIndex": 5,
            "endColumnIndex": 13,
        }

    def test_a1_to_grid_range_single_cell(self):
        grid = SheetsService._a1_to_grid_range(0, "B2")
        assert grid == {
            "sheetId": 0,
            "startRowIndex": 1,
            "startColumnIndex": 1,
            "endRowIndex": 2,
            "endColumnIndex": 2,
        }

    def test_a1_to_grid_range_strips_sheet_name(self):
        grid = SheetsService._a1_to_grid_range(3, "Content Calendar!A1:B1")
        assert grid["sheetId"] == 3
        assert grid["startColumnIndex"] == 0
        assert grid["endColumnIndex"] == 2


class TestFormatCells:
    def test_header_style_builds_repeat_cell(self, sheets_service):
        result = sheets_service.format_cells(
            "ss1",
            sheet_id=0,
            range_a1="A5:M5",
            bold=True,
            background_hex="1B3A4B",
            font_hex="FFFFFF",
            wrap=True,
            horizontal_alignment="center",
        )
        assert result["success"] is True
        req = _batch_requests(sheets_service)[0]["repeatCell"]
        fmt = req["cell"]["userEnteredFormat"]
        assert fmt["textFormat"]["bold"] is True
        assert fmt["backgroundColor"]["red"] == pytest.approx(0x1B / 255)
        assert fmt["textFormat"]["foregroundColor"]["red"] == 1.0
        assert fmt["wrapStrategy"] == "WRAP"
        assert fmt["horizontalAlignment"] == "CENTER"
        # mask only mentions the fields we set
        assert "userEnteredFormat.backgroundColor" in req["fields"]
        assert "userEnteredFormat.textFormat.bold" in req["fields"]

    def test_no_attributes_is_no_op_error(self, sheets_service):
        result = sheets_service.format_cells("ss1", sheet_id=0, range_a1="A1:A1")
        assert result["error"] is True
        assert result["error_type"] == "no_op"
        sheets_service.service.spreadsheets.return_value.batchUpdate.assert_not_called()


class TestFreeze:
    def test_freeze_header_row(self, sheets_service):
        result = sheets_service.freeze("ss1", sheet_id=0, rows=5)
        assert result["success"] is True
        req = _batch_requests(sheets_service)[0]["updateSheetProperties"]
        assert req["properties"]["gridProperties"]["frozenRowCount"] == 5
        assert "gridProperties.frozenRowCount" in req["fields"]

    def test_freeze_no_args_is_no_op(self, sheets_service):
        result = sheets_service.freeze("ss1", sheet_id=0)
        assert result["error"] is True


class TestColumnWidth:
    def test_set_width(self, sheets_service):
        result = sheets_service.set_column_width(
            "ss1", sheet_id=0, start_col=6, end_col=7, width=400
        )
        assert result["success"] is True
        req = _batch_requests(sheets_service)[0]["updateDimensionProperties"]
        assert req["range"]["dimension"] == "COLUMNS"
        assert req["range"]["startIndex"] == 6
        assert req["range"]["endIndex"] == 7
        assert req["properties"]["pixelSize"] == 400


class TestMergeCells:
    def test_merge_title_banner(self, sheets_service):
        result = sheets_service.merge_cells("ss1", sheet_id=0, range_a1="A1:M1")
        assert result["success"] is True
        req = _batch_requests(sheets_service)[0]["mergeCells"]
        assert req["mergeType"] == "MERGE_ALL"
        assert req["range"]["endColumnIndex"] == 13
