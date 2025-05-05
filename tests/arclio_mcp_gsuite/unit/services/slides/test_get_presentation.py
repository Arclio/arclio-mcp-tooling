"""
Unit tests for the SlidesService.get_presentation method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestSlidesGetPresentation:
    """Tests for the SlidesService.get_presentation method."""

    # Removed local mock_slides_service fixture

    def test_get_presentation_success(self, mock_slides_service):
        """Test successful presentation retrieval."""
        # Mock data for the API response
        presentation_id = "test_presentation_123"
        mock_presentation = {
            "presentationId": presentation_id,
            "title": "Test Presentation",
            "slides": [
                {"objectId": "slide1", "pageElements": []},
                {"objectId": "slide2", "pageElements": []},
            ],
            "revisionId": "revision123",
            "lastModifiedTime": "2023-01-01T12:00:00Z",
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_presentation)
        mock_slides_service.service.presentations.return_value.get.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_slides_service.get_presentation(presentation_id)

        # Verify API call
        mock_slides_service.service.presentations.return_value.get.assert_called_once_with(
            presentationId=presentation_id
        )

        # Verify result
        assert result == mock_presentation
        assert result["presentationId"] == presentation_id
        assert result["title"] == "Test Presentation"
        assert len(result["slides"]) == 2

    def test_get_presentation_error(self, mock_slides_service):
        """Test presentation retrieval with API error."""
        presentation_id = "nonexistent_id"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(
            mock_resp, b'{"error": {"message": "Presentation not found"}}'
        )

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.get.return_value.execute.side_effect = (
            http_error
        )

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Presentation not found",
            "operation": "get_presentation",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.get_presentation(presentation_id)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with(
            "get_presentation", http_error
        )
        assert result == expected_error
