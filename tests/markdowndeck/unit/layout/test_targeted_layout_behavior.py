"""Targeted unit tests for specific layout behaviors per the Unified Layout Calculation Contract."""

import pytest
from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.calculator.section_layout import (
    _calculate_predictable_dimensions,
)
from markdowndeck.layout.constants import HORIZONTAL_SPACING, VERTICAL_SPACING
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


class TestEqualSplitBehavior:
    """Test equal space division when no size directives are provided."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_equal_width_split_no_directives(self, calculator):
        """Test that sections with no width directives get equal width allocation."""

        # Create three sections with no width directives
        section1 = Section(
            id="s1",
            type="section",
            elements=[TextElement(element_type=ElementType.TEXT, text="Content 1")],
        )
        section2 = Section(
            id="s2",
            type="section",
            elements=[TextElement(element_type=ElementType.TEXT, text="Content 2")],
        )
        section3 = Section(
            id="s3",
            type="section",
            elements=[TextElement(element_type=ElementType.TEXT, text="Content 3")],
        )

        sections = [section1, section2, section3]

        # Test the predictable dimensions calculation directly
        body_width = calculator.body_width

        dimensions = _calculate_predictable_dimensions(sections, body_width, HORIZONTAL_SPACING, "width")

        # All dimensions should be equal
        usable_width = body_width - (HORIZONTAL_SPACING * 2)
        expected_width = usable_width / 3
        for i, width in enumerate(dimensions):
            assert abs(width - expected_width) < 0.1, (
                f"Section {i} should get equal width: expected {expected_width:.1f}, got {width:.1f}"
            )

    def test_equal_height_split_no_directives(self, calculator):
        """Test that sections with no height directives get equal height allocation."""

        # Create sections with no height directives (vertical layout)
        section1 = Section(
            id="v1",
            type="section",
            elements=[TextElement(element_type=ElementType.TEXT, text="Vertical content 1")],
        )
        section2 = Section(
            id="v2",
            type="section",
            elements=[TextElement(element_type=ElementType.TEXT, text="Vertical content 2")],
        )

        sections = [section1, section2]

        # Test vertical division
        body_height = calculator.body_height

        dimensions = _calculate_predictable_dimensions(sections, body_height, VERTICAL_SPACING, "height")

        # Both sections should get equal height
        usable_height = body_height - (VERTICAL_SPACING * 1)
        expected_height = usable_height / 2
        for i, height in enumerate(dimensions):
            assert abs(height - expected_height) < 0.1, (
                f"Section {i} should get equal height: expected {expected_height:.1f}, got {height:.1f}"
            )

    def test_equal_split_with_many_sections(self, calculator):
        """Test equal division with many sections."""

        # Create 6 sections - should all get equal shares
        sections = []
        for i in range(6):
            section = Section(
                id=f"equal_section_{i}",
                type="section",
                elements=[TextElement(element_type=ElementType.TEXT, text=f"Content {i}")],
            )
            sections.append(section)

        body_width = calculator.body_width

        dimensions = _calculate_predictable_dimensions(sections, body_width, HORIZONTAL_SPACING, "width")

        usable_width = body_width - (HORIZONTAL_SPACING * 5)
        expected_width = usable_width / 6
        for i, width in enumerate(dimensions):
            assert abs(width - expected_width) < 0.1, f"Section {i} in 6-way split should get equal width"

    def test_equal_split_positioning_unified_model(self, calculator):
        """Test that equal split sections are positioned correctly in unified model."""

        title = TextElement(element_type=ElementType.TITLE, text="Equal Split Test")

        # Create sections for full positioning test
        sections = []
        elements = []
        for i in range(3):
            text = TextElement(element_type=ElementType.TEXT, text=f"Text {i}", object_id=f"text_{i}")
            elements.append(text)
            section = Section(id=f"pos_section_{i}", type="section", elements=[text])
            sections.append(section)

        slide = Slide(
            object_id="equal_positioning_slide",
            elements=[title] + elements,
            sections=sections,
        )

        result_slide = calculator.calculate_positions(slide)

        # Verify equal width allocation and proper horizontal positioning (default horizontal layout)
        positioned_sections = result_slide.sections
        body_width = calculator.body_width
        expected_width = body_width / 3  # Approximate, ignoring spacing for simplicity

        for i, section in enumerate(positioned_sections):
            # Check width
            assert abs(section.size[0] - expected_width) < 20, f"Section {i} should have approximately equal width"

            # Check horizontal positioning (each should be to the right of previous)
            if i > 0:
                prev_right = positioned_sections[i - 1].position[0] + positioned_sections[i - 1].size[0]
                curr_left = section.position[0]
                assert curr_left >= prev_right - 5, f"Section {i} should be positioned after section {i - 1}"


class TestUnifiedExplicitSplitBehavior:
    """Test explicit directive handling for precise space allocation in unified model."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_explicit_percentage_directives(self, calculator):
        """Test that percentage directives are honored exactly."""

        # Create sections with specific percentage directives
        section1 = Section(id="25pct", directives={"width": 0.25})  # 25%
        section2 = Section(id="50pct", directives={"width": 0.50})  # 50%
        section3 = Section(id="25pct_2", directives={"width": 0.25})  # 25%

        sections = [section1, section2, section3]
        body_width = calculator.body_width

        dimensions = _calculate_predictable_dimensions(sections, body_width, HORIZONTAL_SPACING, "width")

        usable_width = body_width - (HORIZONTAL_SPACING * 2)
        expected_widths = [
            usable_width * 0.25,
            usable_width * 0.50,
            usable_width * 0.25,
        ]

        for i, (actual, expected) in enumerate(zip(dimensions, expected_widths, strict=False)):
            assert abs(actual - expected) < 0.1, (
                f"Section {i} should have exact percentage width: expected {expected:.1f}, got {actual:.1f}"
            )

    def test_explicit_absolute_directives(self, calculator):
        """Test that absolute point directives are honored exactly."""

        # Create sections with absolute width directives
        section1 = Section(id="abs_100", directives={"width": 100})  # 100 points
        section2 = Section(id="abs_150", directives={"width": 150})  # 150 points
        section3 = Section(id="abs_200", directives={"width": 200})  # 200 points

        sections = [section1, section2, section3]
        body_width = calculator.body_width
        total_spacing = HORIZONTAL_SPACING * (len(sections) - 1)
        available_width = body_width - total_spacing

        dimensions = _calculate_predictable_dimensions(sections, available_width, HORIZONTAL_SPACING, "width")

        expected_widths = [100, 150, 200]

        for i, (actual, expected) in enumerate(zip(dimensions, expected_widths, strict=False)):
            assert abs(actual - expected) < 0.1, (
                f"Section {i} should have exact absolute width: expected {expected}, got {actual:.1f}"
            )

    def test_mixed_explicit_and_implicit_sections(self, calculator):
        """Test mixing explicit directives with implicit (no directive) sections."""

        # Two sections with explicit directives, one without
        section1 = Section(id="explicit_30", directives={"width": 0.3})  # 30%
        section2 = Section(id="implicit")  # No directive - should get remaining space
        section3 = Section(id="explicit_40", directives={"width": 0.4})  # 40%

        sections = [section1, section2, section3]
        body_width = calculator.body_width

        dimensions = _calculate_predictable_dimensions(sections, body_width, HORIZONTAL_SPACING, "width")

        # Section 1: 30% of usable space
        # Section 3: 40% of usable space
        # Section 2: Remaining 30% of usable space
        usable_width = body_width - (HORIZONTAL_SPACING * 2)
        expected_widths = [
            usable_width * 0.3,  # Section 1: explicit 30%
            usable_width * 0.3,  # Section 2: remaining 30%
            usable_width * 0.4,  # Section 3: explicit 40%
        ]

        for i, (actual, expected) in enumerate(zip(dimensions, expected_widths, strict=False)):
            assert abs(actual - expected) < 0.1, (
                f"Section {i} width should account for mixed explicit/implicit: expected {expected:.1f}, got {actual:.1f}"
            )

    def test_explicit_directives_exceeding_available_space(self, calculator):
        """Test that explicit directives are scaled proportionally when they exceed available space."""

        # Create sections with directives that total > 100%
        section1 = Section(id="over_60", directives={"width": 0.6})  # 60%
        section2 = Section(id="over_70", directives={"width": 0.7})  # 70%
        # Total: 130% - should be scaled down proportionally

        sections = [section1, section2]
        body_width = calculator.body_width

        dimensions = _calculate_predictable_dimensions(sections, body_width, HORIZONTAL_SPACING, "width")

        # Should be scaled down by factor of 1.0 / 1.3 = 0.769...
        usable_width = body_width - (HORIZONTAL_SPACING * 1)
        scale_factor = 1.0 / 1.3
        expected_widths = [
            usable_width * 0.6 * scale_factor,  # Scaled 60%
            usable_width * 0.7 * scale_factor,  # Scaled 70%
        ]

        for i, (actual, expected) in enumerate(zip(dimensions, expected_widths, strict=False)):
            assert abs(actual - expected) < 1, (
                f"Oversized section {i} should be scaled proportionally: expected {expected:.1f}, got {actual:.1f}"
            )

    def test_explicit_height_directives(self, calculator):
        """Test explicit height directives work correctly."""

        # Create sections with height directives for vertical layout
        section1 = Section(id="height_60", directives={"height": 60})
        section2 = Section(id="height_100", directives={"height": 100})

        sections = [section1, section2]
        body_height = calculator.body_height

        dimensions = _calculate_predictable_dimensions(sections, body_height, VERTICAL_SPACING, "height")

        expected_heights = [60, 100]

        for i, (actual, expected) in enumerate(zip(dimensions, expected_heights, strict=False)):
            assert abs(actual - expected) < 0.1, f"Section {i} should have exact height: expected {expected}, got {actual:.1f}"


class TestUnifiedIntrinsicElementHeight:
    """Test that elements are sized based on their intrinsic content needs in unified model."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_text_element_content_driven_height_unified(self, calculator):
        """Test that text elements get height based on content length in unified model."""

        short_text = TextElement(element_type=ElementType.TEXT, text="Short", object_id="short")

        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a substantially longer piece of text that will require multiple lines when rendered and should therefore result in a taller element than the short text above. "
            * 2,
            object_id="long",
        )

        # Test with unified model (no explicit sections - should create root section)
        slide = Slide(object_id="text_height_slide", elements=[short_text, long_text])

        result_slide = calculator.calculate_positions(slide)

        # Should have created root section
        assert len(result_slide.sections) == 1, "Should create root section"
        root_section = result_slide.sections[0]

        short_positioned = next(e for e in root_section.elements if e.object_id == "short")
        long_positioned = next(e for e in root_section.elements if e.object_id == "long")

        assert short_positioned.size is not None
        assert long_positioned.size is not None
        assert long_positioned.size[1] > short_positioned.size[1], (
            f"Long text ({long_positioned.size[1]:.1f}) should be taller than short text ({short_positioned.size[1]:.1f})"
        )

    def test_list_element_content_driven_height_unified(self, calculator):
        """Test that list elements get height based on number and content of items in unified model."""

        short_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1"), ListItem(text="Item 2")],
            object_id="short_list",
        )

        long_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"Item {i} with substantial content that takes space") for i in range(1, 8)],
            object_id="long_list",
        )

        slide = Slide(object_id="list_height_slide", elements=[short_list, long_list])

        result_slide = calculator.calculate_positions(slide)

        # Should create root section
        root_section = result_slide.sections[0]

        short_positioned = next(e for e in root_section.elements if e.object_id == "short_list")
        long_positioned = next(e for e in root_section.elements if e.object_id == "long_list")

        assert long_positioned.size[1] > short_positioned.size[1], (
            "List with more items should be taller than list with fewer items"
        )

    def test_table_element_content_driven_height_unified(self, calculator):
        """Test that table elements get height based on number of rows and content in unified model."""

        small_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["A1", "B1"], ["A2", "B2"]],
            object_id="small_table",
        )

        large_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column 1", "Column 2"],
            rows=[[f"Row {i} with longer content", f"More content in row {i}"] for i in range(1, 11)],
            object_id="large_table",
        )

        slide = Slide(object_id="table_height_slide", elements=[small_table, large_table])

        result_slide = calculator.calculate_positions(slide)

        # Should create root section
        root_section = result_slide.sections[0]

        small_positioned = next(e for e in root_section.elements if e.object_id == "small_table")
        large_positioned = next(e for e in root_section.elements if e.object_id == "large_table")

        assert large_positioned.size[1] > small_positioned.size[1], (
            "Table with more rows should be taller than table with fewer rows"
        )

    def test_code_element_content_driven_height_unified(self, calculator):
        """Test that code elements get height based on lines of code in unified model."""

        short_code = CodeElement(
            element_type=ElementType.CODE,
            code="print('hello')",
            language="python",
            object_id="short_code",
        )

        long_code = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join(
                [
                    "def complex_function(param1, param2, param3):",
                    '    """This is a complex function with multiple lines."""',
                    "    result = param1 + param2",
                    "    if result > param3:",
                    "        return result * 2",
                    "    else:",
                    "        return result / 2",
                    "    # This is a comment",
                    "    # Another comment line",
                    "    final_result = some_calculation(result)",
                    "    return final_result",
                ]
            ),
            language="python",
            object_id="long_code",
        )

        slide = Slide(object_id="code_height_slide", elements=[short_code, long_code])

        result_slide = calculator.calculate_positions(slide)

        # Should create root section
        root_section = result_slide.sections[0]

        short_positioned = next(e for e in root_section.elements if e.object_id == "short_code")
        long_positioned = next(e for e in root_section.elements if e.object_id == "long_code")

        assert long_positioned.size[1] > short_positioned.size[1], "Multi-line code should be taller than single-line code"

    def test_element_heights_respect_available_width_unified(self, calculator):
        """Test that element heights vary with available width in unified model."""

        wrappable_text = TextElement(
            element_type=ElementType.TEXT,
            text="This text will wrap differently depending on the available width and should be taller when constrained to a narrow width",
            object_id="wrappable",
        )

        # Test 1: With root section (full width)
        wide_slide = Slide(object_id="wide_slide", elements=[wrappable_text])

        # Test 2: With explicit narrow section
        narrow_section = Section(
            id="narrow_section",
            type="section",
            directives={"width": 0.3},  # 30% width - much narrower
            elements=[wrappable_text],
        )

        narrow_slide = Slide(
            object_id="narrow_slide",
            elements=[wrappable_text],
            sections=[narrow_section],
        )

        # Calculate both layouts
        wide_result = calculator.calculate_positions(wide_slide)
        narrow_result = calculator.calculate_positions(narrow_slide)

        # Extract elements
        wide_element = wide_result.sections[0].elements[0]  # From root section
        narrow_element = narrow_result.sections[0].elements[0]  # From narrow section

        # Narrower width should result in taller height due to text wrapping
        assert narrow_element.size[1] > wide_element.size[1], (
            f"Narrow layout ({narrow_element.size[1]:.1f}) should be taller than wide layout ({wide_element.size[1]:.1f})"
        )


class TestUnifiedVerticalAlignmentCorrectness:
    """Test that valign directives work correctly using two-pass pattern in unified model."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_valign_top_default_behavior_unified(self, calculator):
        """Test that default (top) vertical alignment positions elements at section top."""

        title = TextElement(element_type=ElementType.TITLE, text="VAlign Top Test")

        text1 = TextElement(element_type=ElementType.TEXT, text="First line", object_id="line1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Second line", object_id="line2")

        # Section with explicit height and default (top) alignment
        top_section = Section(
            id="top_aligned_section",
            type="section",
            directives={"height": 200},  # Fixed height for testing
            elements=[text1, text2],
        )

        slide = Slide(
            object_id="valign_top_slide",
            elements=[title, text1, text2],
            sections=[top_section],
        )

        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        elements = section.elements

        # First element should start at top of section (accounting for padding)
        section_top = section.position[1]
        first_element_y = elements[0].position[1]

        # Should be very close to section top (within padding)
        assert abs(first_element_y - section_top) <= 10, (
            f"Top-aligned content should start near section top: section={section_top}, element={first_element_y}"
        )

    def test_valign_middle_centers_content_unified(self, calculator):
        """Test that middle vertical alignment centers content in available space."""

        title = TextElement(element_type=ElementType.TITLE, text="VAlign Middle Test")

        text1 = TextElement(element_type=ElementType.TEXT, text="Centered line 1", object_id="center1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Centered line 2", object_id="center2")

        # Section with middle alignment and fixed height
        middle_section = Section(
            id="middle_aligned_section",
            type="section",
            directives={"valign": "middle", "height": 200},
            elements=[text1, text2],
        )

        slide = Slide(
            object_id="valign_middle_slide",
            elements=[title, text1, text2],
            sections=[middle_section],
        )

        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        elements = section.elements

        # Calculate expected middle position
        section_top = section.position[1]
        section_height = section.size[1]
        section_center = section_top + section_height / 2

        # Calculate actual content center
        first_element_y = elements[0].position[1]
        last_element = elements[-1]
        last_element_bottom = last_element.position[1] + last_element.size[1]
        content_center = (first_element_y + last_element_bottom) / 2

        # Content center should be close to section center
        assert abs(content_center - section_center) <= 15, (
            f"Middle-aligned content center ({content_center:.1f}) should be near section center ({section_center:.1f})"
        )

    def test_valign_bottom_aligns_to_bottom_unified(self, calculator):
        """Test that bottom vertical alignment positions content at section bottom."""

        title = TextElement(element_type=ElementType.TITLE, text="VAlign Bottom Test")

        text1 = TextElement(element_type=ElementType.TEXT, text="Bottom line 1", object_id="bottom1")
        text2 = TextElement(element_type=ElementType.TEXT, text="Bottom line 2", object_id="bottom2")

        # Section with bottom alignment and fixed height
        bottom_section = Section(
            id="bottom_aligned_section",
            type="section",
            directives={"valign": "bottom", "height": 200},
            elements=[text1, text2],
        )

        slide = Slide(
            object_id="valign_bottom_slide",
            elements=[title, text1, text2],
            sections=[bottom_section],
        )

        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        elements = section.elements

        # Last element should end near bottom of section (accounting for padding)
        section_bottom = section.position[1] + section.size[1]
        last_element = elements[-1]
        last_element_bottom = last_element.position[1] + last_element.size[1]

        assert abs(last_element_bottom - section_bottom) <= 15, (
            f"Bottom-aligned content should end near section bottom: section={section_bottom}, element={last_element_bottom}"
        )


class TestUnifiedOverflowAcceptance:
    """Test that content overflow is accepted and positioned correctly in unified model."""

    @pytest.fixture
    def calculator(self):
        return PositionCalculator()

    def test_element_overflow_in_small_section_unified(self, calculator):
        """Test that large elements overflow small sections without constraint in unified model."""

        title = TextElement(element_type=ElementType.TITLE, text="Overflow Test")

        # Create a very large table
        huge_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2", "Col3", "Col4", "Col5"],
            rows=[
                [
                    f"Row {i} Col 1 with lengthy content",
                    f"Row {i} Col 2",
                    f"Row {i} Col 3",
                    f"Row {i} Col 4",
                    f"Row {i} Col 5",
                ]
                for i in range(1, 21)  # 20 rows - will be very tall
            ],
            object_id="huge_table",
        )

        # Put it in a tiny section
        tiny_section = Section(
            id="tiny_constrained_section",
            type="section",
            directives={"height": 50, "width": 200},  # Very small
            elements=[huge_table],
        )

        slide = Slide(
            object_id="overflow_test_slide",
            elements=[title, huge_table],
            sections=[tiny_section],
        )

        # Should not raise exceptions
        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        table = section.elements[0]

        # Verify table is positioned normally
        assert table.position is not None
        assert table.size is not None

        # Table should be sized based on content, not constrained by section
        assert table.size[1] > section.size[1], (
            f"Table height ({table.size[1]:.1f}) should exceed tiny section height ({section.size[1]:.1f})"
        )

        assert abs(table.size[0] - section.size[0]) < 1, (
            f"Table width ({table.size[0]:.1f}) should be constrained by section width ({section.size[0]:.1f})"
        )

        # Table should start within section bounds (but extend beyond)
        assert table.position[0] >= section.position[0], "Table should start within section horizontally"
        assert table.position[1] >= section.position[1], "Table should start within section vertically"

    def test_multiple_overflowing_elements_unified(self, calculator):
        """Test multiple large elements in constrained sections in unified model."""

        title = TextElement(element_type=ElementType.TITLE, text="Multiple Overflow Test")

        # Create multiple large elements
        large_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is an extremely long paragraph of text that goes on and on and contains far too much content to fit in a small section. It should overflow gracefully without being constrained or modified by the layout system. "
            * 3,
            object_id="large_text",
        )

        large_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text=f"This is bullet point {i} with substantial content that takes up significant space")
                for i in range(1, 16)
            ],
            object_id="large_list",
        )

        # Put them in a constrained section
        constrained_section = Section(
            id="constrained_multi_section",
            type="section",
            directives={"height": 80},  # Very small height
            elements=[large_text, large_list],
        )

        slide = Slide(
            object_id="multi_overflow_slide",
            elements=[title, large_text, large_list],
            sections=[constrained_section],
        )

        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        text_element = section.elements[0]
        list_element = section.elements[1]

        # Both elements should be positioned and sized normally
        assert text_element.position is not None
        assert text_element.size is not None
        assert list_element.position is not None
        assert list_element.size is not None

        # Both should likely overflow the small section
        assert text_element.size[1] > 40, "Large text should have substantial height"
        assert list_element.size[1] > 40, "Large list should have substantial height"

        # Combined height likely exceeds section height - this is correct
        combined_height = text_element.size[1] + list_element.size[1] + VERTICAL_SPACING
        assert combined_height > section.size[1], (
            "Combined element height should exceed small section height (overflow expected)"
        )

        # Elements should be stacked normally
        assert list_element.position[1] > text_element.position[1], "List should be positioned below text element"

    def test_overflow_with_section_padding_unified(self, calculator):
        """Test that overflow works correctly even with section padding in unified model."""

        title = TextElement(element_type=ElementType.TITLE, text="Overflow with Padding Test")

        # Large code block
        large_code = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join(
                [
                    f"def function_{i}():\n    return 'This is function number {i} with code that takes space'\n"
                    for i in range(1, 16)
                ]
            ),
            language="python",
            object_id="large_code",
        )

        # Section with padding and height constraint
        padded_section = Section(
            id="padded_constrained_section",
            type="section",
            directives={"height": 100, "padding": 20},  # Small height, large padding
            elements=[large_code],
        )

        slide = Slide(
            object_id="padded_overflow_slide",
            elements=[title, large_code],
            sections=[padded_section],
        )

        result_slide = calculator.calculate_positions(slide)

        section = result_slide.sections[0]
        code_element = section.elements[0]

        # Code should be positioned accounting for padding
        expected_content_left = section.position[0] + 20  # padding
        expected_content_top = section.position[1] + 20  # padding

        assert abs(code_element.position[0] - expected_content_left) <= 1, (
            "Code should be positioned accounting for left padding"
        )
        assert abs(code_element.position[1] - expected_content_top) <= 1, (
            "Code should be positioned accounting for top padding"
        )

        # Code should still be sized based on content (likely overflowing)
        available_content_height = section.size[1] - 40  # Total padding
        assert code_element.size[1] > available_content_height, "Large code block should overflow constrained padded section"

    def test_root_section_overflow_behavior(self, calculator):
        """Test overflow behavior when elements are in auto-created root section."""

        title = TextElement(element_type=ElementType.TITLE, text="Root Section Overflow Test")

        # Create very large content that would overflow even the full body zone
        massive_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column A", "Column B", "Column C"],
            rows=[
                [
                    f"Row {i} with substantial content",
                    f"Row {i} Col B",
                    f"Row {i} Col C",
                ]
                for i in range(1, 50)  # 49 rows - will be extremely tall
            ],
            object_id="massive_table",
        )

        # No explicit sections - should create root section
        slide = Slide(
            object_id="root_overflow_slide",
            elements=[title, massive_table],
        )

        result_slide = calculator.calculate_positions(slide)

        # Should have root section
        assert len(result_slide.sections) == 1, "Should create root section"
        root_section = result_slide.sections[0]

        table_element = root_section.elements[0]

        # Table should be positioned normally
        assert table_element.position is not None
        assert table_element.size is not None

        # Table should be sized based on content (will definitely overflow)
        body_height = calculator.body_height
        assert table_element.size[1] > body_height, (
            f"Massive table height ({table_element.size[1]:.1f}) should exceed body height ({body_height:.1f})"
        )

        # Width should be constrained by body width
        body_width = calculator.body_width
        assert abs(table_element.size[0] - body_width) < 5, "Table width should be constrained by body width"

        # Position should be within root section (which spans body zone)
        assert table_element.position[0] >= root_section.position[0], "Table should start within root section horizontally"
        assert table_element.position[1] >= root_section.position[1], "Table should start within root section vertically"
