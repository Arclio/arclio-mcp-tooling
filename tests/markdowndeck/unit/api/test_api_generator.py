"""
Unit tests for the ApiRequestGenerator, ensuring adherence to API_GEN_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_UNIT_API_GENERATOR.md`.
"""

import re
from copy import deepcopy

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.models.elements.list import ListElement


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


@pytest.fixture
def finalized_slide() -> Slide:
    """
    Provides a slide in the 'Finalized' state, which is the expected
    input for the ApiRequestGenerator.
    """
    return Slide(
        object_id="final_slide_1",
        sections=[],  # Must be empty
        elements=[],  # Must be empty
        renderable_elements=[
            TextElement(
                element_type=ElementType.TITLE,
                text="Finalized Title",
                object_id="el_title",
                position=(50, 50),
                size=(620, 40),
            ),
            TextElement(
                element_type=ElementType.TEXT,
                text="Finalized Body",
                object_id="el_body",
                position=(50, 150),
                size=(620, 100),
            ),
        ],
    )


class TestApiRequestGenerator:
    """Tests the functionality of the ApiRequestGenerator."""

    def test_object_id_regex_compliance(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-06
        Validates that all generated objectIds comply with Google Slides API regex.

        Per Google Slides API documentation, objectIds must match:
        ^[a-zA-Z0-9_][a-zA-Z0-9_-:]*$
        """
        # Arrange: Create a slide with various element types without object_ids
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Test Title",
                    position=(50, 50),
                    size=(620, 40),
                    object_id=None,  # Explicitly set to None to force generation
                ),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Test Body",
                    position=(50, 150),
                    size=(620, 100),
                    object_id=None,  # Explicitly set to None to force generation
                ),
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="https://example.com/image.jpg",
                    position=(50, 300),
                    size=(300, 200),
                    object_id=None,  # Explicitly set to None to force generation
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that ALL objectIds in createShape/createImage requests match the regex
        google_slides_object_id_regex = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_:\-]*$")

        generated_object_ids = []
        for batch in batches:
            for request in batch["requests"]:
                object_id = None

                # Extract objectId from different request types
                if "createShape" in request:
                    object_id = request["createShape"]["objectId"]
                elif "createImage" in request:
                    object_id = request["createImage"]["objectId"]
                elif "createSlide" in request:
                    object_id = request["createSlide"]["objectId"]
                elif "insertText" in request:
                    object_id = request["insertText"]["objectId"]
                elif "updateParagraphStyle" in request:
                    object_id = request["updateParagraphStyle"]["objectId"]

                # Validate objectId if found
                if object_id:
                    generated_object_ids.append(object_id)
                    assert google_slides_object_id_regex.match(object_id), (
                        f"ObjectId '{object_id}' does not match Google Slides API regex "
                        f"^[a-zA-Z0-9_][a-zA-Z0-9_-:]*$"
                    )

        # Ensure we actually tested some objectIds
        assert len(generated_object_ids) > 0, "No objectIds were generated to test"

    def test_empty_list_no_delete_text(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-07
        Validates that empty lists don't generate invalid deleteText requests.

        This tests the fix for Discrepancy #2: Invalid deleteText for empty placeholders.
        """
        # Arrange: Create a slide with an empty list element
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[],  # Empty list
                    position=(50, 150),
                    size=(620, 100),
                    object_id=None,
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that no deleteText requests are generated for empty lists
        for batch in batches:
            for request in batch["requests"]:
                assert (
                    "deleteText" not in request
                ), "Empty lists should not generate deleteText requests as they would be invalid"

    def test_invalid_image_url_skipped(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-08
        Validates that invalid image URLs are skipped and don't generate createImage requests.

        This tests the fix for Discrepancy #3: Inconsistent image URL validation.
        """
        # Arrange: Create a slide with an invalid image URL
        slide = Slide(
            object_id="test_slide",
            sections=[],
            elements=[],
            renderable_elements=[
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="invalid-url-not-http",  # Invalid URL
                    position=(50, 300),
                    size=(300, 200),
                    object_id=None,
                ),
            ],
        )
        deck = Deck(slides=[slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert: Check that no createImage requests are generated for invalid URLs
        for batch in batches:
            for request in batch["requests"]:
                assert (
                    "createImage" not in request
                ), "Invalid image URLs should not generate createImage requests"

    def test_api_c_01(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-01
        Validates the generator ONLY reads from `slide.renderable_elements`.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange: Add junk data to stale lists
        finalized_slide.sections = [Section(id="junk_section")]
        finalized_slide.elements = [
            ImageElement(element_type=ElementType.IMAGE, url="junk.png")
        ]
        deck = Deck(slides=[finalized_slide])

        # Act
        batches = api_generator.generate_batch_requests(deck, "pres_id")

        # Assert
        requests = batches[0]["requests"]

        # Check that requests were generated for renderable_elements
        title_req = next(
            (
                r
                for r in requests
                if r.get("insertText", {}).get("text") == "Finalized Title"
            ),
            None,
        )
        body_req = next(
            (
                r
                for r in requests
                if r.get("insertText", {}).get("text") == "Finalized Body"
            ),
            None,
        )
        assert title_req is not None
        assert body_req is not None

        # Check that junk data was ignored
        image_req = next((r for r in requests if "createImage" in r), None)
        assert (
            image_req is None
        ), "Junk data from stale 'elements' list should be ignored."

    def test_api_c_02(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-02
        Validates that the generator is stateless and does not modify its input.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        original_slide_copy = deepcopy(finalized_slide)
        deck = Deck(slides=[finalized_slide])

        # Act
        api_generator.generate_batch_requests(deck, "pres_id")

        # Assert
        assert (
            finalized_slide == original_slide_copy
        ), "Generator must not modify the input slide object."

    def test_api_c_03(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-03
        Validates interpretation of visual styling directives.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        styled_element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled Text",
            object_id="styled_el",
            position=(50, 200),
            size=(200, 50),
            directives={"color": "#FF0000", "fontsize": 18},
        )
        finalized_slide.renderable_elements.append(styled_element)
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        style_reqs = [
            r
            for r in requests
            if "updateTextStyle" in r
            and r["updateTextStyle"]["objectId"] == "styled_el"
        ]
        assert (
            len(style_reqs) > 0
        ), "Should generate updateTextStyle requests for directives."

        # Find the specific style updates
        color_update = next(
            (
                r
                for r in style_reqs
                if "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        font_update = next(
            (r for r in style_reqs if "fontSize" in r["updateTextStyle"]["style"]), None
        )

        assert (
            color_update is not None
        ), "A request to update foregroundColor should exist."
        assert (
            color_update["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
                "rgbColor"
            ]["red"]
            == 1.0
        )

        assert font_update is not None, "A request to update fontSize should exist."
        assert font_update["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 18

    def test_api_c_04(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-04
        Validates correct structure for position and size in API requests.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        shape_req = next(
            (
                r
                for r in requests
                if "createShape" in r and r["createShape"]["objectId"] == "el_body"
            ),
            None,
        )
        assert (
            shape_req is not None
        ), "A createShape request for the element should exist."

        props = shape_req["createShape"]["elementProperties"]

        # Check size structure
        assert "size" in props
        assert "width" in props["size"]
        assert "height" in props["size"]
        assert "magnitude" in props["size"]["width"]
        assert "unit" in props["size"]["width"]

        # Check transform structure
        assert "transform" in props
        assert "translateX" in props["transform"]
        assert "translateY" in props["transform"]
        assert "unit" in props["transform"]

    def test_api_c_05(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-05
        Validates that generated requests use precise `fields` masks.
        From: docs/markdowndeck/testing/TEST_CASES_API_GENERATOR.md
        """
        # Arrange
        bg_element = TextElement(
            element_type=ElementType.TEXT,
            text="BG Text",
            object_id="bg_el",
            position=(50, 250),
            size=(200, 50),
            directives={"background": ("color", "#123456")},
        )
        finalized_slide.renderable_elements.append(bg_element)
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Assert
        update_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and r["updateShapeProperties"]["objectId"] == "bg_el"
            ),
            None,
        )

        assert (
            update_req is not None
        ), "An updateShapeProperties request should exist for the background."

        # Validate the fields mask is precise as per the gotcha
        expected_mask = "shapeBackgroundFill.solidFill.color.rgbColor"
        assert (
            update_req["updateShapeProperties"]["fields"] == expected_mask
        ), f"Field mask must be precise. Expected '{expected_mask}', got '{update_req['updateShapeProperties']['fields']}'"
