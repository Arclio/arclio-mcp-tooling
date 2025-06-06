"""
Integration tests for the ApiClient, ensuring it correctly orchestrates
the ApiRequestGenerator and handles API interactions.
"""

from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.api.api_client import ApiClient
from markdowndeck.models import Deck, ElementType, ImageElement, Slide, TextElement


@pytest.fixture
def mock_google_service() -> MagicMock:
    """Provides a mock Google API service resource."""
    service = MagicMock()
    # Mock the presentations().create().execute() chain
    service.presentations.return_value.create.return_value.execute.return_value = {
        "presentationId": "pres_id_123",
        "slides": [{"objectId": "default_slide_id"}],
    }
    # Mock the presentations().batchUpdate().execute() chain
    service.presentations.return_value.batchUpdate.return_value.execute.return_value = {
        "replies": []
    }
    # Mock the presentations().get().execute() chain for fetching notes IDs
    service.presentations.return_value.get.return_value.execute.return_value = {
        "slides": [
            {
                "objectId": "slide_1",
                "slideProperties": {
                    "notesPage": {
                        "pageElements": [
                            {
                                "shape": {"shapeType": "TEXT_BOX"},
                                "objectId": "notes_shape_1",
                            }
                        ]
                    }
                },
            }
        ]
    }
    return service


@pytest.fixture
def api_client(mock_google_service: MagicMock) -> ApiClient:
    """Provides an ApiClient instance with a mocked service."""
    return ApiClient(service=mock_google_service)


class TestApiClientIntegration:
    """
    Tests the integration of ApiClient with ApiRequestGenerator and the (mocked) Google Slides API.
    """

    @patch("requests.head")
    def test_create_presentation_from_deck_flow(
        self, mock_requests_head, api_client: ApiClient, mock_google_service: MagicMock
    ):
        """
        Tests the entire `create_presentation_from_deck` flow, verifying orchestration.
        """
        # Mock requests.head to always return a valid image response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg", "content-length": "1024"}
        mock_requests_head.return_value = mock_response

        # Create a Deck object with various elements
        deck = Deck(
            title="Integration Test Deck",
            slides=[
                Slide(
                    object_id="slide_1",
                    elements=[
                        TextElement(element_type=ElementType.TITLE, text="Title"),
                        ImageElement(
                            element_type=ElementType.IMAGE,
                            url="http://valid.image/test.jpg",
                        ),
                    ],
                    notes="Slide 1 notes.",
                )
            ],
        )

        result = api_client.create_presentation_from_deck(deck)

        # 1. Verify presentation creation
        mock_google_service.presentations().create.assert_called_once_with(
            body={"title": "Integration Test Deck"}
        )

        # 2. Verify default slide deletion
        batch_update_calls = (
            mock_google_service.presentations().return_value.batchUpdate.call_args_list
        )
        delete_call = next(
            (c for c in batch_update_calls if "deleteObject" in str(c.kwargs["body"])),
            None,
        )
        assert (
            delete_call is not None
        ), "A batchUpdate call to delete the default slide was not made."
        assert (
            delete_call.kwargs["body"]["requests"][0]["deleteObject"]["objectId"]
            == "default_slide_id"
        )

        # 3. Verify content batch update
        content_call = next(
            (c for c in batch_update_calls if "createSlide" in str(c.kwargs["body"])),
            None,
        )
        assert (
            content_call is not None
        ), "A batchUpdate call to create content was not made."
        assert any(
            "createImage" in req for req in content_call.kwargs["body"]["requests"]
        ), "Image creation request missing."

        # 4. Verify notes batch update
        notes_call = next(
            (
                c
                for c in batch_update_calls
                if "insertText" in str(c.kwargs["body"])
                and c.kwargs["body"]["requests"][0]["insertText"]["objectId"]
                == "notes_shape_1"
            ),
            None,
        )
        assert notes_call is not None, "A batchUpdate call to add notes was not made."
        assert (
            notes_call.kwargs["body"]["requests"][0]["insertText"]["text"]
            == "Slide 1 notes."
        )

        # 5. Verify final result
        assert result["presentationId"] == "pres_id_123"
        assert result["title"] == "Integration Test Deck"

    @patch("requests.head")
    def test_image_validation_replaces_invalid_url(
        self, mock_requests_head, api_client: ApiClient, mock_google_service: MagicMock
    ):
        """
        Tests that the ApiClient correctly identifies an invalid image URL and
        replaces the createImage request with a placeholder shape request.
        """
        # Mock requests.head to return a 404 Not Found
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests_head.return_value = mock_response

        deck = Deck(
            title="Invalid Image Deck",
            slides=[
                Slide(
                    object_id="slide_1",
                    elements=[
                        ImageElement(
                            element_type=ElementType.IMAGE,
                            url="http://invalid.image/test.jpg",
                            object_id="invalid_image_1",
                        ),
                    ],
                )
            ],
        )

        api_client.create_presentation_from_deck(deck)

        # Find the content creation call
        batch_update_calls = (
            mock_google_service.presentations().return_value.batchUpdate.call_args_list
        )
        content_call = next(
            (c for c in batch_update_calls if "createSlide" in str(c.kwargs["body"])),
            None,
        )
        assert content_call is not None

        requests = content_call.kwargs["body"]["requests"]

        # The createImage request should be GONE
        assert not any("createImage" in r for r in requests)

        # A createShape request for the placeholder should exist
        placeholder_shape_req = next(
            (
                r
                for r in requests
                if "createShape" in r
                and r["createShape"]["objectId"] == "invalid_image_1"
            ),
            None,
        )
        assert placeholder_shape_req is not None
        assert placeholder_shape_req["createShape"]["shapeType"] == "TEXT_BOX"

        # Text should be inserted into the placeholder
        placeholder_text_req = next(
            (
                r
                for r in requests
                if "insertText" in r
                and r["insertText"]["objectId"] == "invalid_image_1"
            ),
            None,
        )
        assert placeholder_text_req is not None
        assert placeholder_text_req["insertText"]["text"] == "[Image not available]"

    def test_single_batch_for_default_slide_deletion(
        self, api_client: ApiClient, mock_google_service: MagicMock
    ):
        """Tests that multiple default slides are deleted in a single API call."""
        # Mock a presentation with multiple default slides
        presentation_data = {
            "presentationId": "pres_id_multi_slide",
            "slides": [
                {"objectId": "default_1"},
                {"objectId": "default_2"},
                {"objectId": "default_3"},
            ],
        }

        api_client._delete_default_slides("pres_id_multi_slide", presentation_data)

        # Should be exactly ONE batchUpdate call
        mock_google_service.presentations().batchUpdate.assert_called_once()

        # The body of that call should contain 3 deleteObject requests
        call_args = mock_google_service.presentations().batchUpdate.call_args
        requests_list = call_args.kwargs["body"]["requests"]

        assert len(requests_list) == 3
        assert all("deleteObject" in r for r in requests_list)
        object_ids_deleted = {r["deleteObject"]["objectId"] for r in requests_list}
        assert object_ids_deleted == {"default_1", "default_2", "default_3"}
