"""
Unit tests for the SlidesService.create_presentation method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestSlidesCreatePresentation:
    """Tests for the SlidesService.create_presentation method."""

    # Removed local mock_slides_service fixture

    def test_create_presentation_success(self, mock_slides_service):
        """Test successful presentation creation."""
        # Test data
        title = "New Test Presentation"

        # Mock API response
        mock_presentation = {
            "presentationId": "new_presentation_123",
            "title": title,
            "slides": [],
            "revisionId": "initial_revision",
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_presentation)
        mock_slides_service.service.presentations.return_value.create.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_slides_service.create_presentation(title)

        # Verify API call with correct title
        mock_slides_service.service.presentations.return_value.create.assert_called_once_with(
            body={"title": title}
        )

        # Verify result
        assert result == mock_presentation
        assert result["title"] == title
        assert result["presentationId"] == "new_presentation_123"

    def test_create_presentation_error(self, mock_slides_service):
        """Test presentation creation with API error."""
        title = "Failed Presentation"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = "Permission Denied"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Permission denied"}}')

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.create.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 403,
            "message": "Permission denied",
            "operation": "create_presentation",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.create_presentation(title)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with(
            "create_presentation", http_error
        )
        assert result == expected_error
