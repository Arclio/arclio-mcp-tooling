"""
Tests for SlidesService.get_slides and delete_slide methods.
"""

# Explicitly import the service, although mocks might override it
from unittest.mock import MagicMock  # , patch

# import pytest # Removed unused import
from googleapiclient.errors import HttpError


class TestSlidesGetAndDeleteSlides:
    """Tests for SlidesService.get_slides and delete_slide methods."""

    # Removed local mock_slides_service fixture

    def test_get_slides_success(self, mock_slides_service):
        """Test successful slides retrieval."""
        # Test data
        presentation_id = "presentation_123"

        # Mock API response for get presentation
        mock_presentation = {
            "presentationId": presentation_id,
            "slides": [
                {
                    "objectId": "slide1",
                    "pageElements": [
                        {
                            "objectId": "text1",
                            "shape": {
                                "shapeType": "TEXT_BOX",
                                "text": {"textElements": [{"textRun": {"content": "Title text"}}]},
                            },
                        },
                        {
                            "objectId": "image1",
                            "image": {"contentUrl": "https://example.com/image.jpg"},
                        },
                    ],
                },
                {"objectId": "slide2", "pageElements": []},
            ],
        }

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_presentation)
        mock_slides_service.service.presentations.return_value.get.return_value.execute = mock_execute

        # Call the method
        result = mock_slides_service.get_slides(presentation_id)

        # Verify API call
        mock_slides_service.service.presentations.return_value.get.assert_called_once_with(presentationId=presentation_id)

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 2

        # Check first slide with elements
        assert result[0]["id"] == "slide1"
        assert len(result[0]["elements"]) == 2
        assert result[0]["elements"][0]["type"] == "text"
        assert result[0]["elements"][0]["content"] == "Title text"
        assert result[0]["elements"][1]["type"] == "image"
        assert result[0]["elements"][1]["content"] == "https://example.com/image.jpg"

        # Check second slide with no elements
        assert result[1]["id"] == "slide2"
        assert result[1]["elements"] == []

    def test_get_slides_error(self, mock_slides_service):
        """Test slides retrieval with API error."""
        presentation_id = "nonexistent_id"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Presentation not found"}}')

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.get.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 404,
            "message": "Presentation not found",
            "operation": "get_slides",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.get_slides(presentation_id)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with("get_slides", http_error)
        assert result == expected_error

    def test_delete_slide_success(self, mock_slides_service):
        """Test successful slide deletion."""
        # Test data
        presentation_id = "presentation_123"
        slide_id = "slide_to_delete"

        # Mock API response
        mock_response = {"replies": [{}]}

        # Setup execute mock
        mock_execute = MagicMock(return_value=mock_response)
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute = mock_execute

        # Call the method
        result = mock_slides_service.delete_slide(presentation_id, slide_id)

        # Verify API call with correct parameters
        mock_slides_service.service.presentations.return_value.batchUpdate.assert_called_once()
        call_args = mock_slides_service.service.presentations.return_value.batchUpdate.call_args
        assert call_args[1]["presentationId"] == presentation_id

        # Verify the request body contains correct deleteObject request
        request_body = call_args[1]["body"]
        assert "requests" in request_body
        assert len(request_body["requests"]) == 1
        assert "deleteObject" in request_body["requests"][0]
        assert request_body["requests"][0]["deleteObject"]["objectId"] == slide_id

        # Verify result has expected fields
        assert result["presentationId"] == presentation_id
        assert result["slideId"] == slide_id
        assert result["operation"] == "delete_slide"
        assert result["result"] == "success"

    def test_delete_slide_error(self, mock_slides_service):
        """Test slide deletion with API error."""
        presentation_id = "presentation_123"
        slide_id = "nonexistent_slide"

        # Create a mock HttpError
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        http_error = HttpError(mock_resp, b'{"error": {"message": "Invalid object ID"}}')

        # Setup the mock to raise the error
        mock_slides_service.service.presentations.return_value.batchUpdate.return_value.execute.side_effect = http_error

        # Mock error handling
        expected_error = {
            "error": True,
            "error_type": "http_error",
            "status_code": 400,
            "message": "Invalid object ID",
            "operation": "delete_slide",
        }
        mock_slides_service.handle_api_error = MagicMock(return_value=expected_error)

        # Call the method
        result = mock_slides_service.delete_slide(presentation_id, slide_id)

        # Verify error handling
        mock_slides_service.handle_api_error.assert_called_once_with("delete_slide", http_error)
        assert result == expected_error
