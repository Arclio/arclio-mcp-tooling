import pytest
from markdowndeck.layout.calculator import PositionCalculator
from markdowndeck.layout.constants import BODY_TOP_ADJUSTMENT
from markdowndeck.models import (
    ElementType,
    Section,
    Slide,
    TextElement,
)


class TestBaseCalculator:
    """Tests for the base calculator module functionality."""

    @pytest.fixture
    def default_margins(self) -> dict[str, float]:
        return {"top": 50, "right": 50, "bottom": 50, "left": 50}

    @pytest.fixture
    def calculator(self, default_margins: dict[str, float]) -> PositionCalculator:
        return PositionCalculator(slide_width=720, slide_height=405, margins=default_margins)

    def test_basic_slide_initialization(self, calculator: PositionCalculator):
        """Test basic attributes of a newly created PositionCalculator."""
        assert calculator.slide_width == 720
        assert calculator.slide_height == 405

        # Check margins
        assert calculator.margins["top"] == 50
        assert calculator.margins["right"] == 50
        assert calculator.margins["bottom"] == 50
        assert calculator.margins["left"] == 50

        # Check derived attributes
        assert calculator.max_content_width == 720 - 50 - 50  # slide_width - left - right
        assert calculator.max_content_height == 405 - 50 - 50  # slide_height - top - bottom

        # Check body zone calculation
        assert calculator.body_left == 50  # left margin
        assert (
            calculator.body_top > 50
        )  # Should be greater than top margin to account for title area
        assert calculator.body_width == calculator.max_content_width
        # Body height should be less than max_content_height to account for header/footer
        assert calculator.body_height < calculator.max_content_height

    def test_calculate_positions_zone_based(self, calculator: PositionCalculator):
        """Test that calculate_positions correctly handles zone-based layout."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        text = TextElement(element_type=ElementType.TEXT, text="Text")
        slide = Slide(
            elements=[title, text],
            # No sections, so it will use zone-based layout
        )

        result_slide = calculator.calculate_positions(slide)

        # Ensure all elements have positions
        for element in result_slide.elements:
            assert element.position is not None
            assert element.size is not None

        # Title should be in the header zone
        title_element = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        assert (
            title_element.position[1] < calculator.body_top
        )  # Title Y position should be above body_top

        # Text should be in the body zone, accounting for BODY_TOP_ADJUSTMENT
        text_element = next(e for e in result_slide.elements if e.element_type == ElementType.TEXT)
        assert (
            text_element.position[1] >= calculator.body_top - BODY_TOP_ADJUSTMENT
        )  # Text Y position should be at or below adjusted body_top

    def test_calculate_positions_section_based(self, calculator: PositionCalculator):
        """Test that calculate_positions correctly handles section-based layout."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        text1 = TextElement(element_type=ElementType.TEXT, text="Left Column")
        text2 = TextElement(element_type=ElementType.TEXT, text="Right Column")

        # Create sections for a side-by-side layout
        section1 = Section(id="s1", directives={"width": 0.5})
        section2 = Section(id="s2", directives={"width": 0.5})

        # Assign elements to sections
        section1.elements = [text1]
        section2.elements = [text2]

        slide = Slide(
            elements=[title, text1, text2],
            sections=[section1, section2],
            # Having sections triggers section-based layout
        )

        result_slide = calculator.calculate_positions(slide)

        # Check that sections have positions and sizes
        assert len(result_slide.sections) == 2
        for section in result_slide.sections:
            assert section.position is not None
            assert section.size is not None

        # Sections should be side by side (horizontally arranged)
        section1 = result_slide.sections[0]
        section2 = result_slide.sections[1]
        assert section1.position[0] < section2.position[0]
        assert section1.position[1] == section2.position[1]  # Same vertical start

        # Elements should be positioned within their sections
        text1_elem = section1.elements[0]
        text2_elem = section2.elements[0]

        assert text1_elem.position[0] >= section1.position[0]
        assert (
            text1_elem.position[0] + text1_elem.size[0] <= section1.position[0] + section1.size[0]
        )

        assert text2_elem.position[0] >= section2.position[0]
        assert (
            text2_elem.position[0] + text2_elem.size[0] <= section2.position[0] + section2.size[0]
        )

        # Title should still be in header zone
        title_element = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        assert title_element.position[1] < calculator.body_top

    def test_calculate_positions_auto_layout_detection(self, calculator: PositionCalculator):
        """Test that calculate_positions correctly auto-detects layout type."""
        title = TextElement(element_type=ElementType.TITLE, text="Title")
        text1 = TextElement(element_type=ElementType.TEXT, text="Left Column")
        text2 = TextElement(element_type=ElementType.TEXT, text="Right Column")

        # Create a slide with sections but no explicit layout_type
        section1 = Section(id="s1", directives={"width": 0.5})
        section2 = Section(id="s2", directives={"width": 0.5})

        section1.elements = [text1]
        section2.elements = [text2]

        slide = Slide(
            elements=[title, text1, text2],
            sections=[section1, section2],
            # No layout_type specified - should auto-detect as section-based
        )

        result_slide = calculator.calculate_positions(slide)

        # Check that sections have positions
        assert len(result_slide.sections) == 2
        for section in result_slide.sections:
            assert section.position is not None
            assert section.size is not None

        # Similarly, create a slide with no sections and no layout_type
        slide_zone = Slide(
            elements=[title, text1, text2],
            # No sections, no layout_type - should default to zone-based
        )

        result_slide_zone = calculator.calculate_positions(slide_zone)

        # All elements should still be positioned
        for element in result_slide_zone.elements:
            assert element.position is not None
            assert element.size is not None

        # Elements should be stacked vertically in zone-based layout
        elements = [e for e in result_slide_zone.elements if e.element_type == ElementType.TEXT]
        assert elements[0].position[1] < elements[1].position[1]

    def test_calculate_positions_empty_slide(self, calculator: PositionCalculator):
        slide = Slide(elements=[])
        result_slide = calculator.calculate_positions(slide)
        assert len(result_slide.elements) == 0  # No elements to position

    def test_calculate_positions_slide_with_only_footer(self, calculator: PositionCalculator):
        footer = TextElement(element_type=ElementType.FOOTER, text="Footer only")
        slide = Slide(elements=[footer])
        result_slide = calculator.calculate_positions(slide)
        assert len(result_slide.elements) == 1
        positioned_footer = result_slide.elements[0]
        assert positioned_footer.position is not None
        assert positioned_footer.size is not None
        # Check it's at the bottom
        expected_y = (
            calculator.slide_height - calculator.margins["bottom"] - positioned_footer.size[1]
        )
        assert positioned_footer.position[1] == pytest.approx(expected_y)
