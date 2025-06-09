# File: tests/markdowndeck/unit/api/test_api_generator_placeholders.py

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    Slide,
    SlideLayout,
    TextElement,
)


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


class TestApiPlaceholderUsage:
    def test_subtitle_uses_placeholder_instead_of_creating_new_shape(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-C-16 (new)
        Validates that a subtitle element correctly uses the subtitle placeholder
        from a theme layout instead of creating a new shape. This prevents
        overlapping, empty text boxes on title slides.
        """
        # Arrange
        # A slide with a layout that typically has both a title and subtitle placeholder.
        # Let the SlideRequestBuilder auto-generate placeholder mappings from LAYOUT_PLACEHOLDERS
        slide = Slide(
            object_id="subtitle_placeholder_test",
            layout=SlideLayout.TITLE,  # This layout currently only has CENTERED_TITLE, no SUBTITLE
            renderable_elements=[
                TextElement(element_type=ElementType.TITLE, text="Main Title"),
                TextElement(element_type=ElementType.SUBTITLE, text="My Subtitle"),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        # Find all createShape requests in the batch
        create_shape_requests = [
            req.get("createShape") for req in requests if "createShape" in req
        ]

        # This is the critical assertion that will fail. We should NOT be creating new shapes for subtitle elements
        # when subtitle placeholders are available.
        subtitle_shape_created = any(
            shape_req.get("shapeType") == "TEXT_BOX"
            and any(
                "insertText" in req
                and req["insertText"]["objectId"] == shape_req.get("objectId")
                and req["insertText"]["text"] == "My Subtitle"
                for req in requests
            )
            for shape_req in create_shape_requests
        )
        assert (
            not subtitle_shape_created
        ), "A new shape should NOT be created for the subtitle; it should use the placeholder."

        # Verify that we are inserting text into a subtitle placeholder instead of creating new shapes
        # In the current implementation, since TITLE layout has no SUBTITLE placeholder defined,
        # this should fail until we fix the layout definition
        subtitle_placeholder_used = any(
            req.get("insertText", {}).get("text") == "My Subtitle"
            and "placeholder" in req.get("insertText", {}).get("objectId", "")
            for req in requests
        )

        assert subtitle_placeholder_used, (
            "Subtitle should use a placeholder, not create a new shape. "
            "This indicates that TITLE layout needs SUBTITLE placeholder defined."
        )
