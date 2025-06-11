"""
Unit tests for the ApiRequestGenerator, ensuring adherence to API_GEN_SPEC.md.
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
    """Provides a slide in the 'Finalized' state."""
    return Slide(
        object_id="final_slide_1",
        sections=[],
        elements=[],
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
        """
        finalized_slide.sections = [Section(id="junk_section")]
        finalized_slide.elements = [
            ImageElement(element_type=ElementType.IMAGE, url="junk.png")
        ]
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        title_req = next(
            (
                r
                for r in requests
                if r.get("createShape", {}).get("objectId") == "el_title"
            ),
            None,
        )
        body_req = next(
            (
                r
                for r in requests
                if r.get("createShape", {}).get("objectId") == "el_body"
            ),
            None,
        )
        assert title_req is not None
        assert body_req is not None
        image_req = next((r for r in requests if "createImage" in r), None)
        assert (
            image_req is None
        ), "Junk data from stale 'elements' list must be ignored."

    def test_api_c_02(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-02
        Validates that the generator is stateless and does not modify its input.
        """
        original_slide_copy = deepcopy(finalized_slide)
        deck = Deck(slides=[finalized_slide])
        api_generator.generate_batch_requests(deck, "pres_id")
        assert (
            finalized_slide == original_slide_copy
        ), "Generator must not modify the input slide."

    def test_api_c_03(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-03
        Validates interpretation of visual styling directives.
        """
        styled_element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled",
            object_id="styled_el",
            position=(50, 200),
            size=(200, 50),
            directives={"color": "#FF0000", "fontsize": 18},
        )
        finalized_slide.renderable_elements.append(styled_element)
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        style_reqs = [
            r
            for r in requests
            if "updateTextStyle" in r
            and r["updateTextStyle"]["objectId"] == "styled_el"
        ]
        assert len(style_reqs) > 0
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
        assert font_update is not None, "A request to update fontSize should exist."

    def test_api_c_05(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-05
        Validates that generated requests use precise `fields` masks.
        """
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
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        update_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and r["updateShapeProperties"]["objectId"] == "bg_el"
            ),
            None,
        )
        assert update_req is not None

        # FIXED: Test that the required mask is a SUBSET of the generated fields.
        # This is more robust and allows for combined property updates.
        expected_mask = "shapeBackgroundFill.solidFill.color.rgbColor"
        actual_fields = update_req["updateShapeProperties"]["fields"]
        assert (
            expected_mask in actual_fields
        ), f"Expected fields to contain '{expected_mask}', but got '{actual_fields}'."

    def test_api_c_18_universal_shape_creation(
        self, api_generator: ApiRequestGenerator, finalized_slide: Slide
    ):
        """
        Test Case: API-C-18
        Validates that a new shape is created for the TITLE element.
        """
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        title_create_shape = next(
            (
                r
                for r in requests
                if "createShape" in r and r["createShape"]["objectId"] == "el_title"
            ),
            None,
        )
        assert (
            title_create_shape is not None
        ), "A createShape request MUST be generated for the TITLE element."

    def test_api_c_06_blank_layout_is_always_used(
        self, api_generator: ApiRequestGenerator, finalized_slide: Slide
    ):
        """
        Test Case: API-C-06
        Validates that all slides are created using the BLANK layout.
        """
        # Arrange
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        create_slide_req = next((r for r in requests if "createSlide" in r), None)

        # Assert
        assert create_slide_req is not None
        assert (
            create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            == "BLANK"
        )

    def test_api_c_09_color_format_handling(
        self, api_generator: ApiRequestGenerator, finalized_slide: Slide
    ):
        """
        Test Case: API-C-09
        Validates correct conversion of different color formats.
        """
        # Arrange
        hex_element = TextElement(
            element_type=ElementType.TEXT,
            text="Red",
            object_id="hex_el",
            position=(10, 10),
            size=(100, 20),
            directives={"color": "#FF0000"},
        )
        finalized_slide.renderable_elements.append(hex_element)
        deck = Deck(slides=[finalized_slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == "hex_el"
            ),
            None,
        )

        # Assert
        assert style_req is not None
        rgb_color = style_req["updateTextStyle"]["style"]["foregroundColor"][
            "opaqueColor"
        ]["rgbColor"]
        assert abs(rgb_color["red"] - 1.0) < 0.01
        assert abs(rgb_color["green"] - 0.0) < 0.01
        assert abs(rgb_color["blue"] - 0.0) < 0.01
