"""
Unit tests for Slides create_presentation_from_markdown tool.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.slides import create_presentation_from_markdown

pytestmark = pytest.mark.anyio


class TestCreatePresentationFromMarkdown:
    """Tests for the create_presentation_from_markdown tool function."""

    @pytest.fixture
    def mock_slides_service(self):
        """Patch SlidesService for tool tests."""
        with patch("google_workspace_mcp.tools.slides.SlidesService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_create_presentation_from_markdown_success(self, mock_slides_service):
        """Test create_presentation_from_markdown successful case."""
        mock_service_response = {
            "presentationId": "new_pres_123",
            "title": "Test Presentation",
            "slides": [
                {"objectId": "slide1", "pageType": "SLIDE"},
                {"objectId": "slide2", "pageType": "SLIDE"},
            ],
        }
        mock_slides_service.create_presentation_from_markdown.return_value = mock_service_response

        markdown_content = """# First Slide

Content for the first slide.

---

# Second Slide

More content here."""

        args = {
            "title": "Test Presentation",
            "markdown_content": markdown_content,
        }
        result = await create_presentation_from_markdown(**args)

        mock_slides_service.create_presentation_from_markdown.assert_called_once_with(
            title="Test Presentation",
            markdown_content=markdown_content,
        )
        assert result == mock_service_response

    async def test_create_presentation_from_markdown_service_error(self, mock_slides_service):
        """Test create_presentation_from_markdown when the service returns an error."""
        mock_slides_service.create_presentation_from_markdown.return_value = {
            "error": True,
            "message": "API Error: Failed to create presentation",
        }

        args = {
            "title": "Failed Presentation",
            "markdown_content": "# Test",
        }
        with pytest.raises(ValueError, match="API Error: Failed to create presentation"):
            await create_presentation_from_markdown(**args)

    async def test_create_presentation_from_markdown_missing_args(self):
        """Test create_presentation_from_markdown with missing required arguments."""
        # Test missing title
        args = {"title": "", "markdown_content": "# Test"}
        with pytest.raises(ValueError, match="Title and markdown content are required"):
            await create_presentation_from_markdown(**args)

        # Test missing markdown_content
        args = {"title": "Test Title", "markdown_content": ""}
        with pytest.raises(ValueError, match="Title and markdown content are required"):
            await create_presentation_from_markdown(**args)
