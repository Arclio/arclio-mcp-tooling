# File: tests/markdowndeck/unit/api/test_api_generator_request_order.py

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    Slide,
    TextElement,
)
from markdowndeck.models.constants import SlideLayout


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


class TestApiRequestOrder:
    def test_autofit_is_disabled_before_inserting_text_in_placeholders(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-14 (new)
        Validates that for themed placeholders, the 'autofit: NONE' request
        is sent BEFORE the 'insertText' request to prevent race conditions
        with theme-default autofitting.
        """
        # Arrange
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This text goes into a themed placeholder.",
        )
        slide = Slide(
            object_id="themed_slide_order_test",
            renderable_elements=[text_element],
            placeholder_mappings={ElementType.TEXT: "body_placeholder_id_123"},
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        autofit_request_index = -1
        insert_text_request_index = -1

        for i, req in enumerate(requests):
            if (
                "updateShapeProperties" in req
                and req["updateShapeProperties"]["objectId"]
                == "body_placeholder_id_123"
            ) and "autofit" in req["updateShapeProperties"].get("shapeProperties", {}):
                autofit_request_index = i

            if (
                "insertText" in req
                and req["insertText"]["objectId"] == "body_placeholder_id_123"
            ):
                insert_text_request_index = i

        assert autofit_request_index != -1, "Autofit request for placeholder not found."
        assert (
            insert_text_request_index != -1
        ), "Insert text request for placeholder not found."

        # This is the critical assertion that will fail with the current implementation.
        assert (
            autofit_request_index < insert_text_request_index
        ), "The 'autofit: NONE' request must come BEFORE the 'insertText' request."

    def test_unused_placeholders_are_deleted(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-15 (new)
        Validates that unused placeholders from a slide's layout are explicitly
        deleted to prevent them from appearing on the final slide.
        """
        # Arrange
        # Use a two-column layout but only provide content for the first column.
        slide = Slide(
            object_id="placeholder_cleanup_test",
            layout=SlideLayout.TITLE_AND_TWO_COLUMNS,
            renderable_elements=[
                TextElement(element_type=ElementType.TITLE, text="Title"),
                TextElement(element_type=ElementType.TEXT, text="Left Column Content"),
            ],
            # Simulate the placeholder mappings that would be created.
            # We will use the 'BODY' placeholder for the left column, leaving 'BODY_1' unused.
            placeholder_mappings={
                ElementType.TITLE: "ph_title",
                ElementType.TEXT: "ph_body_0",  # Mapped to the left column text
                "text_1": "ph_body_1",  # This is the unused placeholder
            },
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        delete_requests = [req for req in requests if "deleteObject" in req]

        assert len(delete_requests) > 0, "Expected at least one deleteObject request."

        deleted_object_ids = [
            req["deleteObject"]["objectId"] for req in delete_requests
        ]

        # The key assertion: The unused placeholder must be in the list of deleted objects.
        assert (
            "ph_body_1" in deleted_object_ids
        ), "The unused placeholder 'ph_body_1' was not deleted."
