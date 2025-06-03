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
            {"objectId": "slide1", "pageType": "SLIDE"},
            {"objectId": "slide2", "pageType": "SLIDE"},
        ]
        mock_slides_service.get_slides.return_value = mock_service_response

        args = {"presentation_id": "pres123"}
        result = await get_slides(**args)

        mock_slides_service.get_slides.assert_called_once_with(presentation_id="pres123")
        assert result == {"count": 2, "slides": mock_service_response}

    async def test_get_slides_no_results(self, mock_slides_service):
        """Test get_slides when no slides are found."""
        mock_slides_service.get_slides.return_value = []

        args = {"presentation_id": "empty_pres"}
        result = await get_slides(**args)

        mock_slides_service.get_slides.assert_called_once_with(presentation_id="empty_pres")
        assert result == {"message": "No slides found in this presentation."}

    async def test_get_slides_service_error(self, mock_slides_service):
        """Test get_slides when the service returns an error."""
        mock_slides_service.get_slides.return_value = {
            "error": True,
            "message": "API Error: Presentation access denied",
        }

        args = {"presentation_id": "access_denied"}
        with pytest.raises(ValueError, match="API Error: Presentation access denied"):
            await get_slides(**args)

    async def test_get_slides_missing_id(self):
        """Test get_slides with missing presentation_id."""
        args = {"presentation_id": ""}
        with pytest.raises(ValueError, match="Presentation ID is required"):
            await get_slides(**args)
