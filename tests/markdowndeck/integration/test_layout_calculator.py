"""Integration tests for the content-aware layout calculation system."""

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.layout.constants import (
    DEFAULT_SLIDE_HEIGHT,
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    HEADER_TO_BODY_SPACING,
    VERTICAL_SPACING,
)
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
)


class TestLayoutCalculatorIntegration:
    """Integration tests for the layout calculation system."""

    @pytest.fixture
    def layout_manager(self) -> LayoutManager:
        """Create a layout manager with default settings."""
        return LayoutManager()

    def test_zone_based_content_aware_sizing(self, layout_manager: LayoutManager):
        """Test that zone-based layout properly sizes elements based on content."""

        # Create elements with varying content complexity
        title = TextElement(
            element_type=ElementType.TITLE, text="Test Title", object_id="title_1"
        )

        short_text = TextElement(
            element_type=ElementType.TEXT,
            text="Short paragraph.",
            object_id="short_text",
        )

        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a substantially longer paragraph with much more content that should result in a significantly taller element when measured by the content-aware metrics system because it will require multiple lines to display properly. "
            * 2,
            object_id="long_text",
        )

        simple_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="First item"), ListItem(text="Second item")],
            object_id="simple_list",
        )

        footer = TextElement(
            element_type=ElementType.FOOTER, text="Page Footer", object_id="footer_1"
        )

        slide = Slide(
            object_id="content_aware_slide",
            elements=[title, short_text, long_text, simple_list, footer],
        )

        # Calculate layout
        result_slide = layout_manager.calculate_positions(slide)

        # Verify all elements have positions and sizes
        for element in result_slide.elements:
            assert (
                element.position is not None
            ), f"Element {element.object_id} missing position"
            assert element.size is not None, f"Element {element.object_id} missing size"
            assert (
                element.size[0] > 0 and element.size[1] > 0
            ), f"Element {element.object_id} has invalid size"

        # Get positioned elements
        positioned_title = next(
            e for e in result_slide.elements if e.object_id == "title_1"
        )
        positioned_short = next(
            e for e in result_slide.elements if e.object_id == "short_text"
        )
        positioned_long = next(
            e for e in result_slide.elements if e.object_id == "long_text"
        )
        positioned_list = next(
            e for e in result_slide.elements if e.object_id == "simple_list"
        )
        positioned_footer = next(
            e for e in result_slide.elements if e.object_id == "footer_1"
        )

        # Verify content-aware sizing: longer content should result in taller elements
        assert (
            positioned_long.size[1] > positioned_short.size[1]
        ), f"Longer text ({positioned_long.size[1]}) should be taller than shorter text ({positioned_short.size[1]})"

        assert (
            positioned_list.size[1] > positioned_short.size[1]
        ), "List should be taller than simple text"

        # Verify vertical stacking in body zone with proper spacing
        body_elements = [positioned_short, positioned_long, positioned_list]
        for i in range(len(body_elements) - 1):
            current_element = body_elements[i]
            next_element = body_elements[i + 1]

            current_bottom = current_element.position[1] + current_element.size[1]
            next_top = next_element.position[1]

            # Next element should start after current element plus some spacing
            spacing = next_top - current_bottom
            assert spacing >= 0, f"Element {i+1} should not overlap element {i}"
            assert (
                spacing <= VERTICAL_SPACING * 2
            ), f"Spacing too large between elements {i} and {i+1}"

        # Verify slide zones are respected
        header_zone_bottom = layout_manager.margins["top"] + HEADER_HEIGHT
        body_zone_top = header_zone_bottom + HEADER_TO_BODY_SPACING
        footer_zone_top = (
            DEFAULT_SLIDE_HEIGHT - layout_manager.margins["bottom"] - FOOTER_HEIGHT
        )

        # Title in header zone
        assert (
            positioned_title.position[1] >= layout_manager.margins["top"]
        ), "Title should be in header zone"
        assert (
            positioned_title.position[1] < header_zone_bottom
        ), "Title should be within header zone"

        # Body elements in body zone
        for element in body_elements:
            assert (
                element.position[1] >= body_zone_top
            ), "Body element should be in body zone"

        # Footer in footer zone
        assert (
            positioned_footer.position[1] >= footer_zone_top
        ), "Footer should be in footer zone"

    def test_section_equal_division_no_directives(self, layout_manager: LayoutManager):
        """Test that sections are divided equally when no size directives are provided."""

        title = TextElement(element_type=ElementType.TITLE, text="Equal Division Test")

        # Create three sections with no width directives - should get equal widths
        section1 = Section(
            id="equal_section_1",
            type="section",
            elements=[
                TextElement(
                    element_type=ElementType.TEXT, text="Content 1", object_id="text_1"
                )
            ],
        )
        section2 = Section(
            id="equal_section_2",
            type="section",
            elements=[
                TextElement(
                    element_type=ElementType.TEXT, text="Content 2", object_id="text_2"
                )
            ],
        )
        section3 = Section(
            id="equal_section_3",
            type="section",
            elements=[
                TextElement(
                    element_type=ElementType.TEXT, text="Content 3", object_id="text_3"
                )
            ],
        )

        slide = Slide(
            object_id="equal_division_slide",
            elements=[title] + [s.elements[0] for s in [section1, section2, section3]],
            sections=[section1, section2, section3],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Verify sections have equal widths (horizontal layout due to lack of height directives)
        sections = result_slide.sections
        assert len(sections) == 3

        for section in sections:
            assert section.position is not None
            assert section.size is not None

        # Check that all sections have approximately equal widths
        section_widths = [s.size[0] for s in sections]
        expected_width = layout_manager.position_calculator.body_width / 3

        for i, width in enumerate(section_widths):
            assert (
                abs(width - expected_width) < 5
            ), f"Section {i} width {width:.1f} should be approximately {expected_width:.1f}"

        # Verify sections are arranged horizontally (side by side)
        for i in range(len(sections) - 1):
            current_right = sections[i].position[0] + sections[i].size[0]
            next_left = sections[i + 1].position[0]
            # Next section should start at or after current section ends (accounting for spacing)
            assert (
                next_left >= current_right - 5
            ), f"Section {i+1} should be to the right of section {i}"

    def test_section_explicit_directive_splits(self, layout_manager: LayoutManager):
        """Test that sections with explicit directives receive exact dimensions specified."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Explicit Division Test"
        )

        # Create sections with specific width directives (30%, 50%, 20%)
        left_section = Section(
            id="left_30_percent",
            type="section",
            directives={"width": 0.3},  # 30%
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Left 30%",
                    object_id="left_text",
                )
            ],
        )

        middle_section = Section(
            id="middle_50_percent",
            type="section",
            directives={"width": 0.5},  # 50%
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Middle 50%",
                    object_id="middle_text",
                )
            ],
        )

        right_section = Section(
            id="right_20_percent",
            type="section",
            directives={"width": 0.2},  # 20%
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Right 20%",
                    object_id="right_text",
                )
            ],
        )

        slide = Slide(
            object_id="explicit_division_slide",
            elements=[title]
            + [s.elements[0] for s in [left_section, middle_section, right_section]],
            sections=[left_section, middle_section, right_section],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Verify sections have exact specified widths
        sections = result_slide.sections
        body_width = layout_manager.position_calculator.body_width

        expected_widths = [body_width * 0.3, body_width * 0.5, body_width * 0.2]

        for i, (section, expected_width) in enumerate(
            zip(sections, expected_widths, strict=False)
        ):
            actual_width = section.size[0]
            assert (
                abs(actual_width - expected_width) < 2
            ), f"Section {i} width {actual_width:.1f} should be exactly {expected_width:.1f}"

        # Verify horizontal arrangement
        assert (
            sections[0].position[0] < sections[1].position[0] < sections[2].position[0]
        ), "Sections should be arranged left to right"

    def test_vertical_alignment_middle_and_bottom(self, layout_manager: LayoutManager):
        """Test that valign: middle and valign: bottom work correctly using two-pass pattern."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Vertical Alignment Test"
        )

        # Create sections with different vertical alignments and fixed heights
        short_text1 = TextElement(
            element_type=ElementType.TEXT, text="Line 1", object_id="line1"
        )
        short_text2 = TextElement(
            element_type=ElementType.TEXT, text="Line 2", object_id="line2"
        )

        # Middle-aligned section
        middle_section = Section(
            id="middle_aligned_section",
            type="section",
            directives={"valign": "middle", "height": 150, "width": 0.5},
            elements=[short_text1, short_text2],
        )

        # Bottom-aligned section
        bottom_text1 = TextElement(
            element_type=ElementType.TEXT, text="Bottom 1", object_id="bottom1"
        )
        bottom_text2 = TextElement(
            element_type=ElementType.TEXT, text="Bottom 2", object_id="bottom2"
        )

        bottom_section = Section(
            id="bottom_aligned_section",
            type="section",
            directives={"valign": "bottom", "height": 150, "width": 0.5},
            elements=[bottom_text1, bottom_text2],
        )

        slide = Slide(
            object_id="valign_test_slide",
            elements=[title, short_text1, short_text2, bottom_text1, bottom_text2],
            sections=[middle_section, bottom_section],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Test middle alignment
        middle_sec = result_slide.sections[0]
        middle_elements = middle_sec.elements

        # Calculate total content height for middle section
        total_content_height = sum(
            e.size[1] for e in middle_elements
        ) + VERTICAL_SPACING * (len(middle_elements) - 1)

        section_height = middle_sec.size[1]
        section_top = middle_sec.position[1]

        # With middle alignment, content should be vertically centered
        expected_start_y = section_top + (section_height - total_content_height) / 2
        actual_start_y = middle_elements[0].position[1]

        assert (
            abs(actual_start_y - expected_start_y) < 5
        ), f"Middle-aligned content should start at {expected_start_y:.1f}, got {actual_start_y:.1f}"

        # Test bottom alignment
        bottom_sec = result_slide.sections[1]
        bottom_elements = bottom_sec.elements

        # Calculate total content height for bottom section
        bottom_content_height = sum(
            e.size[1] for e in bottom_elements
        ) + VERTICAL_SPACING * (len(bottom_elements) - 1)

        bottom_section_height = bottom_sec.size[1]
        bottom_section_top = bottom_sec.position[1]

        # With bottom alignment, content should start near the bottom
        expected_bottom_start_y = (
            bottom_section_top + bottom_section_height - bottom_content_height
        )
        actual_bottom_start_y = bottom_elements[0].position[1]

        assert (
            abs(actual_bottom_start_y - expected_bottom_start_y) < 5
        ), f"Bottom-aligned content should start at {expected_bottom_start_y:.1f}, got {actual_bottom_start_y:.1f}"

    def test_overflow_acceptance_no_constraints(self, layout_manager: LayoutManager):
        """Test that content overflow is allowed and positioned correctly without constraints."""

        title = TextElement(element_type=ElementType.TITLE, text="Overflow Test")

        # Create a large table that will definitely overflow a small section
        large_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column 1", "Column 2", "Column 3", "Column 4"],
            rows=[
                [
                    f"Row {i} Cell 1 with longer content",
                    f"Row {i} Cell 2",
                    f"Row {i} Cell 3",
                    f"Row {i} Cell 4",
                ]
                for i in range(1, 16)  # 15 rows - will be very tall
            ],
            object_id="oversized_table",
        )

        # Put it in a section with very limited height
        small_section = Section(
            id="constrained_section",
            type="section",
            directives={"height": 80},  # Very small - table won't fit
            elements=[large_table],
        )

        slide = Slide(
            object_id="overflow_test_slide",
            elements=[title, large_table],
            sections=[small_section],
        )

        # This should succeed without throwing exceptions
        result_slide = layout_manager.calculate_positions(slide)

        # Verify table was positioned normally
        section = result_slide.sections[0]
        table_element = section.elements[0]

        assert (
            table_element.position is not None
        ), "Overflowing table should still be positioned"
        assert table_element.size is not None, "Overflowing table should still be sized"

        # Table should be sized based on its content, not constrained by section
        assert (
            table_element.size[1] > section.size[1]
        ), f"Table height ({table_element.size[1]}) should exceed section height ({section.size[1]}) - overflow allowed"

        # Table should be positioned at the section's top-left (or according to alignment)
        assert (
            table_element.position[0] >= section.position[0]
        ), "Table should start within section horizontally"
        assert (
            table_element.position[1] >= section.position[1]
        ), "Table should start within section vertically"

        # The table extending beyond section boundaries is the expected and correct behavior

    def test_complex_nested_section_layout(self, layout_manager: LayoutManager):
        """Test complex nested section layout with row and column combinations."""

        title = TextElement(element_type=ElementType.TITLE, text="Nested Layout Test")

        # Create nested structure: main row containing two columns, second column has sub-rows
        text1 = TextElement(
            element_type=ElementType.TEXT,
            text="Left column content",
            object_id="left_content",
        )

        text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Right top content",
            object_id="right_top",
        )
        text3 = TextElement(
            element_type=ElementType.TEXT,
            text="Right bottom content",
            object_id="right_bottom",
        )

        # Left column (simple)
        left_column = Section(
            id="left_column",
            type="section",
            directives={"width": 0.6},
            elements=[text1],
        )

        # Right column with sub-sections (30% top, 70% bottom)
        right_top_section = Section(
            id="right_top_section",
            type="section",
            directives={"height": 0.3},
            elements=[text2],
        )

        right_bottom_section = Section(
            id="right_bottom_section",
            type="section",
            directives={"height": 0.7},
            elements=[text3],
        )

        right_column = Section(
            id="right_column",
            type="section",
            directives={"width": 0.4},
            subsections=[right_top_section, right_bottom_section],
        )

        # Main row container
        main_row = Section(
            id="main_row", type="row", subsections=[left_column, right_column]
        )

        slide = Slide(
            object_id="nested_layout_slide",
            elements=[title, text1, text2, text3],
            sections=[main_row],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Verify structure
        main_row_result = result_slide.sections[0]
        assert main_row_result.type == "row"
        assert len(main_row_result.subsections) == 2

        left_col_result = main_row_result.subsections[0]
        right_col_result = main_row_result.subsections[1]

        # Verify horizontal arrangement of main columns
        assert (
            left_col_result.position[0] < right_col_result.position[0]
        ), "Left column should be to the left of right column"

        # Verify width proportions (60/40 split)
        body_width = layout_manager.position_calculator.body_width
        expected_left_width = body_width * 0.6
        expected_right_width = body_width * 0.4

        assert (
            abs(left_col_result.size[0] - expected_left_width) < 5
        ), "Left column width should be ~60% of body width"
        assert (
            abs(right_col_result.size[0] - expected_right_width) < 5
        ), "Right column width should be ~40% of body width"

        # Verify right column sub-sections
        assert len(right_col_result.subsections) == 2
        right_top_result = right_col_result.subsections[0]
        right_bottom_result = right_col_result.subsections[1]

        # Verify vertical arrangement of right sub-sections
        assert (
            right_top_result.position[1] < right_bottom_result.position[1]
        ), "Top sub-section should be above bottom sub-section"

        # Verify height proportions within right column (30/70 split)
        right_col_height = right_col_result.size[1]
        expected_top_height = right_col_height * 0.3
        expected_bottom_height = right_col_height * 0.7

        assert (
            abs(right_top_result.size[1] - expected_top_height) < 5
        ), "Right top section height should be ~30% of right column height"
        assert (
            abs(right_bottom_result.size[1] - expected_bottom_height) < 5
        ), "Right bottom section height should be ~70% of right column height"

    def test_intrinsic_element_heights_zone_layout(self, layout_manager: LayoutManager):
        """Test that zone-based layout respects intrinsic element heights from content."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Intrinsic Height Test"
        )

        # Create elements with very different content characteristics
        empty_text = TextElement(
            element_type=ElementType.TEXT,
            text="",  # Empty - should get minimum height
            object_id="empty_text",
        )

        minimal_text = TextElement(
            element_type=ElementType.TEXT,
            text="X",  # Single character
            object_id="minimal_text",
        )

        medium_code = CodeElement(
            element_type=ElementType.CODE,
            code="def function():\n    return True\n# Comment",
            language="python",
            object_id="medium_code",
        )

        large_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(
                    text=f"Item {i} with substantial content that will take up space"
                )
                for i in range(1, 8)
            ],
            object_id="large_list",
        )

        slide = Slide(
            object_id="intrinsic_height_slide",
            elements=[title, empty_text, minimal_text, medium_code, large_list],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Get positioned elements (excluding title)
        positioned_empty = next(
            e for e in result_slide.elements if e.object_id == "empty_text"
        )
        positioned_minimal = next(
            e for e in result_slide.elements if e.object_id == "minimal_text"
        )
        positioned_code = next(
            e for e in result_slide.elements if e.object_id == "medium_code"
        )
        positioned_list = next(
            e for e in result_slide.elements if e.object_id == "large_list"
        )

        # Verify elements have different heights based on content
        assert (
            positioned_large_list.size[1] > positioned_code.size[1]
        ), "Large list should be taller than medium code block"

        assert (
            positioned_code.size[1] > positioned_minimal.size[1]
        ), "Multi-line code should be taller than single character text"

        assert (
            positioned_minimal.size[1] >= positioned_empty.size[1]
        ), "Single character should be at least as tall as empty text"

        # Verify all heights are reasonable (positive and within expected ranges)
        for element in [
            positioned_empty,
            positioned_minimal,
            positioned_code,
            positioned_list,
        ]:
            assert element.size[1] > 0, "Element should have positive height"
            assert (
                element.size[1] < 1000
            ), f"Element height should be reasonable, got {element.size[1]}"

        # Verify proper stacking without overlap
        body_elements = [
            positioned_empty,
            positioned_minimal,
            positioned_code,
            positioned_list,
        ]
        for i in range(len(body_elements) - 1):
            current_bottom = body_elements[i].position[1] + body_elements[i].size[1]
            next_top = body_elements[i + 1].position[1]
            assert (
                next_top >= current_bottom
            ), f"Element {i+1} should not overlap element {i}"

    def test_directive_precedence_and_inheritance(self, layout_manager: LayoutManager):
        """Test that directives are applied with correct precedence and inheritance."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Directive Precedence Test"
        )

        # Element with its own alignment directive
        element_aligned = TextElement(
            element_type=ElementType.TEXT,
            text="Element-aligned text",
            directives={"align": "right"},  # Element-level directive
            object_id="element_aligned",
        )

        # Element without its own directive (should inherit from section)
        section_aligned = TextElement(
            element_type=ElementType.TEXT,
            text="Section-aligned text",
            object_id="section_aligned",
        )

        # Create a section with alignment directive
        test_section = Section(
            id="alignment_test_section",
            type="section",
            directives={"align": "center", "padding": 10},  # Section-level directives
            elements=[element_aligned, section_aligned],
        )

        slide = Slide(
            object_id="directive_precedence_slide",
            elements=[title, element_aligned, section_aligned],
            sections=[test_section],
        )

        result_slide = layout_manager.calculate_positions(slide)

        section_result = result_slide.sections[0]
        element_aligned_result = section_result.elements[0]
        section_result.elements[1]

        section_left = section_result.position[0]
        section_width = section_result.size[0]
        section_right = section_left + section_width

        # Element with its own directive should be right-aligned (element directive wins)
        element_right = (
            element_aligned_result.position[0] + element_aligned_result.size[0]
        )
        expected_right_position = section_right - 10  # Account for padding

        assert (
            abs(element_right - expected_right_position) < 5
        ), "Element with right alignment directive should be positioned at right edge"

        # Element without directive should inherit center alignment from section
        element_center = (
            element_aligned_result.position[0] + element_aligned_result.size[0] / 2
        )
        section_center = section_left + section_width / 2

        assert (
            abs(element_center - section_center) < 10
        ), "Element without directive should inherit center alignment from section"
