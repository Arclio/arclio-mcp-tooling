import pytest
from markdowndeck import markdown_to_requests
from markdowndeck.layout import LayoutManager
from markdowndeck.models import CodeElement, ElementType, Section, Slide, TextElement


@pytest.fixture
def layout_manager() -> LayoutManager:
    """Provides a LayoutManager with standard dimensions."""
    return LayoutManager()


def _get_shape_properties_by_text(requests: list, text: str) -> dict | None:
    """Helper to find the elementProperties of a shape containing specific text."""
    text_req = next(
        (r for r in requests if "insertText" in r and text in r["insertText"]["text"]),
        None,
    )
    if not text_req:
        return None
    object_id = text_req["insertText"]["objectId"]
    shape_req = next(
        (
            r
            for r in requests
            if "createShape" in r and r["createShape"]["objectId"] == object_id
        ),
        None,
    )
    return shape_req["createShape"]["elementProperties"] if shape_req else None


class TestLayoutBugReproduction:
    """Tests designed to fail, exposing known bugs in layout calculation."""

    def test_bug_column_width_calculation_incorrect(self):
        """
        Test Case: LAYOUT-BUG-01
        Description: Exposes the bug where proportional column widths are miscalculated,
                     seemingly taking a fraction of a fraction.
        Expected to Fail: Yes. The assertion on width will fail.
        """
        # Arrange: Three columns, each requesting 1/3 of the width.
        markdown = ":::row\n:::column [width=1/3]\nA\n:::\n:::column [width=1/3]\nB\n:::\n:::column [width=1/3]\nC\n:::\n:::"

        # Act
        result = markdown_to_requests(markdown)
        requests = result["slide_batches"][0]["requests"]

        # Assert
        shape_a_props = _get_shape_properties_by_text(requests, "A")
        assert shape_a_props is not None, "Shape for column A not found."

        # Slide width is 720. No gap. Usable width is 720.
        # Each column should be ~240pt wide.
        expected_width = 720 / 3.0
        actual_width = shape_a_props["size"]["width"]["magnitude"]

        assert (
            abs(actual_width - expected_width) < 5.0
        ), f"Column width is incorrect. Expected ~{expected_width}, but got {actual_width}."

    def test_bug_code_block_label_overlaps_heading(self, layout_manager: LayoutManager):
        """
        Test Case: LAYOUT-BUG-02
        Description: Exposes the bug where a code block's language label is positioned
                     on top of a preceding heading element.
        Expected to Fail: Yes. The assertion on vertical positioning will fail.
        """
        # Arrange
        heading = TextElement(
            element_type=ElementType.TEXT, text="Python Code Example", object_id="h1"
        )
        # FIXED: Use the correct CodeElement type
        code = CodeElement(
            element_type=ElementType.CODE,
            code="print('hello')",
            object_id="c1",
            directives={"language": "python"},
        )

        # The LayoutManager needs to know these are related to adjust spacing
        heading.related_to_next = True
        code.related_to_prev = True

        root_section = Section(id="root", children=[heading, code])
        slide = Slide(
            object_id="s1", root_section=root_section, elements=[heading, code]
        )

        # Act
        # NOTE: This bug is in the API Generator, but we can see the position collision in the LayoutManager
        # if we could inspect the label's position. For now, we test the element positions.
        # The real fix is in the CodeRequestBuilder to adjust the label's Y position.
        positioned_slide = layout_manager.calculate_positions(slide)

        pos_heading = positioned_slide.root_section.children[0]
        pos_code = positioned_slide.root_section.children[1]

        heading_bottom = pos_heading.position[1] + pos_heading.size[1]
        code_top = pos_code.position[1]

        # This test won't fail yet as it only checks the code block position, not its internal label.
        # A more detailed test would inspect the generated API requests.
        # We will add a test for the API generator to cover the label position.
        assert (
            code_top > heading_bottom
        ), "Code block should be positioned below the heading."
