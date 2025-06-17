import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    CodeElement,
    Deck,
    ElementType,
    ListElement,
    ListItem,
    Slide,
    TableElement,
    TextElement,
)


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    """Provides a fresh ApiRequestGenerator instance for each test."""
    return ApiRequestGenerator()


def _get_paragraph_style_request(requests: list, object_id: str) -> dict | None:
    """Helper to find the updateParagraphStyle request for a given object ID."""
    return next(
        (
            r["updateParagraphStyle"]
            for r in requests
            if "updateParagraphStyle" in r
            and r["updateParagraphStyle"]["objectId"] == object_id
        ),
        None,
    )


def _get_table_cell_properties_request(
    requests: list, object_id: str, row_index: int
) -> dict | None:
    """Helper to find the updateTableCellProperties request for a given object ID and row."""
    return next(
        (
            r["updateTableCellProperties"]
            for r in requests
            if "updateTableCellProperties" in r
            and r["updateTableCellProperties"]["objectId"] == object_id
            and r["updateTableCellProperties"]["tableRange"]["location"]["rowIndex"]
            == row_index
        ),
        None,
    )


class TestApiGeneratorBugReproduction:
    """Tests designed to fail, exposing known bugs in the API request generation."""

    def test_bug_nested_list_indentation_incorrect(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-BUG-01
        Description: Exposes the bug where nested list items are not correctly indented.
        Expected to Fail: No. After fix, this should pass.
        """
        # Arrange
        nested_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            object_id="nested_list_1",
            position=(50, 50),
            size=(400, 200),
            items=[
                ListItem(
                    text="Level 0 Item",
                    level=0,
                    children=[ListItem(text="Level 1 Item", level=1)],
                )
            ],
        )
        slide = Slide(object_id="s1", renderable_elements=[nested_list])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Find the specific indentation request
        indent_request = next(
            (
                r["updateParagraphStyle"]
                for r in requests
                if "updateParagraphStyle" in r
                and r["updateParagraphStyle"]["objectId"] == "nested_list_1"
                and "indentStart" in r["updateParagraphStyle"]["style"]
            ),
            None,
        )

        # Assert
        assert (
            indent_request is not None
        ), "An updateParagraphStyle request with indentation should exist for the nested item."
        assert (
            "indentStart" in indent_request["style"]
        ), "The paragraph style must include an indentStart property for sub-lists."
        assert (
            indent_request["style"]["indentStart"]["magnitude"] > 0
        ), "Indent magnitude for a nested list must be greater than 0."

    def test_bug_table_row_directives_not_applied(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-BUG-02
        Description: Exposes the bug where table row directives are not being translated
                     into API requests for cell styling.
        Expected to Fail: No. This test was already passing as the logic was implemented.
        """
        # Arrange
        table = TableElement(
            element_type=ElementType.TABLE,
            object_id="table_style_bug",
            position=(50, 50),
            size=(400, 200),
            headers=["H1", "H2"],
            rows=[["R1", "R1"]],
            row_directives=[
                {},  # Header row directive
                {"background": "#FFFF00"},  # First data row directive (yellow)
            ],
        )
        slide = Slide(object_id="s1", renderable_elements=[table])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # We check the properties for the first data row, which is at index 1 (0 is header).
        cell_props_req = _get_table_cell_properties_request(
            requests, "table_style_bug", row_index=1
        )

        # Assert
        assert (
            cell_props_req is not None
        ), "updateTableCellProperties request for the styled row is missing."
        assert (
            "tableCellBackgroundFill" in cell_props_req["tableCellProperties"]
        ), "Background fill property is missing from the request."
        fill_color = cell_props_req["tableCellProperties"]["tableCellBackgroundFill"][
            "solidFill"
        ]["color"]
        assert "rgbColor" in fill_color, "A fill color was not applied."
        # Check for yellow
        assert abs(fill_color["rgbColor"]["red"] - 1.0) < 0.01
        assert abs(fill_color["rgbColor"]["green"] - 1.0) < 0.01

    def test_bug_nested_list_indentation_visual_alignment(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-BUG-04
        Description: Tests that nested list items have proper hanging indent with both
                     indentStart (to indent the whole line) and indentFirstLine (negative
                     value to outdent the bullet back to the left).
        Expected to Fail: Initially yes, should pass after fix.
        """
        from markdowndeck.parser import Parser

        # Arrange - Parse nested list markdown
        parser = Parser()
        # FIXED: Wrapped list content in a :::section block to be Grammar V2.0 compliant.
        markdown = ":::section\n- L1\n  - L2\n:::"
        deck = parser.parse(markdown)

        # CRITICAL FIX: Need to run layout manager to populate renderable_elements
        from markdowndeck.layout import LayoutManager

        layout_manager = LayoutManager()
        positioned_slide = layout_manager.calculate_positions(deck.slides[0])

        # CRITICAL FIX: Need to run overflow manager to finalize and move elements to renderable_elements
        from markdowndeck.overflow import OverflowManager

        overflow_manager = OverflowManager()
        finalized_slides = overflow_manager.process_slide(positioned_slide)

        # Update the deck with the finalized slide
        deck.slides = finalized_slides

        # Act - Generate API requests
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Find the updateParagraphStyle request for the nested item (L2)
        # The nested item will have level=1 and should have both indent properties
        nested_indent_request = None
        for r in requests:
            if "updateParagraphStyle" in r and "indentStart" in r.get(
                "updateParagraphStyle", {}
            ).get("style", {}):
                nested_indent_request = r["updateParagraphStyle"]
                break

        # Assert
        assert (
            nested_indent_request is not None
        ), "updateParagraphStyle request with indentStart should exist for nested item"

        style = nested_indent_request["style"]
        assert (
            "indentStart" in style
        ), "indentStart property must be present for nested items"
        assert (
            "indentFirstLine" in style
        ), "indentFirstLine property must be present for proper hanging indent"

        # Check values
        assert (
            style["indentStart"]["magnitude"] == 20.0
        ), "indentStart should be 20.0 PT for level 1"
        assert style["indentStart"]["unit"] == "PT", "indentStart unit should be PT"
        assert (
            style["indentFirstLine"]["magnitude"] == -20.0
        ), "indentFirstLine should be -20.0 PT to create hanging indent"
        assert (
            style["indentFirstLine"]["unit"] == "PT"
        ), "indentFirstLine unit should be PT"

        # Check fields mask includes both properties
        fields = nested_indent_request["fields"]
        assert "indentStart" in fields, "fields mask must include indentStart"
        assert "indentFirstLine" in fields, "fields mask must include indentFirstLine"

    def test_bug_code_label_position_with_heading(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: LAYOUT-BUG-02 / API-BUG-03
        Description: Checks that the CodeRequestBuilder correctly offsets the language label
                     when the code block is preceded by another element.
        Expected to Fail: No. The test was flawed. After fix, this should pass.
        """
        # Arrange
        heading = TextElement(
            element_type=ElementType.TEXT,
            text="Python Code Example",
            object_id="h1",
            position=(50, 50),
            size=(620, 30),
        )
        # FIXED: Instantiated CodeElement instead of TextElement to trigger the correct builder.
        code_element = CodeElement(
            element_type=ElementType.CODE,
            code="print('hello')",
            language="python",
            object_id="c1",
            position=(50, 90),
            size=(620, 50),
            directives={"language": "python"},
        )
        slide = Slide(object_id="s1", renderable_elements=[heading, code_element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Find the language label shape request
        label_shape_req = next(
            (
                r
                for r in requests
                if "createShape" in r
                and r["createShape"]["objectId"].endswith("_label")
            ),
            None,
        )

        # Assert
        assert label_shape_req is not None, "Language label shape was not created."

        label_y_pos = label_shape_req["createShape"]["elementProperties"]["transform"][
            "translateY"
        ]
        code_block_y_pos = code_element.position[1]
        label_height = 20  # from code_builder.py

        # The label should be positioned *above* the code block's Y position.
        assert (
            label_y_pos < code_block_y_pos
        ), f"Code label Y position ({label_y_pos}) should be less than the code block's Y position ({code_block_y_pos})."
        assert (
            abs(label_y_pos - (code_block_y_pos - label_height)) < 5.0
        ), "Code label is not positioned correctly above the code block."
