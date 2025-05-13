import pytest
from markdowndeck.layout.calculator.element_utils import (
    adjust_vertical_spacing,
    apply_horizontal_alignment,
    mark_related_elements,
)
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    TextElement,
)


class TestElementUtils:
    """Unit tests for element utility functions."""

    def test_apply_horizontal_alignment_left(self):
        """Test applying left horizontal alignment to an element."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Test Text",
            size=(100, 30),
            horizontal_alignment=AlignmentType.LEFT,
        )

        area_x = 50
        area_width = 600
        y_pos = 100

        apply_horizontal_alignment(element, area_x, area_width, y_pos)

        # Left aligned element should start at area_x
        assert element.position == (area_x, y_pos)

    def test_apply_horizontal_alignment_center(self):
        """Test applying center horizontal alignment to an element."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Test Text",
            size=(100, 30),
            horizontal_alignment=AlignmentType.CENTER,
        )

        area_x = 50
        area_width = 600
        y_pos = 100

        apply_horizontal_alignment(element, area_x, area_width, y_pos)

        # Center aligned element should be centered in area
        expected_x = area_x + (area_width - element.size[0]) / 2
        assert element.position[0] == pytest.approx(expected_x)
        assert element.position[1] == y_pos

    def test_apply_horizontal_alignment_right(self):
        """Test applying right horizontal alignment to an element."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Test Text",
            size=(100, 30),
            horizontal_alignment=AlignmentType.RIGHT,
        )

        area_x = 50
        area_width = 600
        y_pos = 100

        apply_horizontal_alignment(element, area_x, area_width, y_pos)

        # Right aligned element should end at area_x + area_width
        expected_x = area_x + area_width - element.size[0]
        assert element.position[0] == pytest.approx(expected_x)
        assert element.position[1] == y_pos

    def test_mark_related_elements(self):
        """Test marking related elements in a sequence."""
        # Create a heading followed by a list - these should be marked as related
        heading = TextElement(
            element_type=ElementType.TEXT,
            text="Heading",
            directives={"level": 3},  # This marks it as a heading
        )

        list_elem = TextElement(element_type=ElementType.BULLET_LIST, text="List Item")

        regular_text = TextElement(element_type=ElementType.TEXT, text="Regular Text")

        elements = [heading, list_elem, regular_text]

        mark_related_elements(elements)

        # The list should be marked as related to the previous heading
        assert hasattr(list_elem, "related_to_prev")
        assert list_elem.related_to_prev

        # The regular text should not be marked as related
        assert not (
            hasattr(regular_text, "related_to_prev") and regular_text.related_to_prev
        )

        # The heading (first element) should not be marked as related
        assert not (hasattr(heading, "related_to_prev") and heading.related_to_prev)

    def test_adjust_vertical_spacing_for_related_elements(self):
        """Test adjusting vertical spacing for related elements."""
        # Create a related element with related_to_next flag (which is what the current implementation checks)
        element = TextElement(element_type=ElementType.BULLET_LIST, text="List Item")
        element.related_to_next = True  # Current implementation uses this flag

        # Standard spacing is usually 20
        standard_spacing = 20

        adjusted_spacing = adjust_vertical_spacing(element, standard_spacing)

        # Spacing should be reduced for elements with related_to_next flag
        assert adjusted_spacing < standard_spacing
        # Check if it's around 70% of standard (common reduction would be 30%)
        assert adjusted_spacing == pytest.approx(standard_spacing * 0.7, abs=2)

    def test_adjust_vertical_spacing_for_related_to_prev_elements(self):
        """Test adjusting vertical spacing for elements with related_to_prev flag."""
        # Create an element with related_to_prev flag
        element = TextElement(element_type=ElementType.BULLET_LIST, text="List Item")
        element.related_to_prev = True

        # Standard spacing is usually 20
        standard_spacing = 20

        adjusted_spacing = adjust_vertical_spacing(element, standard_spacing)

        # With current implementation, related_to_prev doesn't affect spacing adjustment
        assert adjusted_spacing == standard_spacing

    def test_adjust_vertical_spacing_for_regular_elements(self):
        """Test adjusting vertical spacing for regular elements."""
        # Create a regular element
        element = TextElement(element_type=ElementType.TEXT, text="Regular Text")

        # Standard spacing is usually 20
        standard_spacing = 20

        adjusted_spacing = adjust_vertical_spacing(element, standard_spacing)

        # Spacing should remain the same for regular elements
        assert adjusted_spacing == standard_spacing

    def test_heading_followed_by_multiple_content_items(self):
        """Test marking multiple content items as related to a heading."""
        # Create a heading followed by multiple content items
        heading = TextElement(
            element_type=ElementType.TEXT,
            text="Heading",
            directives={"level": 2},  # This marks it as a heading
        )

        list_item = TextElement(element_type=ElementType.BULLET_LIST, text="List Item")
        code_block = TextElement(element_type=ElementType.CODE, text="Code Block")
        regular_text = TextElement(element_type=ElementType.TEXT, text="Regular Text")

        # Arrange elements with heading followed by related content
        elements = [heading, list_item, code_block, regular_text]

        # Mark related elements
        mark_related_elements(elements)

        # In the current implementation, only list items are related to headings
        # Code blocks and regular text aren't marked as related
        assert hasattr(list_item, "related_to_prev")
        assert list_item.related_to_prev is True
        assert (
            not hasattr(code_block, "related_to_prev") or not code_block.related_to_prev
        )
        assert (
            not hasattr(regular_text, "related_to_prev")
            or not regular_text.related_to_prev
        )
