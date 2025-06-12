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
    # REFACTORED: Removed `sections` argument to align with the new Slide model.
    return Slide(
        object_id="final_slide_1",
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
        # Add junk data to stale attributes to ensure they are ignored.
        finalized_slide.root_section = "Junk data"  # type: ignore
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
        assert image_req is None, "Junk data from stale attributes must be ignored."

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
        ), "Generator must not modify input."

    def test_api_c_03_and_c_09(
        self, api_generator: ApiRequestGenerator, finalized_slide: Slide
    ):
        """
        Test Cases: API-C-03 & API-C-09
        Validates interpretation of visual styling directives and color formats.
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

        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == "styled_el"
            ),
            None,
        )
        assert style_req is not None, "A request to update text style should exist."

        style_payload = style_req["updateTextStyle"]["style"]
        assert (
            "foregroundColor" in style_payload
        ), "Style payload should contain foregroundColor."
        assert "fontSize" in style_payload, "Style payload should contain fontSize."

        rgb_color = style_payload["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert abs(rgb_color["red"] - 1.0) < 0.01
        assert rgb_color["green"] == 0
        assert rgb_color["blue"] == 0

    def test_api_c_05_and_c_18(
        self, api_generator: ApiRequestGenerator, finalized_slide: Slide
    ):
        """
        Test Cases: API-C-05 & API-C-18
        Validates that all slides are created using the BLANK layout and all elements are new shapes.
        """
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None
        assert (
            create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"]
            == "BLANK"
        )

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
