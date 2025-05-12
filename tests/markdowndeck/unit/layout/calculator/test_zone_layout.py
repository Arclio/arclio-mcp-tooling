from copy import deepcopy

import pytest
from markdowndeck.layout.calculator import PositionCalculator
from markdowndeck.layout.calculator.zone_layout import calculate_zone_based_positions
from markdowndeck.layout.constants import BODY_TOP_ADJUSTMENT
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    Slide,
    TextElement,
)


class TestZoneLayout:
    """Unit tests for the zone-based layout calculator."""

    @pytest.fixture
    def default_margins(self) -> dict[str, float]:
        return {"top": 50, "right": 50, "bottom": 50, "left": 50}

    @pytest.fixture
    def calculator(self, default_margins: dict[str, float]) -> PositionCalculator:
        return PositionCalculator(slide_width=720, slide_height=405, margins=default_margins)

    def test_calculate_zone_based_positions_title_only(self, calculator: PositionCalculator):
        """Test that a slide with only a title is positioned correctly."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        slide = Slide(elements=[deepcopy(title)])

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Title should be positioned within header zone
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        assert positioned_title.position is not None
        assert positioned_title.position[1] == pytest.approx(calculator.margins["top"] + 20)
        # Title should be horizontally centered
        assert positioned_title.position[0] == pytest.approx(
            calculator.margins["left"]
            + (calculator.max_content_width - positioned_title.size[0]) / 2
        )

    def test_calculate_zone_based_positions_body_elements(self, calculator: PositionCalculator):
        """Test that body elements are positioned correctly within the body zone."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        text1 = TextElement(element_type=ElementType.TEXT, text="Body text 1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Body text 2")
        slide = Slide(elements=[deepcopy(title), deepcopy(text1), deepcopy(text2)])

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Get the positioned body elements
        body_elements = [e for e in result_slide.elements if e.element_type == ElementType.TEXT]
        assert len(body_elements) == 2

        # Body elements should be within body zone, accounting for BODY_TOP_ADJUSTMENT
        for element in body_elements:
            assert element.position[0] >= calculator.body_left
            # Updated assertion to account for BODY_TOP_ADJUSTMENT
            assert element.position[1] >= calculator.body_top - BODY_TOP_ADJUSTMENT
            assert (element.position[0] + element.size[0]) <= (
                calculator.body_left + calculator.body_width
            )

        # Elements should be stacked vertically
        assert body_elements[0].position[1] < body_elements[1].position[1]

    def test_calculate_zone_based_positions_with_footer(self, calculator: PositionCalculator):
        """Test that a slide with a footer positions the footer correctly."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        text = TextElement(element_type=ElementType.TEXT, text="Body text")
        footer = TextElement(element_type=ElementType.FOOTER, text="Footer")
        slide = Slide(elements=[deepcopy(title), deepcopy(text), deepcopy(footer)])

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Footer should be at the bottom of the slide
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )
        assert positioned_footer.position is not None

        # Footer should be at the bottom - margins - footer height
        expected_footer_y = (
            calculator.slide_height - calculator.margins["bottom"] - positioned_footer.size[1]
        )
        assert positioned_footer.position[1] == pytest.approx(expected_footer_y)

    def test_calculate_zone_based_positions_element_alignment(self, calculator: PositionCalculator):
        """Test that elements with different alignments are positioned correctly."""
        # Create elements with different alignments
        text_left = TextElement(
            element_type=ElementType.TEXT,
            text="Left aligned",
            horizontal_alignment=AlignmentType.LEFT,
        )
        text_center = TextElement(
            element_type=ElementType.TEXT,
            text="Center aligned",
            horizontal_alignment=AlignmentType.CENTER,
        )
        text_right = TextElement(
            element_type=ElementType.TEXT,
            text="Right aligned",
            horizontal_alignment=AlignmentType.RIGHT,
        )

        slide = Slide(elements=[deepcopy(text_left), deepcopy(text_center), deepcopy(text_right)])

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        positioned_elements = result_slide.elements

        # Verify left alignment
        left_element = next(e for e in positioned_elements if e.text == "Left aligned")
        assert left_element.position[0] == calculator.body_left

        # Verify center alignment
        center_element = next(e for e in positioned_elements if e.text == "Center aligned")
        center_x = calculator.body_left + (calculator.body_width - center_element.size[0]) / 2
        assert center_element.position[0] == pytest.approx(center_x)

        # Verify right alignment
        right_element = next(e for e in positioned_elements if e.text == "Right aligned")
        right_x = calculator.body_left + calculator.body_width - right_element.size[0]
        assert right_element.position[0] == pytest.approx(right_x)

    def test_calculate_zone_based_positions_element_width_directive(
        self, calculator: PositionCalculator
    ):
        """Test that elements with width directives have correct sizes."""
        # Create elements with width directives
        text_full = TextElement(element_type=ElementType.TEXT, text="Full width")
        text_half = TextElement(
            element_type=ElementType.TEXT, text="Half width", directives={"width": 0.5}
        )
        text_fixed = TextElement(
            element_type=ElementType.TEXT, text="Fixed width", directives={"width": 200}
        )

        slide = Slide(elements=[deepcopy(text_full), deepcopy(text_half), deepcopy(text_fixed)])

        result_slide = calculate_zone_based_positions(calculator, slide)

        # Extract positioned elements
        positioned_elements = result_slide.elements

        # Verify full width element (default)
        full_element = next(e for e in positioned_elements if e.text == "Full width")
        assert full_element.size[0] == calculator.body_width

        # Verify half width element
        half_element = next(e for e in positioned_elements if e.text == "Half width")
        assert half_element.size[0] == pytest.approx(calculator.body_width * 0.5)

        # Verify fixed width element
        fixed_element = next(e for e in positioned_elements if e.text == "Fixed width")
        assert fixed_element.size[0] == 200
