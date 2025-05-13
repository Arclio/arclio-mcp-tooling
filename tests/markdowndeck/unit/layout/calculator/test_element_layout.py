from copy import deepcopy

import pytest
from markdowndeck.layout.calculator import PositionCalculator
from markdowndeck.layout.calculator.element_layout import (
    position_footer_element,
    position_header_elements,
)
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    Slide,
    TextElement,
)


class TestElementLayout:
    """Unit tests for the element layout functions."""

    @pytest.fixture
    def default_margins(self) -> dict[str, float]:
        return {"top": 50, "right": 50, "bottom": 50, "left": 50}

    @pytest.fixture
    def calculator(self, default_margins: dict[str, float]) -> PositionCalculator:
        return PositionCalculator(
            slide_width=720, slide_height=405, margins=default_margins
        )

    def test_position_header_elements_title_only(self, calculator: PositionCalculator):
        """Test positioning of title element in the header zone."""
        title = TextElement(element_type=ElementType.TITLE, text="Test Title")
        slide = Slide(elements=[deepcopy(title)])

        position_header_elements(calculator, slide)

        # Get the positioned title
        positioned_title = next(
            e for e in slide.elements if e.element_type == ElementType.TITLE
        )

        # Should have a position and size
        assert positioned_title.position is not None
        assert positioned_title.size is not None

        # Title should be positioned at expected y coordinate
        expected_y = (
            calculator.margins["top"] + 20
        )  # From element_layout.py implementation
        assert positioned_title.position[1] == pytest.approx(expected_y)

        # Title should be centered horizontally
        title_width = positioned_title.size[0]
        expected_x = (
            calculator.margins["left"]
            + (calculator.max_content_width - title_width) / 2
        )
        assert positioned_title.position[0] == pytest.approx(expected_x)

    def test_position_header_elements_title_and_subtitle(
        self, calculator: PositionCalculator
    ):
        """Test positioning of title and subtitle elements in the header zone."""
        title = TextElement(element_type=ElementType.TITLE, text="Test Title")
        subtitle = TextElement(element_type=ElementType.SUBTITLE, text="Test Subtitle")
        slide = Slide(elements=[deepcopy(title), deepcopy(subtitle)])

        position_header_elements(calculator, slide)

        # Get the positioned elements
        positioned_title = next(
            e for e in slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_subtitle = next(
            e for e in slide.elements if e.element_type == ElementType.SUBTITLE
        )

        # Both should have positions and sizes
        assert positioned_title.position is not None
        assert positioned_title.size is not None
        assert positioned_subtitle.position is not None
        assert positioned_subtitle.size is not None

        # Title should be at expected y coordinate
        title_y = calculator.margins["top"] + 20
        assert positioned_title.position[1] == pytest.approx(title_y)

        # Subtitle should be below title
        subtitle_y = (
            title_y + positioned_title.size[1] + 10
        )  # 10 is spacing from implementation
        assert positioned_subtitle.position[1] == pytest.approx(subtitle_y)

        # Both should be centered horizontally
        title_x = (
            calculator.margins["left"]
            + (calculator.max_content_width - positioned_title.size[0]) / 2
        )
        subtitle_x = (
            calculator.margins["left"]
            + (calculator.max_content_width - positioned_subtitle.size[0]) / 2
        )

        assert positioned_title.position[0] == pytest.approx(title_x)
        assert positioned_subtitle.position[0] == pytest.approx(subtitle_x)

    def test_position_header_elements_subtitle_only(
        self, calculator: PositionCalculator
    ):
        """Test positioning of subtitle element when no title is present."""
        subtitle = TextElement(element_type=ElementType.SUBTITLE, text="Only Subtitle")
        slide = Slide(elements=[deepcopy(subtitle)])

        position_header_elements(calculator, slide)

        # Get the positioned subtitle
        positioned_subtitle = next(
            e for e in slide.elements if e.element_type == ElementType.SUBTITLE
        )

        # Should have a position and size
        assert positioned_subtitle.position is not None
        assert positioned_subtitle.size is not None

        # Subtitle should be positioned at expected y coordinate when no title
        expected_y = (
            calculator.margins["top"] + 30
        )  # From element_layout.py implementation
        assert positioned_subtitle.position[1] == pytest.approx(expected_y)

        # Subtitle should be centered horizontally
        subtitle_width = positioned_subtitle.size[0]
        expected_x = (
            calculator.margins["left"]
            + (calculator.max_content_width - subtitle_width) / 2
        )
        assert positioned_subtitle.position[0] == pytest.approx(expected_x)

    def test_position_footer_element_default_alignment(
        self, calculator: PositionCalculator
    ):
        """Test positioning of footer element with default (center) alignment."""
        footer = TextElement(element_type=ElementType.FOOTER, text="Test Footer")
        slide = Slide(elements=[deepcopy(footer)])

        position_footer_element(calculator, slide)

        # Get the positioned footer
        positioned_footer = next(
            e for e in slide.elements if e.element_type == ElementType.FOOTER
        )

        # Should have a position and size
        assert positioned_footer.position is not None
        assert positioned_footer.size is not None

        # Footer should be at the bottom of the slide
        expected_y = (
            calculator.slide_height
            - calculator.margins["bottom"]
            - positioned_footer.size[1]
        )
        assert positioned_footer.position[1] == pytest.approx(expected_y)

        # Default alignment is center, so x position should be at left margin
        assert positioned_footer.position[0] == calculator.margins["left"]

    def test_position_footer_element_with_alignments(
        self, calculator: PositionCalculator
    ):
        """Test positioning of footer with different alignments."""
        # Test left alignment
        footer_left = TextElement(
            element_type=ElementType.FOOTER,
            text="Left Footer",
            horizontal_alignment=AlignmentType.LEFT,
        )
        slide_left = Slide(elements=[deepcopy(footer_left)])
        position_footer_element(calculator, slide_left)
        positioned_left = next(
            e for e in slide_left.elements if e.element_type == ElementType.FOOTER
        )
        assert positioned_left.position[0] == calculator.margins["left"]

        # Test right alignment
        footer_right = TextElement(
            element_type=ElementType.FOOTER,
            text="Right Footer",
            horizontal_alignment=AlignmentType.RIGHT,
        )
        slide_right = Slide(elements=[deepcopy(footer_right)])
        position_footer_element(calculator, slide_right)
        positioned_right = next(
            e for e in slide_right.elements if e.element_type == ElementType.FOOTER
        )
        expected_right_x = (
            calculator.slide_width
            - calculator.margins["right"]
            - positioned_right.size[0]
        )
        assert positioned_right.position[0] == pytest.approx(expected_right_x)

        # All footers should be at same y position
        expected_y = (
            calculator.slide_height
            - calculator.margins["bottom"]
            - positioned_left.size[1]
        )
        assert positioned_left.position[1] == pytest.approx(expected_y)
        assert positioned_right.position[1] == pytest.approx(expected_y)
