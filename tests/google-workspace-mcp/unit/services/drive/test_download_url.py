"""
Tests for the non-redirecting download_url added to Drive results.

webContentLink (drive.google.com/uc?...&export=download) 303-redirects to a
virus-scan confirmation page for large files, breaking consumers that don't
follow redirects. download_url uses drive.usercontent.google.com/download with
confirm=t, which serves the bytes directly.
"""

from google_workspace_mcp.services.drive import (
    _direct_download_url,
    _with_download_url,
)


class TestDirectDownloadUrl:
    def test_url_shape(self):
        url = _direct_download_url("ABC123")
        assert url == (
            "https://drive.usercontent.google.com/download?id=ABC123"
            "&export=download&confirm=t"
        )

    def test_non_redirecting_host(self):
        # The whole point: NOT the drive.google.com/uc host that 303s.
        url = _direct_download_url("x")
        assert "drive.usercontent.google.com/download" in url
        assert "uc?id" not in url
        assert "confirm=t" in url


class TestWithDownloadUrl:
    def test_binary_file_gets_download_url(self):
        meta = {"id": "fid", "mimeType": "video/mp4"}
        out = _with_download_url(meta)
        assert out["download_url"] == _direct_download_url("fid")

    def test_native_google_file_gets_none(self):
        # Google Docs/Sheets/Slides are not byte-downloadable.
        meta = {"id": "fid", "mimeType": "application/vnd.google-apps.document"}
        out = _with_download_url(meta)
        assert out["download_url"] is None

    def test_missing_id_gets_none(self):
        out = _with_download_url({"mimeType": "video/mp4"})
        assert out["download_url"] is None

    def test_missing_mimetype_treated_as_downloadable(self):
        # No mimeType (e.g. some list responses) -> still build the URL.
        out = _with_download_url({"id": "fid"})
        assert out["download_url"] == _direct_download_url("fid")

    def test_returns_same_dict_mutated(self):
        meta = {"id": "fid", "mimeType": "image/png"}
        assert _with_download_url(meta) is meta


class TestShareFileDownloadUrl:
    def test_share_file_returns_download_url(self, mock_drive_service):
        mock_drive_service.service.permissions.return_value.create.return_value.execute.return_value = {}
        mock_drive_service.service.files.return_value.get.return_value.execute.return_value = {
            "id": "vid1",
            "name": "clip.mp4",
            "mimeType": "video/mp4",
            "webViewLink": "http://view",
            "webContentLink": "https://drive.google.com/uc?id=vid1&export=download",
        }

        result = mock_drive_service.share_file("vid1")

        assert result["shared"] is True
        assert (
            result["download_url"]
            == "https://drive.usercontent.google.com/download?id=vid1"
            "&export=download&confirm=t"
        )
        # webContentLink kept for backward compat.
        assert "webContentLink" in result


class TestSearchDownloadUrl:
    def test_search_results_carry_download_url(self, mock_drive_service):
        mock_drive_service.service.files.return_value.list.return_value.execute.return_value = {
            "files": [
                {"id": "a", "mimeType": "video/mp4"},
                {"id": "b", "mimeType": "application/vnd.google-apps.document"},
            ]
        }
        files = mock_drive_service.search_files(query="x", page_size=5)
        assert files[0]["download_url"] == _direct_download_url("a")
        assert files[1]["download_url"] is None  # native doc
