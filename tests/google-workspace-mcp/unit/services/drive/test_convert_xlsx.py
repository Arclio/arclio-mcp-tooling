"""
Unit tests for DriveService.convert_xlsx_to_google_sheet.

Converting an uploaded .xlsx into a native Google Sheet is done server-side via
files().copy() with the native Sheet target mimeType, so the original .xlsx is
left untouched and the new Sheet is fully editable.
"""

from google_workspace_mcp.services.drive import (
    NATIVE_SHEET_MIME_TYPE,
    XLSX_MIME_TYPE,
    DriveService,
)


def _mock_get(mock_drive_service):
    return mock_drive_service.service.files.return_value.get.return_value.execute


def _mock_copy(mock_drive_service):
    return mock_drive_service.service.files.return_value.copy.return_value.execute


class TestConvertXlsxToGoogleSheet:
    def test_converts_and_defaults_name_stripping_extension(
        self, mock_drive_service
    ):
        _mock_get(mock_drive_service).return_value = {
            "id": "src1",
            "name": "Budget.xlsx",
            "mimeType": XLSX_MIME_TYPE,
            "parents": ["folderA"],
        }
        _mock_copy(mock_drive_service).return_value = {
            "id": "sheet1",
            "name": "Budget",
            "mimeType": NATIVE_SHEET_MIME_TYPE,
            "webViewLink": "http://x",
        }

        result = mock_drive_service.convert_xlsx_to_google_sheet("src1")

        # copy() invoked with the native Sheet target mimeType and stripped name
        _, kwargs = mock_drive_service.service.files.return_value.copy.call_args
        assert kwargs["fileId"] == "src1"
        assert kwargs["body"]["mimeType"] == NATIVE_SHEET_MIME_TYPE
        assert kwargs["body"]["name"] == "Budget"
        assert kwargs["supportsAllDrives"] is True
        assert result["id"] == "sheet1"

    def test_honors_explicit_name_and_parent(self, mock_drive_service):
        _mock_get(mock_drive_service).return_value = {
            "id": "src1",
            "name": "Budget.xlsx",
            "mimeType": XLSX_MIME_TYPE,
        }
        _mock_copy(mock_drive_service).return_value = {"id": "sheet1"}

        mock_drive_service.convert_xlsx_to_google_sheet(
            "src1", new_name="Q3 Budget", parent_folder_id="folderB"
        )

        _, kwargs = mock_drive_service.service.files.return_value.copy.call_args
        assert kwargs["body"]["name"] == "Q3 Budget"
        assert kwargs["body"]["parents"] == ["folderB"]

    def test_rejects_non_xlsx_source(self, mock_drive_service):
        _mock_get(mock_drive_service).return_value = {
            "id": "src1",
            "name": "notes.pdf",
            "mimeType": "application/pdf",
        }

        result = mock_drive_service.convert_xlsx_to_google_sheet("src1")

        assert result["error"] is True
        assert result["error_type"] == "unsupported_type"
        mock_drive_service.service.files.return_value.copy.assert_not_called()

    def test_empty_source_id_errors(self, mock_drive_service):
        result = mock_drive_service.convert_xlsx_to_google_sheet("")
        assert result["error"] is True


class TestMoveFile:
    def test_move_removes_existing_parents(self, mock_drive_service):
        _mock_get(mock_drive_service).return_value = {"parents": ["root", "old"]}
        mock_drive_service.service.files.return_value.update.return_value.execute.return_value = {
            "id": "f1",
            "name": "deliverable.xlsx",
            "parents": ["dest"],
        }

        result = mock_drive_service.move_file("f1", "dest")

        _, kwargs = mock_drive_service.service.files.return_value.update.call_args
        assert kwargs["addParents"] == "dest"
        assert kwargs["removeParents"] == "root,old"
        assert result["parents"] == ["dest"]

    def test_move_requires_both_ids(self, mock_drive_service):
        assert mock_drive_service.move_file("", "dest")["error"] is True
        assert mock_drive_service.move_file("f1", "")["error"] is True
