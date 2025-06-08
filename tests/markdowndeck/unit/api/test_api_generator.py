"""
Unit tests for the ApiRequestGenerator, ensuring adherence to API_GEN_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_UNIT_API_GENERATOR.md`.
"""

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
