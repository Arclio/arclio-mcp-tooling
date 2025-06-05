"""Unit tests for zone-based layout calculations with content-aware positioning."""

import pytest
from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.calculator.element_utils import mark_related_elements
from markdowndeck.layout.calculator.zone_layout import (
    _calculate_horizontal_position,
    calculate_zone_based_positions,
)
from markdowndeck.layout.constants import (
    VERTICAL_SPACING,
)
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Slide,
    TableElement,
    TextElement,
)


class TestZoneLayoutCalculations:
    """Test zone-based layout calculations."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_content_aware_element_sizing(self, calculator):
        """Test that elements are sized based on their content in zone layout."""

        # Create elements with different content characteristics
        short_text = TextElement(
            element_type=ElementType.TEXT, text="Short.", object_id="short"
        )

        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a much longer text element that contains substantially more content and should therefore require more vertical space when rendered. "
            * 2,
            object_id="long",
        )

        simple_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1"), ListItem(text="Item 2")],
            object_id="simple_list",
        )

        complex_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(
                    text=f"Complex item {i} with more detailed content that spans multiple words"
                )
                for i in range(1, 6)
            ],
            object_id="complex_list",
        )

        slide = Slide(
            object_id="sizing_test_slide",
            elements=[short_text, long_text, simple_list, complex_list],
        )

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        positioned_short = next(
            e for e in result_slide.elements if e.object_id == "short"
        )
        positioned_long = next(
            e for e in result_slide.elements if e.object_id == "long"
        )
        positioned_simple = next(
            e for e in result_slide.elements if e.object_id == "simple_list"
        )
        positioned_complex = next(
            e for e in result_slide.elements if e.object_id == "complex_list"
        )

        # Verify content-aware sizing
        assert (
            positioned_long.size[1] > positioned_short.size[1]
        ), "Longer text should be taller than shorter text"

        assert (
            positioned_complex.size[1] > positioned_simple.size[1]
        ), "Complex list should be taller than simple list"

        # All elements should have reasonable sizes
        for element in [
            positioned_short,
            positioned_long,
            positioned_simple,
            positioned_complex,
        ]:
            assert (
                element.size[0] > 0 and element.size[1] > 0
            ), "Elements should have positive dimensions"
            assert element.size[1] < 1000, "Element heights should be reasonable"

    def test_vertical_stacking_with_proper_spacing(self, calculator):
        """Test that elements are stacked vertically with appropriate spacing."""

        text1 = TextElement(
            element_type=ElementType.TEXT, text="First element", object_id="first"
        )
        text2 = TextElement(
            element_type=ElementType.TEXT, text="Second element", object_id="second"
        )
        text3 = TextElement(
            element_type=ElementType.TEXT, text="Third element", object_id="third"
        )

        slide = Slide(object_id="stacking_test_slide", elements=[text1, text2, text3])

        result_slide = calculate_zone_based_positions(calculator, slide)

        elements = [
            next(e for e in result_slide.elements if e.object_id == "first"),
            next(e for e in result_slide.elements if e.object_id == "second"),
            next(e for e in result_slide.elements if e.object_id == "third"),
        ]

        # Verify vertical stacking order
        for i in range(len(elements) - 1):
            current = elements[i]
            next_elem = elements[i + 1]

            assert (
                current.position[1] < next_elem.position[1]
            ), f"Element {i+1} should be below element {i}"

            # Check spacing
            current_bottom = current.position[1] + current.size[1]
            next_top = next_elem.position[1]
            spacing = next_top - current_bottom

            assert spacing >= 0, f"No overlap between elements {i} and {i+1}"
            assert spacing <= VERTICAL_SPACING * 2, "Spacing should be reasonable"

        # All elements should be in body zone
        for element in elements:
            assert (
                element.position[1] >= calculator.body_top
            ), "Element should be in body zone"

    def test_related_elements_marking(self, calculator):
        """Test that related elements are properly identified and marked."""

        # Create elements with relationships
        heading_text = TextElement(
            element_type=ElementType.TEXT,
            text="# This is a heading",
            object_id="heading",
        )

        follow_up_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Related item 1"), ListItem(text="Related item 2")],
            object_id="related_list",
        )

        image_element = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            object_id="test_image",
        )

        caption_text = TextElement(
            element_type=ElementType.TEXT, text="Image caption", object_id="caption"
        )

        unrelated_text = TextElement(
            element_type=ElementType.TEXT,
            text="Unrelated paragraph",
            object_id="unrelated",
        )

        elements = [
            heading_text,
            follow_up_list,
            image_element,
            caption_text,
            unrelated_text,
        ]

        # Test the marking function directly
        mark_related_elements(elements)

        # Verify relationships were detected
        assert (
            hasattr(heading_text, "related_to_next") and heading_text.related_to_next
        ), "Heading should be related to following list"
        assert (
            hasattr(follow_up_list, "related_to_prev")
            and follow_up_list.related_to_prev
        ), "List should be related to previous heading"

        assert (
            hasattr(image_element, "related_to_next") and image_element.related_to_next
        ), "Image should be related to following caption"
        assert (
            hasattr(caption_text, "related_to_prev") and caption_text.related_to_prev
        ), "Caption should be related to previous image"

    def test_related_elements_reduced_spacing(self, calculator):
        """Test that related elements get reduced spacing between them."""

        # Create a heading followed by a list (should be related)
        heading = TextElement(
            element_type=ElementType.TEXT,
            text="# Section Heading",
            object_id="section_heading",
            directives={"heading_level": 1},  # Add this line
        )

        related_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Related point 1"), ListItem(text="Related point 2")],
            object_id="related_list",
        )

        # Create unrelated elements for comparison
        unrelated_text1 = TextElement(
            element_type=ElementType.TEXT,
            text="Unrelated paragraph 1",
            object_id="unrelated1",
        )

        unrelated_text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Unrelated paragraph 2",
            object_id="unrelated2",
        )

        slide = Slide(
            object_id="spacing_test_slide",
            elements=[heading, related_list, unrelated_text1, unrelated_text2],
        )

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        pos_heading = next(
            e for e in result_slide.elements if e.object_id == "section_heading"
        )
        pos_related = next(
            e for e in result_slide.elements if e.object_id == "related_list"
        )
        pos_unrelated1 = next(
            e for e in result_slide.elements if e.object_id == "unrelated1"
        )
        pos_unrelated2 = next(
            e for e in result_slide.elements if e.object_id == "unrelated2"
        )

        # Calculate spacing between related elements
        related_spacing = pos_related.position[1] - (
            pos_heading.position[1] + pos_heading.size[1]
        )

        # Calculate spacing between unrelated elements
        unrelated_spacing = pos_unrelated2.position[1] - (
            pos_unrelated1.position[1] + pos_unrelated1.size[1]
        )

        # Related elements should have smaller spacing
        assert (
            related_spacing < unrelated_spacing
        ), f"Related elements should have reduced spacing: {related_spacing:.1f} vs {unrelated_spacing:.1f}"

    def test_horizontal_alignment_directives(self, calculator):
        """Test that horizontal alignment directives are respected in zone layout."""

        # Create elements with different alignments
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left aligned text",
            directives={"align": "left"},
            object_id="left_aligned",
        )

        center_text = TextElement(
            element_type=ElementType.TEXT,
            text="Center aligned text",
            directives={"align": "center"},
            object_id="center_aligned",
        )

        right_text = TextElement(
            element_type=ElementType.TEXT,
            text="Right aligned text",
            directives={"align": "right"},
            object_id="right_aligned",
        )

        slide = Slide(
            object_id="alignment_test_slide",
            elements=[left_text, center_text, right_text],
        )

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        pos_left = next(
            e for e in result_slide.elements if e.object_id == "left_aligned"
        )
        pos_center = next(
            e for e in result_slide.elements if e.object_id == "center_aligned"
        )
        pos_right = next(
            e for e in result_slide.elements if e.object_id == "right_aligned"
        )

        body_left = calculator.body_left
        body_width = calculator.body_width
        body_right = body_left + body_width

        # Verify alignments
        # Left alignment
        assert (
            abs(pos_left.position[0] - body_left) < 2
        ), f"Left-aligned element should be at body left: expected {body_left}, got {pos_left.position[0]}"

        # Center alignment
        element_center = pos_center.position[0] + pos_center.size[0] / 2
        body_center = body_left + body_width / 2
        assert (
            abs(element_center - body_center) < 5
        ), f"Center-aligned element should be centered in body: expected {body_center}, got {element_center}"

        # Right alignment
        element_right = pos_right.position[0] + pos_right.size[0]
        assert (
            abs(element_right - body_right) < 2
        ), f"Right-aligned element should end at body right: expected {body_right}, got {element_right}"

    def test_horizontal_position_calculation_function(self, calculator):
        """Test the horizontal position calculation function directly."""

        container_left = 100.0
        container_width = 400.0
        element_width = 200.0

        # Test left alignment
        left_element = TextElement(
            element_type=ElementType.TEXT, text="Test", directives={"align": "left"}
        )
        left_pos = _calculate_horizontal_position(
            left_element, container_left, container_width, element_width
        )
        assert (
            abs(left_pos - container_left) < 0.1
        ), "Left alignment should position at container left"

        # Test center alignment
        center_element = TextElement(
            element_type=ElementType.TEXT, text="Test", directives={"align": "center"}
        )
        center_pos = _calculate_horizontal_position(
            center_element, container_left, container_width, element_width
        )
        expected_center = container_left + (container_width - element_width) / 2
        assert (
            abs(center_pos - expected_center) < 0.1
        ), "Center alignment should center element"

        # Test right alignment
        right_element = TextElement(
            element_type=ElementType.TEXT, text="Test", directives={"align": "right"}
        )
        right_pos = _calculate_horizontal_position(
            right_element, container_left, container_width, element_width
        )
        expected_right = container_left + container_width - element_width
        assert (
            abs(right_pos - expected_right) < 0.1
        ), "Right alignment should position at container right"

    def test_element_width_calculations_in_zone_layout(self, calculator):
        """Test that element widths are calculated correctly in zone layout."""

        # Element with no width directive - should use body width
        full_width_text = TextElement(
            element_type=ElementType.TEXT,
            text="Full width text",
            object_id="full_width",
        )

        # Element with percentage width directive
        half_width_text = TextElement(
            element_type=ElementType.TEXT,
            text="Half width text",
            directives={"width": 0.5},
            object_id="half_width",
        )

        # Element with absolute width directive
        fixed_width_text = TextElement(
            element_type=ElementType.TEXT,
            text="Fixed width text",
            directives={"width": 300},
            object_id="fixed_width",
        )

        slide = Slide(
            object_id="width_test_slide",
            elements=[full_width_text, half_width_text, fixed_width_text],
        )

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        pos_full = next(e for e in result_slide.elements if e.object_id == "full_width")
        pos_half = next(e for e in result_slide.elements if e.object_id == "half_width")
        pos_fixed = next(
            e for e in result_slide.elements if e.object_id == "fixed_width"
        )

        body_width = calculator.body_width

        # Verify widths
        assert (
            abs(pos_full.size[0] - body_width) < 2
        ), f"Full width element should use body width: expected {body_width}, got {pos_full.size[0]}"

        expected_half_width = body_width * 0.5
        assert (
            abs(pos_half.size[0] - expected_half_width) < 2
        ), f"Half width element should be 50% of body: expected {expected_half_width}, got {pos_half.size[0]}"

        assert (
            abs(pos_fixed.size[0] - 300) < 2
        ), f"Fixed width element should be 300pt: got {pos_fixed.size[0]}"

    def test_mixed_element_types_in_zone_layout(self, calculator):
        """Test zone layout with a variety of element types."""

        title = TextElement(element_type=ElementType.TITLE, text="Mixed Elements Test")

        # Various element types
        text_elem = TextElement(
            element_type=ElementType.TEXT,
            text="Regular text paragraph with some content.",
            object_id="text",
        )

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"List item {i}") for i in range(1, 4)],
            object_id="list",
        )

        table_elem = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["R1C1", "R1C2"], ["R2C1", "R2C2"]],
            object_id="table",
        )

        code_elem = CodeElement(
            element_type=ElementType.CODE,
            code="def example():\n    return 'hello'",
            language="python",
            object_id="code",
        )

        image_elem = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            object_id="image",
        )

        footer = TextElement(element_type=ElementType.FOOTER, text="Test Footer")

        slide = Slide(
            object_id="mixed_elements_slide",
            elements=[
                title,
                text_elem,
                list_elem,
                table_elem,
                code_elem,
                image_elem,
                footer,
            ],
        )

        result_slide = calculator.calculate_positions(slide)

        # All elements should be positioned and sized
        for element in result_slide.elements:
            assert element.position is not None, "Element should be positioned"
            assert element.size is not None, "Element should be sized"
            assert (
                element.size[0] > 0 and element.size[1] > 0
            ), "Element should have positive dimensions"

        # Title should be in header zone
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        assert (
            positioned_title.position[1] < calculator.body_top
        ), "Title should be in header zone"

        # Footer should be in footer zone
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )
        assert (
            positioned_footer.position[1] >= calculator.footer_top
        ), "Footer should be in footer zone"

        # Body elements should be in body zone and stacked vertically
        body_elements = [
            next(e for e in result_slide.elements if e.object_id == "text"),
            next(e for e in result_slide.elements if e.object_id == "list"),
            next(e for e in result_slide.elements if e.object_id == "table"),
            next(e for e in result_slide.elements if e.object_id == "code"),
            next(e for e in result_slide.elements if e.object_id == "image"),
        ]

        for element in body_elements:
            assert (
                element.position[1] >= calculator.body_top
            ), "Body element should be in body zone"

        # Elements should be stacked vertically
        for i in range(len(body_elements) - 1):
            current = body_elements[i]
            next_elem = body_elements[i + 1]
            assert (
                current.position[1] < next_elem.position[1]
            ), "Elements should be stacked vertically"

    def test_empty_slide_zone_layout(self, calculator):
        """Test zone layout with empty slide."""

        empty_slide = Slide(object_id="empty_slide", elements=[])
        result_slide = calculate_zone_based_positions(calculator, empty_slide)

        assert result_slide.object_id == "empty_slide"
        assert len(result_slide.elements) == 0
        # Should not raise exceptions

    def test_slide_with_only_header_footer_zone_layout(self, calculator):
        """Test zone layout with only header and footer elements."""

        title = TextElement(element_type=ElementType.TITLE, text="Only Title")
        footer = TextElement(element_type=ElementType.FOOTER, text="Only Footer")

        slide = Slide(object_id="header_footer_only", elements=[title, footer])

        result_slide = calculator.calculate_positions(slide)

        # Both elements should be positioned correctly
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )

        assert (
            positioned_title.position[1] < calculator.body_top
        ), "Title should be in header zone"
        assert (
            positioned_footer.position[1] >= calculator.footer_top
        ), "Footer should be in footer zone"
