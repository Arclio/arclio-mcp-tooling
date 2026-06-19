"""
Unit tests for reading uploaded .xlsx workbooks via DriveService.

An uploaded .xlsx is not a native Google Sheet (so it has no export path) and is
not text, so without dedicated handling it falls through to an unusable base64
dump. These tests cover the openpyxl-based CSV extraction and the routing in
_download_regular_file.
"""

import io

import pytest
from google_workspace_mcp.services.drive import XLSX_MIME_TYPE, DriveService
from openpyxl import Workbook


def _make_xlsx(sheets: dict[str, list[list]]) -> bytes:
    """Build an in-memory .xlsx from {sheet_name: [[row], ...]}."""
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestExtractXlsxText:
    def test_single_sheet_has_no_header(self):
        content = _make_xlsx({"Data": [["a", "b"], ["1", "2"]]})
        out = DriveService._extract_xlsx_text(content, "one.xlsx")
        assert out == "a,b\n1,2"

    def test_multi_sheet_is_labeled(self):
        content = _make_xlsx(
            {
                "Revenue": [["Month", "Amount"], ["Jan", 1000]],
                "Costs": [["Item", "Cost"], ["Hosting", 42.5]],
            }
        )
        out = DriveService._extract_xlsx_text(content, "book.xlsx")
        assert "# Sheet: Revenue" in out
        assert "Month,Amount\nJan,1000" in out
        assert "# Sheet: Costs" in out
        assert "Hosting,42.5" in out

    def test_none_cells_become_empty(self):
        content = _make_xlsx({"S": [["a", None, "c"]]})
        out = DriveService._extract_xlsx_text(content, "gaps.xlsx")
        assert out == "a,,c"

    def test_invalid_bytes_return_none(self):
        assert DriveService._extract_xlsx_text(b"not a zip", "bad.xlsx") is None


class TestDownloadRegularFileXlsxRouting:
    def test_xlsx_routes_to_csv(self, mock_drive_service, monkeypatch):
        content = _make_xlsx({"Data": [["x"], ["1"]]})
        monkeypatch.setattr(
            mock_drive_service, "_download_content", lambda request: content
        )
        result = mock_drive_service._download_regular_file(
            "fid", "data.xlsx", XLSX_MIME_TYPE
        )
        assert result["encoding"] == "utf-8"
        assert result["mimeType"] == "text/csv"
        assert result["sourceMimeType"] == XLSX_MIME_TYPE
        assert result["content"] == "x\n1"

    def test_xlsx_falls_back_to_base64_when_unparseable(
        self, mock_drive_service, monkeypatch
    ):
        monkeypatch.setattr(
            mock_drive_service, "_download_content", lambda request: b"corrupt"
        )
        result = mock_drive_service._download_regular_file(
            "fid", "bad.xlsx", XLSX_MIME_TYPE
        )
        assert result["encoding"] == "base64"
        assert result["mimeType"] == XLSX_MIME_TYPE
