"""Unit tests for the refactored content-aware base position calculator."""

import pytest
from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.constants import (
    BODY_TO_FOOTER_SPACING,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_SLIDE_HEIGHT,
    DEFAULT_SLIDE_WIDTH,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    HEADER_TO_BODY_SPACING,
)
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TextElement,
)


class TestBasePositionCalculator:
    """Unit tests for the base position calculator functionality."""

    @pytest.fixture
    def default_margins(self) -> dict[str, float]:
        return {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

    @pytest.fixture
    def calculator(self, default_margins: dict[str, float]) -> PositionCalculator:
        return PositionCalculator(
            slide_width=DEFAULT_SLIDE_WIDTH,
            slide_height=DEFAULT_SLIDE_HEIGHT,
            margins=default_margins,
        )

    def test_slide_zone_calculation_with_clear_spacing(
        self, calculator: PositionCalculator
    ):
        """Test that slide zones are calculated with clear spacing between them."""

        # Verify basic dimensions
        assert calculator.slide_width == DEFAULT_SLIDE_WIDTH
        assert calculator.slide_height == DEFAULT_SLIDE_HEIGHT

        # Verify content area calculation
        expected_content_width = (
            DEFAULT_SLIDE_WIDTH - DEFAULT_MARGIN_LEFT - DEFAULT_MARGIN_RIGHT
        )
        expected_content_height = (
            DEFAULT_SLIDE_HEIGHT - DEFAULT_MARGIN_TOP - DEFAULT_MARGIN_BOTTOM
        )

        assert calculator.max_content_width == expected_content_width
        assert calculator.max_content_height == expected_content_height

        # Verify header zone
        assert calculator.header_top == DEFAULT_MARGIN_TOP
        assert calculator.header_left == DEFAULT_MARGIN_LEFT
        assert calculator.header_width == expected_content_width
        assert calculator.header_height == HEADER_HEIGHT

        # Verify body zone with clear spacing
        expected_body_top = (
            calculator.header_top + HEADER_HEIGHT + HEADER_TO_BODY_SPACING
        )
        assert calculator.body_top == expected_body_top
        assert calculator.body_left == DEFAULT_MARGIN_LEFT
        assert calculator.body_width == expected_content_width

        # Verify footer zone
        expected_footer_top = (
            DEFAULT_SLIDE_HEIGHT - DEFAULT_MARGIN_BOTTOM - FOOTER_HEIGHT
        )
        assert calculator.footer_top == expected_footer_top
        assert calculator.footer_height == FOOTER_HEIGHT

        # Verify body height calculation (space between body start and footer with spacing)
        expected_body_bottom = expected_footer_top - BODY_TO_FOOTER_SPACING
        expected_body_height = expected_body_bottom - expected_body_top
        assert calculator.body_height == expected_body_height

        # Verify zones don't overlap
        assert calculator.header_top + HEADER_HEIGHT < calculator.body_top
        assert calculator.body_top + calculator.body_height < calculator.footer_top

    def test_zone_based_layout_content_aware_positioning(
        self, calculator: PositionCalculator
    ):
        """Test zone-based layout with content-aware element positioning."""

        title = TextElement(element_type=ElementType.TITLE, text="Zone Test Title")

        # Create elements with different content characteristics
        short_para = TextElement(
            element_type=ElementType.TEXT,
            text="Short paragraph.",
            object_id="short_para",
        )

        long_para = TextElement(
            element_type=ElementType.TEXT,
            text="This is a much longer paragraph that will require significantly more vertical space due to line wrapping and content length. "
            * 2,
            object_id="long_para",
        )

        bullet_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="First bullet point"),
                ListItem(text="Second bullet point with more content"),
                ListItem(text="Third bullet point"),
            ],
            object_id="bullet_list",
        )

        footer = TextElement(element_type=ElementType.FOOTER, text="Test Footer")

        slide = Slide(
            object_id="zone_test_slide",
            elements=[title, short_para, long_para, bullet_list, footer],
        )

        result_slide = calculator.calculate_positions(slide)

        # Verify all elements are positioned and sized
        for element in result_slide.elements:
            assert (
                element.position is not None
            ), f"Element {getattr(element, 'object_id', 'unknown')} not positioned"
            assert (
                element.size is not None
            ), f"Element {getattr(element, 'object_id', 'unknown')} not sized"

        # Get positioned elements
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_short = next(
            e for e in result_slide.elements if e.object_id == "short_para"
        )
        positioned_long = next(
            e for e in result_slide.elements if e.object_id == "long_para"
        )
        positioned_list = next(
            e for e in result_slide.elements if e.object_id == "bullet_list"
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )

        # Verify content-aware sizing
        assert (
            positioned_long.size[1] > positioned_short.size[1]
        ), "Longer paragraph should be taller than shorter paragraph"

        assert (
            positioned_list.size[1] > positioned_short.size[1]
        ), "List should be taller than short paragraph"

        # Verify zone placement
        assert (
            positioned_title.position[1] >= calculator.header_top
        ), "Title should be in header zone"
        assert (
            positioned_title.position[1] < calculator.body_top
        ), "Title should be within header zone"

        assert (
            positioned_footer.position[1] >= calculator.footer_top
        ), "Footer should be in footer zone"

        # Verify body elements are in body zone and properly stacked
        body_elements = [positioned_short, positioned_long, positioned_list]
        for element in body_elements:
            assert (
                element.position[1] >= calculator.body_top
            ), "Body element should be in body zone"

        # Verify vertical stacking order
        assert (
            positioned_short.position[1] < positioned_long.position[1]
        ), "Elements should be stacked vertically"
        assert (
            positioned_long.position[1] < positioned_list.position[1]
        ), "Elements should be stacked vertically"

    def test_section_based_predictable_division(self, calculator: PositionCalculator):
        """Test section-based layout with predictable division rules."""
        from markdowndeck.layout.calculator.section_layout import (
            calculate_section_based_positions,
        )

        title = TextElement(
            element_type=ElementType.TITLE, text="Section Division Test"
        )

        text1 = TextElement(
            element_type=ElementType.TEXT, text="Left content", object_id="left_text"
        )
        text2 = TextElement(
            element_type=ElementType.TEXT, text="Right content", object_id="right_text"
        )

        # Create sections with explicit width directives (70% / 30%)
        left_section = Section(
            id="left_section_70",
            type="section",
            directives={"width": 0.7},
            elements=[text1],
        )

        right_section = Section(
            id="right_section_30",
            type="section",
            directives={"width": 0.3},
            elements=[text2],
        )

        slide = Slide(
            object_id="section_division_slide",
            elements=[title, text1, text2],
            sections=[left_section, right_section],
        )

        result_slide = calculate_section_based_positions(calculator, slide)

        # Verify sections are positioned and sized
        assert len(result_slide.sections) == 2
        left_sec = result_slide.sections[0]
        right_sec = result_slide.sections[1]

        assert left_sec.position is not None
        assert left_sec.size is not None
        assert right_sec.position is not None
        assert right_sec.size is not None

        # Verify predictable division - sections should get exactly their specified proportions
        from markdowndeck.layout.constants import HORIZONTAL_SPACING

        body_width = calculator.body_width
        usable_width = body_width - HORIZONTAL_SPACING  # One spacing between 2 sections
        expected_left_width = usable_width * 0.7
        expected_right_width = usable_width * 0.3

        assert (
            abs(left_sec.size[0] - expected_left_width) < 2
        ), f"Left section should be exactly 70% width: expected {expected_left_width}, got {left_sec.size[0]}"

        assert (
            abs(right_sec.size[0] - expected_right_width) < 2
        ), f"Right section should be exactly 30% width: expected {expected_right_width}, got {right_sec.size[0]}"

        # Verify horizontal arrangement (width directives trigger horizontal layout)
        assert (
            left_sec.position[0] < right_sec.position[0]
        ), "Left section should be to left of right section"

        # Verify both sections start at same Y coordinate (horizontal layout)
        assert (
            abs(left_sec.position[1] - right_sec.position[1]) < 1
        ), "Sections should be at same Y level"

        # Verify elements are positioned within their sections
        left_element = left_sec.elements[0]
        right_element = right_sec.elements[0]

        assert (
            left_element.position[0] >= left_sec.position[0]
        ), "Left element should be within left section"
        assert (
            right_element.position[0] >= right_sec.position[0]
        ), "Right element should be within right section"

    def test_equal_division_when_no_width_directives(
        self, calculator: PositionCalculator
    ):
        """Test that sections without size directives get equal space allocation."""
        from markdowndeck.layout.calculator.section_layout import (
            calculate_section_based_positions,
        )

        title = TextElement(element_type=ElementType.TITLE, text="Equal Division Test")

        # Create four sections with NO width directives
        sections = []
        elements = []

        for i in range(4):
            text = TextElement(
                element_type=ElementType.TEXT,
                text=f"Content for section {i+1}",
                object_id=f"text_{i+1}",
            )
            elements.append(text)

            section = Section(
                id=f"section_{i+1}",
                type="section",
                # No width directive - should get equal division
                elements=[text],
            )
            sections.append(section)

        slide = Slide(
            object_id="equal_division_slide",
            elements=[title] + elements,
            sections=sections,
        )

        result_slide = calculate_section_based_positions(calculator, slide)

        # Verify all sections get equal heights (default vertical layout)
        positioned_sections = result_slide.sections
        assert len(positioned_sections) == 4

        from markdowndeck.layout.constants import VERTICAL_SPACING

        body_width = calculator.body_width
        body_height = calculator.body_height
        usable_height = body_height - (
            VERTICAL_SPACING * 3
        )  # 3 spacings between 4 sections
        expected_height_per_section = usable_height / 4

        for i, section in enumerate(positioned_sections):
            assert section.size is not None, f"Section {i} should be sized"

            # All sections should have full body width (vertical layout)
            actual_width = section.size[0]
            assert (
                abs(actual_width - body_width) < 2
            ), f"Section {i} should have full body width: expected {body_width}, got {actual_width}"

            # All sections should have equal height
            actual_height = section.size[1]
            assert (
                abs(actual_height - expected_height_per_section) < 2
            ), f"Section {i} should get equal height: expected {expected_height_per_section}, got {actual_height}"

        # Verify vertical arrangement (sections stacked top to bottom)
        for i in range(len(positioned_sections) - 1):
            current_bottom = (
                positioned_sections[i].position[1] + positioned_sections[i].size[1]
            )
            next_top = positioned_sections[i + 1].position[1]

            # Next section should start at or after current section (accounting for spacing)
            assert (
                next_top >= current_bottom
            ), f"Section {i+1} should be positioned below section {i}"

    def test_height_directives_trigger_vertical_layout(
        self, calculator: PositionCalculator
    ):
        """Test that height directives (without width) trigger vertical layout."""

        title = TextElement(element_type=ElementType.TITLE, text="Vertical Layout Test")

        text1 = TextElement(
            element_type=ElementType.TEXT, text="Top content", object_id="top_text"
        )
        text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Bottom content",
            object_id="bottom_text",
        )

        # Create sections with height directives (should stack vertically)
        top_section = Section(
            id="top_section",
            type="section",
            directives={"height": 100},  # Explicit height, no width
            elements=[text1],
        )

        bottom_section = Section(
            id="bottom_section",
            type="section",
            directives={"height": 80},  # Explicit height, no width
            elements=[text2],
        )

        slide = Slide(
            object_id="vertical_layout_slide",
            elements=[title, text1, text2],
            sections=[top_section, bottom_section],
        )

        result_slide = calculator.calculate_positions(slide)

        # Verify sections are stacked vertically
        top_sec = result_slide.sections[0]
        bottom_sec = result_slide.sections[1]

        # Verify explicit heights are respected
        assert (
            abs(top_sec.size[1] - 100) < 1
        ), "Top section should have specified height"
        assert (
            abs(bottom_sec.size[1] - 80) < 1
        ), "Bottom section should have specified height"

        # Verify both sections span full width (vertical layout)
        body_width = calculator.body_width
        assert (
            abs(top_sec.size[0] - body_width) < 1
        ), "Top section should span full width"
        assert (
            abs(bottom_sec.size[0] - body_width) < 1
        ), "Bottom section should span full width"

        # Verify vertical stacking
        assert (
            top_sec.position[1] < bottom_sec.position[1]
        ), "Top section should be above bottom section"

        # Verify horizontal alignment (both should start at same X)
        assert (
            abs(top_sec.position[0] - bottom_sec.position[0]) < 1
        ), "Sections should align horizontally"

    def test_element_width_calculation_with_directives(
        self, calculator: PositionCalculator
    ):
        """Test element width calculation respects directives and defaults."""

        container_width = 400.0

        # Element with no directive - should use default for type
        text_element = TextElement(element_type=ElementType.TEXT, text="Test text")
        text_width = calculator._calculate_element_width(text_element, container_width)

        # Text elements default to full width
        assert (
            abs(text_width - container_width) < 1
        ), "Text should default to full container width"

        # Element with percentage directive
        narrow_element = TextElement(
            element_type=ElementType.TEXT,
            text="Narrow text",
            directives={"width": 0.5},  # 50% width
        )
        narrow_width = calculator._calculate_element_width(
            narrow_element, container_width
        )

        expected_narrow_width = container_width * 0.5
        assert (
            abs(narrow_width - expected_narrow_width) < 1
        ), f"Element should be 50% width: expected {expected_narrow_width}, got {narrow_width}"

        # Element with absolute directive
        fixed_element = TextElement(
            element_type=ElementType.TEXT,
            text="Fixed width text",
            directives={"width": 200},  # 200 points
        )
        fixed_width = calculator._calculate_element_width(
            fixed_element, container_width
        )

        assert (
            abs(fixed_width - 200) < 1
        ), "Element should have specified absolute width"

        # Element with absolute directive larger than container (should be clamped)
        oversized_element = TextElement(
            element_type=ElementType.TEXT,
            text="Oversized text",
            directives={"width": 500},  # Larger than container
        )
        oversized_width = calculator._calculate_element_width(
            oversized_element, container_width
        )

        assert (
            abs(oversized_width - container_width) < 1
        ), "Oversized width directive should be clamped to container width"

    def test_body_elements_identification(self, calculator: PositionCalculator):
        """Test that body elements are correctly identified (excluding header/footer)."""

        title = TextElement(element_type=ElementType.TITLE, text="Title")
        subtitle = TextElement(element_type=ElementType.SUBTITLE, text="Subtitle")
        text1 = TextElement(element_type=ElementType.TEXT, text="Body text 1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Body text 2")
        code_block = CodeElement(element_type=ElementType.CODE, code="print('hello')")
        footer = TextElement(element_type=ElementType.FOOTER, text="Footer")

        slide = Slide(
            object_id="body_identification_slide",
            elements=[title, subtitle, text1, text2, code_block, footer],
        )

        body_elements = calculator.get_body_elements(slide)

        # Should only include text1, text2, and code_block
        assert (
            len(body_elements) == 3
        ), f"Should have 3 body elements, got {len(body_elements)}"

        body_types = [e.element_type for e in body_elements]
        expected_types = [ElementType.TEXT, ElementType.TEXT, ElementType.CODE]

        assert (
            body_types == expected_types
        ), "Body elements should be text and code only"

        # Verify header and footer elements are excluded
        assert not any(e.element_type == ElementType.TITLE for e in body_elements)
        assert not any(e.element_type == ElementType.SUBTITLE for e in body_elements)
        assert not any(e.element_type == ElementType.FOOTER for e in body_elements)

    def test_custom_slide_dimensions_and_margins(self):
        """Test calculator with custom slide dimensions and margins."""

        custom_width = 800.0
        custom_height = 600.0
        custom_margins = {"top": 40, "right": 30, "bottom": 40, "left": 30}

        calculator = PositionCalculator(
            slide_width=custom_width, slide_height=custom_height, margins=custom_margins
        )

        # Verify custom dimensions are used
        assert calculator.slide_width == custom_width
        assert calculator.slide_height == custom_height
        assert calculator.margins == custom_margins

        # Verify derived calculations use custom values
        expected_content_width = (
            custom_width - custom_margins["left"] - custom_margins["right"]
        )
        expected_content_height = (
            custom_height - custom_margins["top"] - custom_margins["bottom"]
        )

        assert calculator.max_content_width == expected_content_width
        assert calculator.max_content_height == expected_content_height

        # Verify zones use custom margins
        assert calculator.header_top == custom_margins["top"]
        assert calculator.header_left == custom_margins["left"]
        assert calculator.body_left == custom_margins["left"]

        # Verify footer calculation with custom dimensions
        expected_footer_top = custom_height - custom_margins["bottom"] - FOOTER_HEIGHT
        assert calculator.footer_top == expected_footer_top

    def test_empty_slide_handling(self, calculator: PositionCalculator):
        """Test that empty slides are handled gracefully."""

        empty_slide = Slide(object_id="empty_slide", elements=[])
        result_slide = calculator.calculate_positions(empty_slide)

        assert result_slide.object_id == "empty_slide"
        assert len(result_slide.elements) == 0
        # Should not raise any exceptions

    def test_slide_with_only_header_and_footer(self, calculator: PositionCalculator):
        """Test slide with only header and footer elements."""

        title = TextElement(element_type=ElementType.TITLE, text="Only Title")
        footer = TextElement(element_type=ElementType.FOOTER, text="Only Footer")

        slide = Slide(object_id="header_footer_only_slide", elements=[title, footer])

        result_slide = calculator.calculate_positions(slide)

        # Both elements should be positioned
        positioned_title = next(
            e for e in result_slide.elements if e.element_type == ElementType.TITLE
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.element_type == ElementType.FOOTER
        )

        assert positioned_title.position is not None
        assert positioned_title.size is not None
        assert positioned_footer.position is not None
        assert positioned_footer.size is not None

        # Title should be in header zone
        assert positioned_title.position[1] >= calculator.header_top
        assert positioned_title.position[1] < calculator.body_top

        # Footer should be in footer zone
        assert positioned_footer.position[1] >= calculator.footer_top
