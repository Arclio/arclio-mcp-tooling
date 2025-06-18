"""
Unit tests for Drive drive_search_files tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.drive import drive_search_files

pytestmark = pytest.mark.anyio


class TestDriveSearchFilesTool:
    """Tests for the drive_search_files tool function."""

    @pytest.fixture
    def mock_drive_service_for_tool(self):
        """Patch DriveService for tool tests."""
        with patch(
            "google_workspace_mcp.tools.drive.DriveService"
        ) as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            yield mock_service_instance

    async def test_tool_search_files_success(self, mock_drive_service_for_tool):
        """Test drive_search_files tool successful search."""
        mock_files = [
            {"id": "file1", "name": "test1.txt", "mimeType": "text/plain"},
            {"id": "file2", "name": "test2.pdf", "mimeType": "application/pdf"},
        ]
        mock_drive_service_for_tool.search_files.return_value = mock_files

        result = await drive_search_files(query="test documents", page_size=5)

        assert result == {"files": mock_files}
        mock_drive_service_for_tool.search_files.assert_called_once_with(
            query="test documents",
            page_size=5,
            shared_drive_id=None,
            include_shared_drives=True,
        )

    async def test_tool_search_files_with_shared_drive(
        self, mock_drive_service_for_tool
    ):
        """Test drive_search_files tool with shared drive."""
        mock_files = [
            {"id": "shared1", "name": "shared_doc.txt", "mimeType": "text/plain"},
        ]
        mock_drive_service_for_tool.search_files.return_value = mock_files

        result = await drive_search_files(
            query="shared documents", page_size=10, shared_drive_id="drive123"
        )

        assert result == {"files": mock_files}
        mock_drive_service_for_tool.search_files.assert_called_once_with(
            query="shared documents",
            page_size=10,
            shared_drive_id="drive123",
            include_shared_drives=True,
        )

    async def test_tool_search_files_exclude_shared_drives(
        self, mock_drive_service_for_tool
    ):
        """Test drive_search_files tool excluding shared drives."""
        mock_files = [
            {"id": "personal1", "name": "personal_doc.txt", "mimeType": "text/plain"},
        ]
        mock_drive_service_for_tool.search_files.return_value = mock_files

        result = await drive_search_files(
            query="personal documents", include_shared_drives=False
        )

        assert result == {"files": mock_files}
        mock_drive_service_for_tool.search_files.assert_called_once_with(
            query="personal documents",
            page_size=10,
            shared_drive_id=None,
            include_shared_drives=False,
        )

    async def test_tool_search_files_empty_results(self, mock_drive_service_for_tool):
        """Test drive_search_files tool with no results."""
        mock_drive_service_for_tool.search_files.return_value = []

        result = await drive_search_files(query="nonexistent")

        assert result == {"files": []}

    async def test_tool_search_files_empty_query(self, mock_drive_service_for_tool):
        """Test drive_search_files tool with empty query."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await drive_search_files(query="")

    async def test_tool_search_files_whitespace_query(
        self, mock_drive_service_for_tool
    ):
        """Test drive_search_files tool with whitespace-only query."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await drive_search_files(query="   ")

    async def test_tool_search_files_service_error(self, mock_drive_service_for_tool):
        """Test drive_search_files tool when service returns an error."""
        error_response = {
            "error": True,
            "message": "API rate limit exceeded",
            "error_type": "rate_limit",
        }
        mock_drive_service_for_tool.search_files.return_value = error_response

        with pytest.raises(Exception, match="Search failed: API rate limit exceeded"):
            await drive_search_files(query="test")

    async def test_tool_search_files_service_unknown_error(
        self, mock_drive_service_for_tool
    ):
        """Test drive_search_files tool when service returns error without message."""
        error_response = {"error": True, "error_type": "unknown"}
        mock_drive_service_for_tool.search_files.return_value = error_response

        with pytest.raises(Exception, match="Search failed: Unknown error"):
            await drive_search_files(query="test")

    async def test_tool_search_files_default_parameters(
        self, mock_drive_service_for_tool
    ):
        """Test drive_search_files tool with default parameters."""
        mock_files = [{"id": "file1", "name": "test.txt"}]
        mock_drive_service_for_tool.search_files.return_value = mock_files

        result = await drive_search_files(query="test")

        # Verify default parameters
        mock_drive_service_for_tool.search_files.assert_called_once_with(
            query="test", page_size=10, shared_drive_id=None, include_shared_drives=True
        )
        assert result == {"files": mock_files}
