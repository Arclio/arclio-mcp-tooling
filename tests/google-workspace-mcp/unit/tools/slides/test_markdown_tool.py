"""
Unit tests for the create_presentation_from_markdown tool function.
"""

from unittest.mock import MagicMock, patch

import pytest
from google_workspace_mcp.tools.slides import create_presentation_from_markdown

pytestmark = pytest.mark.anyio  # Apply to all tests in this module


class TestCreatePresentationFromMarkdown:
    """Tests for the create_presentation_from_markdown function."""

    @pytest.fixture
    def mock_slides_service(self):
        """Create a patched SlidesService for tool tests."""
        # Patch the service used *by the tool function*
        with patch("google_workspace_mcp.tools.slides.SlidesService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    async def test_create_presentation_success(self, mock_slides_service):
        """Test create_presentation_from_markdown with successful creation."""
        # Setup mock response (raw service result)
        mock_service_response = {
            "presentationId": "pres123",
            "title": "Test Presentation",
            "slides": [{"objectId": "slide1"}, {"objectId": "slide2"}],
        }
        mock_slides_service.create_presentation_from_markdown.return_value = mock_service_response

        # Define arguments (use 'user_id')
        args = {
            "user_id": "user@example.com",
            "title": "Test Presentation",
            "markdown_content": "# Slide 1\n---\n# Slide 2",
        }

        # Call the function
        result = await create_presentation_from_markdown(**args)

        # Verify service call
        mock_slides_service.create_presentation_from_markdown.assert_called_once_with(
            title="Test Presentation", markdown_content="# Slide 1\n---\n# Slide 2"
        )
        # Verify raw result
        assert result == mock_service_response

    async def test_create_presentation_service_error(self, mock_slides_service):
        """Test create_presentation_from_markdown when the service returns an error."""
        # Setup mock error response
        mock_slides_service.create_presentation_from_markdown.return_value = {
            "error": True,
            "message": "API Error",
        }

        # Define arguments (use 'user_id')
        args = {
            "user_id": "user@example.com",
            "title": "Test Presentation",
            "markdown_content": "# Slide 1",
        }

        # Call the function and assert ValueError
        with pytest.raises(ValueError, match="API Error"):
            await create_presentation_from_markdown(**args)

        # Verify service call
        mock_slides_service.create_presentation_from_markdown.assert_called_once_with(
            title="Test Presentation", markdown_content="# Slide 1"
        )

    async def test_create_presentation_missing_title(self):
        """Test with missing title (validation handled by function)."""
        args = {
            "user_id": "user@example.com",
            "title": "",
            "markdown_content": "# Slide 1",
        }
        with pytest.raises(ValueError, match="Title and Markdown content are required"):
            await create_presentation_from_markdown(**args)

    async def test_create_presentation_missing_markdown(self):
        """Test with missing markdown (validation handled by function)."""
        args = {
            "user_id": "user@example.com",
            "title": "Test Title",
            "markdown_content": "",
        }
        with pytest.raises(ValueError, match="Title and Markdown content are required"):
            await create_presentation_from_markdown(**args)
