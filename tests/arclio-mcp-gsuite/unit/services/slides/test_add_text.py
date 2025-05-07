"""
Unit tests for the SlidesService.add_text method.
"""

from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestSlidesAddText:
    """Tests for the SlidesService.add_text method."""

    # Removed local mock_slides_service fixture

    def test_add_text_success(self, mock_slides_service):
        """Test successful text addition."""
        # Test data
        presentation_id = "presentation_123"
        slide_id = "slide_123"
        text = "Test text content"
        position = (150, 100)
        size = (350, 100)

        # Mock API response
        mock_response = {
            "replies": [
                {"createShape": {"objectId": "text_obj_123"}},
                {"insertText": {}},
            ]
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_response)
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute = (
            mock_execute
        )

        # Call the method
        result = mock_slides_service.add_text(
            presentation_id, slide_id, text, position=position, size=size
        )

        # Verify API call with correct parameters
        mock_slides_service.service.presentations.return_value.batchUpdate.assert_called_once()
        call_args = mock_slides_service.service.presentations.return_value.batchUpdate.call_args
        assert call_args[1]["presentationId"] == presentation_id

        # Verify the request body contains both createShape and insertText requests
        request_body = call_args[1]["body"]
        assert "requests" in request_body
        assert len(request_body["requests"]) == 2
        assert "createShape" in request_body["requests"][0]
        assert "insertText" in request_body["requests"][1]

        # Verify the createShape request parameters
        create_shape_req = request_body["requests"][0]["createShape"]
        assert create_shape_req["shapeType"] == "TEXT_BOX"
        assert create_shape_req["elementProperties"]["pageObjectId"] == slide_id
        assert create_shape_req["elementProperties"]["transform"]["translateX"] == position[0]
        assert create_shape_req["elementProperties"]["transform"]["translateY"] == position[1]
        assert create_shape_req["elementProperties"]["size"]["width"]["magnitude"] == size[0]
        assert create_shape_req["elementProperties"]["size"]["height"]["magnitude"] == size[1]

        # Verify the insertText request parameters
        insert_text_req = request_body["requests"][1]["insertText"]
        assert insert_text_req["text"] == text
        assert insert_text_req["insertionIndex"] == 0

        # Verify result has expected fields
        assert result["presentationId"] == presentation_id
        assert result["slideId"] == slide_id
        assert result["operation"] == "add_text"
        assert result["result"] == "success"
        assert "elementId" in result

    def test_add_text_error(self, mock_slides_service):
        """Test text addition with API error."""
        presentation_id = "presentation_123"
        slide_id = "invalid_slide"
        text = "Test text"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid slide ID"}}')

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid slide ID",
            "operation": "add_text",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.add_text(presentation_id, slide_id, text)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with("add_text", http_error)
        assert result == expected_error
