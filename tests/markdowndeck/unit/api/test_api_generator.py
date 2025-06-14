from copy import deepcopy

import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
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
    Provides a slide in the 'Finalized' state per DATA_FLOW.md.
    - `renderable_elements` is the source of truth.
    - `root_section` and `elements` are cleared/ignored.
    """
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
        root_section=None,
        elements=[],
    )


class TestApiRequestGenerator:
    """Tests the functionality of the ApiRequestGenerator."""

    def test_api_c_01(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-01 (from spec, re-interpreted for current code)
        Validates the generator ONLY reads from `slide.renderable_elements`.
        """
        # Add junk data to stale attributes to ensure they are ignored.
        finalized_slide.root_section = "Junk data"  # type: ignore
        finalized_slide.elements = [
            ImageElement(
                element_type=ElementType.IMAGE,
                url="junk.png",
                directives={"width": 10, "height": 10},
            )
        ]
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        title_req = next(
            (r for r in requests if r.get("createShape", {}).get("objectId") == "el_title"),
            None,
        )
        body_req = next(
            (r for r in requests if r.get("createShape", {}).get("objectId") == "el_body"),
            None,
        )
        assert title_req is not None, "Request for title in renderable_elements not found."
        assert body_req is not None, "Request for body in renderable_elements not found."
        image_req = next((r for r in requests if "createImage" in r), None)
        assert image_req is None, "Junk data from stale attributes must be ignored."

    def test_api_c_02(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-02 (from spec)
        Validates that the generator is stateless and does not modify its input.
        """
        original_slide_copy = deepcopy(finalized_slide)
        deck = Deck(slides=[finalized_slide])
        api_generator.generate_batch_requests(deck, "pres_id")
        assert finalized_slide == original_slide_copy, "Generator must not modify input."

    def test_api_c_03_visual_styling(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Case: API-C-03 (from spec)
        Validates interpretation of visual styling directives on an element.
        """
        styled_element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled",
            object_id="styled_el",
            position=(50, 200),
            size=(200, 50),
            directives={
                "color": {
                    "type": "color",
                    "value": {"type": "hex", "value": "#FF0000"},
                },
                "fontsize": 18,
            },
        )
        finalized_slide.renderable_elements.append(styled_element)
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        style_req = next(
            (r for r in requests if "updateTextStyle" in r and r["updateTextStyle"]["objectId"] == "styled_el"),
            None,
        )
        assert style_req is not None, "A request to update text style should exist."
        style_payload = style_req["updateTextStyle"]["style"]
        assert "foregroundColor" in style_payload
        assert "fontSize" in style_payload
        rgb_color = style_payload["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert abs(rgb_color["red"] - 1.0) < 0.01

    def test_api_c_04_coordinate_transformation(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-04.
        Spec: Validates correct coordinate transformation into Google Slides API PT format.
        """
        # Arrange
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Positioned",
            object_id="pos_el",
            position=(100, 200),
            size=(300, 50),
        )
        slide = Slide(object_id="pos_slide", renderable_elements=[element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        create_shape_req = next((r for r in requests if "createShape" in r), None)

        # Assert
        assert create_shape_req is not None
        properties = create_shape_req["createShape"]["elementProperties"]
        size = properties["size"]
        transform = properties["transform"]

        assert size["width"] == {"magnitude": 300, "unit": "PT"}
        assert size["height"] == {"magnitude": 50, "unit": "PT"}
        assert transform["translateX"] == 100
        assert transform["translateY"] == 200
        assert transform["unit"] == "PT"

    def test_api_c_05_and_c_06_blank_canvas_and_create_shape(self, api_generator: ApiRequestGenerator, finalized_slide: Slide):
        """
        Test Cases: API-C-05 & API-C-06 (from spec)
        Validates that all slides use BLANK layout and all elements are new shapes.
        """
        deck = Deck(slides=[finalized_slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None
        assert create_slide_req["createSlide"]["slideLayoutReference"]["predefinedLayout"] == "BLANK"
        title_create_shape = next(
            (r for r in requests if "createShape" in r and r["createShape"]["objectId"] == "el_title"),
            None,
        )
        assert title_create_shape is not None, "A createShape request MUST be generated for the TITLE element."

    def test_api_c_07_empty_renderable_elements(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-07.
        Spec: Verify graceful handling of a slide with no renderable elements.
        """
        slide = Slide(object_id="empty_slide", renderable_elements=[])
        deck = Deck(slides=[slide])

        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        create_slide_req = next((r for r in requests if "createSlide" in r), None)
        assert create_slide_req is not None, "createSlide request should always exist."
        assert len(requests) == 1, "Only createSlide request should be generated."

    def test_api_c_08_continuation_title(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-08 (from spec, same as API_GEN_SPEC rule #3)
        Verify correct handling of the `is_continuation` flag to modify a title.
        """
        slide = Slide(
            object_id="cont_slide_1",
            is_continuation=True,
            renderable_elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="My Long Title",
                    object_id="el_cont_title",
                    position=(50, 50),
                    size=(620, 40),
                )
            ],
        )
        deck = Deck(slides=[slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        insert_text_req = next(
            (r for r in requests if "insertText" in r and r["insertText"]["objectId"] == "el_cont_title"),
            None,
        )
        assert insert_text_req is not None
        assert insert_text_req["insertText"]["text"] == "My Long Title (continued)"

    def test_api_c_09_zero_dimension_elements(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-09 (from spec)
        Verify that zero-dimension elements with visual directives are not rendered.
        """
        slide = Slide(
            object_id="zero_dim_slide",
            renderable_elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="",
                    object_id="el_zero_dim",
                    position=(50, 50),
                    size=(0, 0),
                    directives={"background": "#FF0000"},
                )
            ],
        )
        deck = Deck(slides=[slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        shape_req = next(
            (r for r in requests if r.get("createShape", {}).get("objectId") == "el_zero_dim"),
            None,
        )
        assert shape_req is None, (
            "createShape request must not be generated for zero-dimension element with visual directives."
        )

    def test_api_c_10_list_indentation(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-C-10.
        Spec: Verify that nested list items generate proper indentation requests.
        """
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            object_id="list_1",
            position=(50, 50),
            size=(400, 200),
            items=[
                ListItem(
                    text="Level 0",
                    level=0,
                    children=[ListItem(text="Level 1", level=1)],
                )
            ],
        )
        slide = Slide(object_id="list_slide", renderable_elements=[list_element])
        deck = Deck(slides=[slide])

        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        indent_request = next(
            (r for r in requests if "updateParagraphStyle" in r and "indentStart" in r["updateParagraphStyle"]["style"]),
            None,
        )

        assert indent_request is not None, "Indentation request should be generated for nested list items."
        style = indent_request["updateParagraphStyle"]["style"]
        assert style["indentStart"]["magnitude"] > 0
        assert style["indentStart"]["unit"] == "PT"

    def test_api_c_11_continuation_context_title(self, api_generator: ApiRequestGenerator):
        """
        Test Case: NEW, based on API_GEN_SPEC.md Rule #11
        Validates rendering of the `continuation_context_title`.
        """
        slide = Slide(
            object_id="cont_slide_2",
            is_continuation=True,
            continuation_context_title="Continuing list from: Parent Item",
            renderable_elements=[],
        )
        deck = Deck(slides=[slide])
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        create_shape_req = next(
            (r for r in requests if "createShape" in r and "context_title" in r["createShape"]["objectId"]),
            None,
        )
        insert_text_req = next(
            (r for r in requests if "insertText" in r and "context_title" in r["insertText"]["objectId"]),
            None,
        )
        style_req = next(
            (r for r in requests if "updateTextStyle" in r and "context_title" in r["updateTextStyle"]["objectId"]),
            None,
        )

        assert create_shape_req is not None, "Shape for context title must be created."
        assert insert_text_req is not None, "Text for context title must be inserted."
        assert style_req is not None, "Style for context title must be applied."

        assert insert_text_req["insertText"]["text"] == "Continuing list from: Parent Item"
        assert style_req["updateTextStyle"]["style"]["italic"] is True
        assert style_req["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 10
