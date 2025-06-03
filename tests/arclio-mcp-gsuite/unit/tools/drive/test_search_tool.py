"""
Unit tests for Drive gdrive_search tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.drive import gdrive_search

pytestmark = pytest.mark.anyio


class TestGdriveSearchTool:
    """Tests for the gdrive_search tool function."""

    @pytest.fixture
    def mock_drive_service(self):
        """Patch DriveService for tool tests."""
        with patch("arclio_mcp_gsuite.tools.drive.DriveService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_search_success(self, mock_drive_service):
        """Test gdrive_search successful case."""
        mock_service_response = [
            {"id": "file1", "name": "Test Report Q1.docx"},
            {"id": "file2", "name": "Final Report Q1.pdf"},
        ]
        mock_drive_service.search_files.return_value = mock_service_response

        args = {"query": "name contains 'Report Q1'", "user_id": "user@example.com"}
        result = await gdrive_search(**args)

        mock_drive_service.search_files.assert_called_once_with(
            query="name contains 'Report Q1'",
            page_size=10,  # Check internal default
        )
        assert result == {"count": 2, "files": mock_service_response}

    async def test_search_with_page_size(self, mock_drive_service):
        """Test gdrive_search with custom page size."""
        mock_service_response = [{"id": "file1", "name": "Test Report Q1.docx"}]
        mock_drive_service.search_files.return_value = mock_service_response

        args = {
            "query": "name contains 'Report Q1'",
            "user_id": "user@example.com",
            "page_size": 1,
        }
        result = await gdrive_search(**args)

        mock_drive_service.search_files.assert_called_once_with(query="name contains 'Report Q1'", page_size=1)
        assert result == {"count": 1, "files": mock_service_response}

    async def test_search_no_results(self, mock_drive_service):
        """Test gdrive_search when no files are found."""
        mock_drive_service.search_files.return_value = []

        args = {"query": "gobbledygook", "user_id": "user@example.com"}
        result = await gdrive_search(**args)

        mock_drive_service.search_files.assert_called_once_with(query="gobbledygook", page_size=10)
        assert result == {"message": "No files found matching your query."}

    async def test_search_service_error(self, mock_drive_service):
        """Test gdrive_search when the service call fails."""
        mock_drive_service.search_files.return_value = {
            "error": True,
            "message": "API Error: Invalid query",
        }

        args = {"query": "invalid:query'", "user_id": "user@example.com"}
        with pytest.raises(ValueError, match="API Error: Invalid query"):
            await gdrive_search(**args)

    async def test_search_empty_query(self):
        """Test gdrive_search tool validation for empty query."""
        args = {"query": "", "user_id": "user@example.com"}
        # Tool itself raises ValueError for empty query
        with pytest.raises(
            ValueError,
            match="Search query parameter cannot be empty for gdrive_search",
        ):
            await gdrive_search(**args)
