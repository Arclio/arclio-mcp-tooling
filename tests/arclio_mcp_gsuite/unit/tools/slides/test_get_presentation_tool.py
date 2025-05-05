"""
Unit tests for Slides get_presentation tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from arclio_mcp_gsuite.tools.slides import get_presentation

pytestmark = pytest.mark.anyio


class TestGetPresentationTool:
    """Tests for the get_presentation tool function."""

    @pytest.fixture
    def mock_slides_service(self):
        """Patch SlidesService for tool tests."""
        with patch(
            "arclio_mcp_gsuite.tools.slides.SlidesService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_get_presentation_success(self, mock_slides_service):
        """Test get_presentation successful case."""
        mock_service_response = {
            "presentationId": "pres123",
            "title": "My Presentation",
            "slides": [{"objectId": "slide1"}],
        }
        mock_slides_service.get_presentation.return_value = mock_service_response

        args = {"presentation_id": "pres123", "user_id": "user@example.com"}
        result = await get_presentation(**args)

        mock_slides_service.get_presentation.assert_called_once_with("pres123")
        assert result == mock_service_response

    async def test_get_presentation_service_error(self, mock_slides_service):
        """Test get_presentation when the service call fails."""
        mock_slides_service.get_presentation.return_value = {
            "error": True,
            "message": "API Error: Presentation not found",
        }

        args = {
            "presentation_id": "notfound456",
            "user_id": "user@example.com",
        }
        with pytest.raises(ValueError, match="API Error: Presentation not found"):
            await get_presentation(**args)

    async def test_get_presentation_empty_id(self):
        """Test tool validation for empty presentation_id."""
        args = {"presentation_id": "", "user_id": "user@example.com"}
        with pytest.raises(ValueError, match="Presentation ID cannot be empty"):
            await get_presentation(**args)
