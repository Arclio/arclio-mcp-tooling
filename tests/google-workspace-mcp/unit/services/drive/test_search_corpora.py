"""
Tests for the include_shared_drives / corpora behavior of DriveService.search_files.

Ported from the demo branch's drive-search work: folder-aware searches need to
span shared drives (corpora="allDrives"), while the default stays user-only.
"""


class TestSearchCorpora:
    def _last_list_params(self, mock_drive_service):
        _, kwargs = mock_drive_service.service.files.return_value.list.call_args
        return kwargs

    def test_default_is_user_corpora(self, mock_drive_service):
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        mock_drive_service.search_files(query="x", page_size=5)
        assert self._last_list_params(mock_drive_service)["corpora"] == "user"

    def test_include_shared_drives_uses_all_drives(self, mock_drive_service):
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        mock_drive_service.search_files(
            query="x", page_size=5, include_shared_drives=True
        )
        assert self._last_list_params(mock_drive_service)["corpora"] == "allDrives"

    def test_specific_shared_drive_overrides(self, mock_drive_service):
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        mock_drive_service.search_files(
            query="x", page_size=5, shared_drive_id="drive1", include_shared_drives=True
        )
        params = self._last_list_params(mock_drive_service)
        assert params["corpora"] == "drive"
        assert params["driveId"] == "drive1"

    def test_parents_field_requested(self, mock_drive_service):
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        mock_drive_service.search_files(query="x", page_size=5)
        assert "parents" in self._last_list_params(mock_drive_service)["fields"]
