import logging
from unittest.mock import MagicMock, patch

import pytest
from markdowndeck.api import ApiRequestGenerator
from markdowndeck.layout.metrics.text import (
    _get_typography_params,
    calculate_text_element_height,
)
from markdowndeck.models import (
    Deck,
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
)
from markdowndeck.overflow import OverflowManager

logger = logging.getLogger(__name__)


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    return ApiRequestGenerator()


class TestKnownLimitations:
    """A suite of tests designed to fail, exposing known bugs for TDD."""

    def test_bug_text_wrapping_is_one_line_too_short(self):
        """
        BUG: Text Wrapping (-1 Line Bug)
        DESCRIPTION: The layout metrics consistently calculate the height of wrapped
                     text as one line shorter than required, causing the last line to be clipped.
        EXPECTED TO FAIL: No. The workaround in `font_metrics.py` fixes this.
        """
        # Arrange
        long_text = "This is a single, very long line of text designed to test the wrapping capability of the text metrics. It should be broken into multiple lines by the font engine, and the resulting height should be accurate."
        text_element = TextElement(element_type=ElementType.TEXT, text=long_text)
        available_width = 300.0

        # Act
        calculated_height = calculate_text_element_height(text_element, available_width)

        # Assert
        from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox

        font_size, line_height_multiplier, padding, min_height = _get_typography_params(
            ElementType.TEXT, {}
        )
        _, accurate_text_height, line_metrics = calculate_text_bbox(
            long_text,
            font_size,
            max_width=(available_width - (padding * 2)),
            line_height_multiplier=line_height_multiplier,
        )
        expected_height = max(accurate_text_height + (padding * 2), min_height)
        num_lines = len(line_metrics)

        assert num_lines > 1, "Test setup failed: text did not wrap as expected."
        assert abs(calculated_height - expected_height) < 2.0, (
            f"Calculated height is inaccurate. "
            f"Calculated: {calculated_height:.2f}pt, Expected: {expected_height:.2f}pt. "
            f"This suggests the height for one line of text is being omitted."
        )

    def test_bug_nested_list_indentation_is_not_applied_correctly(
        self, api_generator: ApiRequestGenerator
    ):
        """
        BUG: List Indentation API Bug
        DESCRIPTION: Nested list items are not correctly indented in the final Google Slide because
                     the API request is missing the hanging indent (`indentFirstLine`) property.
        EXPECTED TO FAIL: No. This is fixed in ListRequestBuilder.
        """
        # Arrange
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            object_id="nested_list_bug",
            position=(50, 50),
            size=(400, 200),
            items=[
                ListItem(text="L0", level=0, children=[ListItem(text="L1", level=1)])
            ],
        )
        slide = Slide(object_id="s1", renderable_elements=[list_element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        indent_request = None
        for r in requests:
            if "updateParagraphStyle" in r:
                style = r["updateParagraphStyle"].get("style", {})
                if "indentStart" in style and style["indentStart"]["magnitude"] > 0:
                    indent_request = r["updateParagraphStyle"]
                    break
        assert (
            indent_request is not None
        ), "An indentation request for the nested item should exist."
        style = indent_request["style"]
        assert (
            "indentStart" in style
        ), "indentStart property must be present for nested items."
        assert (
            "indentFirstLine" in style
        ), "Hanging indent property 'indentFirstLine' is missing."
        assert (
            style["indentFirstLine"]["magnitude"] < 0
        ), "indentFirstLine should be negative for a hanging indent."

    def test_bug_list_item_styling_is_not_applied(
        self, api_generator: ApiRequestGenerator
    ):
        """
        BUG: List Item Styling Not Applied
        DESCRIPTION: Styling directives on individual list items are parsed but not
                     translated into updateTextStyle API requests.
        EXPECTED TO FAIL: No. This is fixed in ListRequestBuilder and ListFormatter.
        """
        # Arrange
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            object_id="styled_list_bug",
            position=(50, 50),
            size=(400, 100),
            items=[
                ListItem(text="Regular", level=0),
                ListItem(
                    text="Red Item",
                    level=0,
                    formatting=[TextFormat(0, 8, TextFormatType.COLOR, "red")],
                ),
            ],
        )
        slide = Slide(object_id="s2", renderable_elements=[list_element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        color_style_req = None
        for r in requests:
            if "updateTextStyle" in r:
                update_req = r["updateTextStyle"]
                style = update_req.get("style", {})
                if (
                    update_req.get("objectId") == "styled_list_bug"
                    and "foregroundColor" in style
                ):
                    color = (
                        style["foregroundColor"]
                        .get("opaqueColor", {})
                        .get("rgbColor", {})
                    )
                    if color.get("red") == 1.0:
                        color_style_req = r
                        break

        assert (
            color_style_req is not None
        ), "No 'updateTextStyle' request was generated to apply color to the list item."

    def test_bug_table_row_text_styling_is_not_applied(
        self, api_generator: ApiRequestGenerator
    ):
        """
        BUG: Table Row Styling Not Applied
        DESCRIPTION: Styling directives like `color` on table rows are parsed but not
                     translated into updateTextStyle API requests.
        EXPECTED TO FAIL: No. This is fixed in TableRequestBuilder.
        """
        table = TableElement(
            element_type=ElementType.TABLE,
            object_id="table_text_color_bug",
            position=(50, 50),
            size=(400, 200),
            headers=["Header"],
            rows=[["Blue Text"]],
            row_directives=[
                {},
                {
                    "color": {
                        "type": "color",
                        "value": {"type": "hex", "value": "#0000FF"},
                    }
                },
            ],
        )
        slide = Slide(object_id="s3", renderable_elements=[table])
        deck = Deck(slides=[slide])

        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        text_color_req = None
        for r in requests:
            if "updateTextStyle" in r:
                update_req = r["updateTextStyle"]
                if (
                    update_req.get("objectId") == "table_text_color_bug"
                    and "cellLocation" in update_req
                ) and (update_req["cellLocation"].get("rowIndex") == 1):
                    text_color_req = update_req
                    break

        assert (
            text_color_req is not None
        ), "`updateTextStyle` request for the styled table row is missing."
        style = text_color_req["style"]
        assert (
            "foregroundColor" in style
        ), "foregroundColor property is missing from style."
        rgb = style["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert (
            abs(rgb["blue"] - 1.0) < 0.01
        ), "Text color was not correctly set to blue."

    def test_bug_continuation_title_is_duplicated(self):
        """
        BUG: Duplicate "(continued)" Suffix
        DESCRIPTION: The overflow process results in titles like "My Title (continued) (continued)".
        EXPECTED TO FAIL: No. The bug is fixed in the ApiGenerator. This test verifies the fix.
        """
        # Arrange
        # FIXED: Test setup now correctly triggers an overflow.
        title_element = TextElement(
            element_type=ElementType.TITLE, text="Original Title", object_id="title_el"
        )
        text_element = TextElement(
            element_type=ElementType.TEXT, text="Content", object_id="content_el"
        )
        text_element.split = MagicMock(
            return_value=(
                TextElement(element_type=ElementType.TEXT, text="Fit", size=(620, 100)),
                TextElement(
                    element_type=ElementType.TEXT, text="Overflow", size=(620, 700)
                ),
            )
        )

        # Manually create a "Positioned" slide that is guaranteed to overflow.
        text_element.position = (50, 50)
        text_element.size = (620, 800)  # This element overflows
        root_section = Section(
            id="root", position=(50, 50), size=(620, 800), children=[text_element]
        )

        title_element.position = (50, 10)
        title_element.size = (620, 30)

        slide = Slide(
            object_id="overflow_slide",
            elements=[title_element, text_element],
            renderable_elements=[title_element],
            root_section=root_section,
        )

        with patch("markdowndeck.layout.LayoutManager") as mock_lm_class:
            mock_lm_instance = MagicMock()

            # FIXED: Correctly simulate the layout manager's behavior for the continuation slide.
            def relayout(slide):
                if slide.is_continuation:
                    # Move meta-elements to renderable_elements
                    meta_elements = [
                        el
                        for el in slide.elements
                        if el.element_type == ElementType.TITLE
                    ]
                    for el in meta_elements:
                        el.position = (50, 50)
                        el.size = (620, 40)
                        slide.renderable_elements.append(el)
                if slide.root_section:
                    slide.root_section.position = (50, 100)
                return slide

            mock_lm_instance.calculate_positions.side_effect = relayout
            mock_lm_class.return_value = mock_lm_instance

            overflow_manager = OverflowManager()
            api_generator = ApiRequestGenerator()

            # Act
            final_slides = overflow_manager.process_slide(slide)
            assert (
                len(final_slides) > 1
            ), "Test setup failed: Overflow was not triggered."
            continuation_slide = final_slides[1]

            deck = Deck(slides=[continuation_slide])
            requests = api_generator.generate_batch_requests(deck, "pres_id")[0][
                "requests"
            ]

            title_element = continuation_slide.get_title_element()
            assert (
                title_element is not None
            ), "Continuation slide is missing its title element."
            title_id = title_element.object_id

            insert_text_req = next(
                (
                    r
                    for r in requests
                    if "insertText" in r and r["insertText"].get("objectId") == title_id
                ),
                None,
            )
            assert (
                insert_text_req is not None
            ), "Could not find insertText request for title."

            # Assert
            title_in_api_req = insert_text_req["insertText"]["text"]
            assert (
                "(continued) (continued)" not in title_in_api_req
            ), "The '(continued)' suffix must not be duplicated."
            assert (
                title_in_api_req.count("(continued)") == 1
            ), "The '(continued)' suffix should appear exactly once."
