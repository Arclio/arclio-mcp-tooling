"""
Unit tests for Slides get_slides tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.slides import get_slides

pytestmark = pytest.mark.anyio


class TestGetSlidesTool:
    """Tests for the get_slides tool function."""

    @pytest.fixture
    def mock_slides_service(self):
        """Patch SlidesService for tool tests."""
        with patch("google_workspace_mcp.tools.slides.SlidesService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_slides_success(self, mock_slides_service):
        """Test get_slides successful case."""
        mock_service_response = [
            {"id": "slide1", "elements": []},
            {"id": "slide2", "elements": []},
        ]
        mock_slides_service.get_slides.return_value = mock_service_response

        args = {"presentation_id": "pres123", "user_id": "user@example.com"}
        result = await get_slides(**args)

        mock_slides_service.get_slides.assert_called_once_with("pres123")
        assert result == {"count": 2, "slides": mock_service_response}

    async def test_get_slides_no_slides(self, mock_slides_service):
        """Test get_slides when the presentation has no slides."""
        mock_slides_service.get_slides.return_value = []

        args = {
            "presentation_id": "empty_pres",
            "user_id": "user@example.com",
        }
        result = await get_slides(**args)

        mock_slides_service.get_slides.assert_called_once_with("empty_pres")
        assert result == {"message": "The presentation has no slides or could not be accessed."}

    async def test_get_slides_service_error(self, mock_slides_service):
        """Test get_slides when the service call fails."""
        mock_slides_service.get_slides.return_value = {
            "error": True,
            "message": "API Error: Cannot access slides",
        }

        args = {
            "presentation_id": "error_pres",
            "user_id": "user@example.com",
        }
        with pytest.raises(ValueError, match="API Error: Cannot access slides"):
            await get_slides(**args)

    async def test_get_slides_empty_id(self):
        """Test tool validation for empty presentation_id."""
        args = {"presentation_id": "", "user_id": "user@example.com"}
        with pytest.raises(ValueError, match="Presentation ID cannot be empty"):
            await get_slides(**args)
