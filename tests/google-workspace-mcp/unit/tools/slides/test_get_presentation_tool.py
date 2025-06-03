"""
Unit tests for Slides get_presentation tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.slides import get_presentation

pytestmark = pytest.mark.anyio


class TestGetPresentationTool:
    """Tests for the get_presentation tool function."""

    @pytest.fixture
    def mock_slides_service(self):
        """Patch SlidesService for tool tests."""
        with patch("google_workspace_mcp.tools.slides.SlidesService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_presentation_success(self, mock_slides_service):
        """Test get_presentation successful case."""
        mock_service_response = {
            "presentationId": "pres123",
            "title": "Test Presentation",
            "slides": [
                {"objectId": "slide1", "pageType": "SLIDE"},
                {"objectId": "slide2", "pageType": "SLIDE"},
            ],
        }
        mock_slides_service.get_presentation.return_value = mock_service_response

        args = {"presentation_id": "pres123"}
        result = await get_presentation(**args)

        mock_slides_service.get_presentation.assert_called_once_with(presentation_id="pres123")
        assert result == mock_service_response

    async def test_get_presentation_service_error(self, mock_slides_service):
        """Test get_presentation when the service returns an error."""
        mock_slides_service.get_presentation.return_value = {
            "error": True,
            "message": "API Error: Presentation not found",
        }

        args = {"presentation_id": "nonexistent"}
        with pytest.raises(ValueError, match="API Error: Presentation not found"):
            await get_presentation(**args)

    async def test_get_presentation_missing_id(self):
        """Test get_presentation with missing presentation_id."""
        args = {"presentation_id": ""}
        with pytest.raises(ValueError, match="Presentation ID is required"):
            await get_presentation(**args)
