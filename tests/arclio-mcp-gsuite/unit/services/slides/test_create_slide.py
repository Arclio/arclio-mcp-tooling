"""
Unit tests for the SlidesService.create_slide method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestSlidesCreateSlide:
    """Tests for the SlidesService.create_slide method."""

    # Removed local mock_slides_service fixture

    def test_create_slide_success(self, mock_slides_service):
        """Test successful slide creation."""
        # Test data
        presentation_id = "presentation_123"
        layout = "TITLE_AND_BODY"
        new_slide_id = "new_slide_123"

        # Mock API response
        mock_response = {"replies": [{"createSlide": {"objectId": new_slide_id}}]}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_response)
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_slides_service.create_slide(presentation_id, layout)

        # Verify API call with correct parameters
        mock_slides_service.service.presentations.return_value.batchUpdate.assert_called_once()
        call_args = mock_slides_service.service.presentations.return_value.batchUpdate.call_args
        assert call_args[1]["presentationId"] == presentation_id

        # Verify the request body contains correct layout
        request_body = call_args[1]["body"]
        assert "requests" in request_body
        assert len(request_body["requests"]) == 1
        assert "createSlide" in request_body["requests"][0]
        assert (
            request_body["requests"][0]["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            == layout
        )

        # Verify result has expected fields
        assert result["presentationId"] == presentation_id
        assert result["slideId"] == new_slide_id
        assert result["layout"] == layout

    def test_create_slide_error(self, mock_slides_service):
        """Test slide creation with API error."""
        presentation_id = "invalid_presentation"
        layout = "TITLE_ONLY"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Presentation not found"}}')

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Presentation not found",
            "operation": "create_slide",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.create_slide(presentation_id, layout)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with("create_slide", http_error)
        assert result == expected_error
