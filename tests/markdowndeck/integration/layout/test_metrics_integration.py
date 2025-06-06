"""Comprehensive integration tests for the metrics system with the unified layout engine."""

import pytest
from markdowndeck.layout import LayoutManager
from markdowndeck.layout.constants import (
    MIN_CODE_HEIGHT,
    MIN_IMAGE_HEIGHT,
    MIN_LIST_HEIGHT,
    MIN_TABLE_HEIGHT,
    MIN_TEXT_HEIGHT,
)
from markdowndeck.layout.metrics import calculate_element_height
from markdowndeck.layout.metrics.code import calculate_code_element_height
from markdowndeck.layout.metrics.image import calculate_image_element_height
from markdowndeck.layout.metrics.list import calculate_list_element_height
from markdowndeck.layout.metrics.table import calculate_table_element_height
from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import (
    CodeElement,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
)


class TestMetricsSystemIntegration:
    """Test that the metrics system integrates correctly with the layout engine."""

    @pytest.fixture
    def layout_manager(self):
        return LayoutManager()

    def test_metrics_dispatch_correctness(self, layout_manager):
        """Test that the main metrics dispatcher calls the correct specialized functions."""

        # Create elements of different types
        text_elem = TextElement(element_type=ElementType.TEXT, text="Test text")
        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST, items=[ListItem(text="Item")]
        )
        table_elem = TableElement(
            element_type=ElementType.TABLE, headers=["H1"], rows=[["R1"]]
        )
        code_elem = CodeElement(element_type=ElementType.CODE, code="print('test')")
        image_elem = ImageElement(
            element_type=ElementType.IMAGE, url="https://example.com/test.jpg"
        )

        available_width = 400.0

        # Test that dispatcher returns same results as direct calls
        text_height_main = calculate_element_height(text_elem, available_width)
        text_height_direct = calculate_text_element_height(text_elem, available_width)
        assert (
            abs(text_height_main - text_height_direct) < 0.1
        ), "Text metrics dispatch should match direct call"

        list_height_main = calculate_element_height(list_elem, available_width)
        list_height_direct = calculate_list_element_height(list_elem, available_width)
        assert (
            abs(list_height_main - list_height_direct) < 0.1
        ), "List metrics dispatch should match direct call"

        table_height_main = calculate_element_height(table_elem, available_width)
        table_height_direct = calculate_table_element_height(
            table_elem, available_width
        )
        assert (
            abs(table_height_main - table_height_direct) < 0.1
        ), "Table metrics dispatch should match direct call"

        code_height_main = calculate_element_height(code_elem, available_width)
        code_height_direct = calculate_code_element_height(code_elem, available_width)
        assert (
            abs(code_height_main - code_height_direct) < 0.1
        ), "Code metrics dispatch should match direct call"

        image_height_main = calculate_element_height(image_elem, available_width)
        image_height_direct = calculate_image_element_height(
            image_elem, available_width, 0
        )
        assert (
            abs(image_height_main - image_height_direct) < 0.1
        ), "Image metrics dispatch should match direct call"

    def test_metrics_minimum_heights_enforced(self, layout_manager):
        """Test that all metrics modules enforce their minimum heights."""

        # Create empty/minimal elements
        empty_text = TextElement(element_type=ElementType.TEXT, text="")
        empty_list = ListElement(element_type=ElementType.BULLET_LIST, items=[])
        empty_table = TableElement(element_type=ElementType.TABLE, headers=[], rows=[])
        empty_code = CodeElement(element_type=ElementType.CODE, code="")
        empty_image = ImageElement(element_type=ElementType.IMAGE, url="")

        available_width = 400.0

        # All should return at least their minimum heights
        text_height = calculate_text_element_height(empty_text, available_width)
        assert (
            text_height >= MIN_TEXT_HEIGHT
        ), f"Empty text should get minimum height {MIN_TEXT_HEIGHT}, got {text_height}"

        list_height = calculate_list_element_height(empty_list, available_width)
        assert (
            list_height >= MIN_LIST_HEIGHT
        ), f"Empty list should get minimum height {MIN_LIST_HEIGHT}, got {list_height}"

        table_height = calculate_table_element_height(empty_table, available_width)
        assert (
            table_height >= MIN_TABLE_HEIGHT
        ), f"Empty table should get minimum height {MIN_TABLE_HEIGHT}, got {table_height}"

        code_height = calculate_code_element_height(empty_code, available_width)
        assert (
            code_height >= MIN_CODE_HEIGHT
        ), f"Empty code should get minimum height {MIN_CODE_HEIGHT}, got {code_height}"

        image_height = calculate_image_element_height(empty_image, available_width)
        assert (
            image_height >= MIN_IMAGE_HEIGHT
        ), f"Empty image should get minimum height {MIN_IMAGE_HEIGHT}, got {image_height}"

    def test_metrics_width_responsiveness(self, layout_manager):
        """Test that metrics respond correctly to width changes (narrower = taller for text-based)."""

        # Create elements with content that will wrap differently at different widths
        wrappable_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a moderately long piece of text that will wrap differently depending on the available width and should demonstrate the content-aware nature of the metrics system.",
        )

        wrappable_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(
                    text="This is a bullet point with substantial content that will also wrap differently at different widths"
                ),
                ListItem(
                    text="Another bullet point with more content to test wrapping behavior"
                ),
            ],
        )

        wrappable_code = CodeElement(
            element_type=ElementType.CODE,
            code="def long_function_name_that_will_wrap(parameter_one, parameter_two, parameter_three, parameter_four):\n    return some_calculation_with_long_variable_names(parameter_one, parameter_two)",
        )

        wide_width = 600.0
        narrow_width = 200.0

        # Test text wrapping
        text_wide = calculate_text_element_height(wrappable_text, wide_width)
        text_narrow = calculate_text_element_height(wrappable_text, narrow_width)
        assert (
            text_narrow > text_wide
        ), f"Text should be taller when narrow ({text_narrow}) vs wide ({text_wide})"

        # Test list wrapping
        list_wide = calculate_list_element_height(wrappable_list, wide_width)
        list_narrow = calculate_list_element_height(wrappable_list, narrow_width)
        assert (
            list_narrow > list_wide
        ), f"List should be taller when narrow ({list_narrow}) vs wide ({list_wide})"

        # Test code wrapping
        code_wide = calculate_code_element_height(wrappable_code, wide_width)
        code_narrow = calculate_code_element_height(wrappable_code, narrow_width)
        assert (
            code_narrow > code_wide
        ), f"Code should be taller when narrow ({code_narrow}) vs wide ({code_wide})"

    def test_metrics_integration_in_unified_layout_context(self, layout_manager):
        """Test that metrics work correctly when integrated with the unified layout system."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Metrics Integration Test"
        )

        # Create elements with known content characteristics
        short_text = TextElement(
            element_type=ElementType.TEXT, text="Brief content.", object_id="short_text"
        )

        medium_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="First point"),
                ListItem(text="Second point with more content"),
                ListItem(text="Third point"),
            ],
            object_id="medium_list",
        )

        large_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column A", "Column B", "Column C"],
            rows=[
                [f"Row {i} Content A", f"Row {i} Content B", f"Row {i} Content C"]
                for i in range(1, 8)
            ],
            object_id="large_table",
        )

        # Test with unified layout (no explicit sections - should create root section)
        slide = Slide(
            object_id="metrics_integration_slide",
            elements=[title, short_text, medium_list, large_table],
        )

        # Calculate layout using unified system
        result_slide = layout_manager.calculate_positions(slide)

        # Verify root section was created
        assert len(result_slide.sections) == 1, "Should create root section"
        root_section = result_slide.sections[0]

        # Extract positioned elements from root section
        positioned_text = next(
            e for e in root_section.elements if e.object_id == "short_text"
        )
        positioned_list = next(
            e for e in root_section.elements if e.object_id == "medium_list"
        )
        positioned_table = next(
            e for e in root_section.elements if e.object_id == "large_table"
        )

        # Heights should reflect content complexity: table > list > short text
        assert (
            positioned_table.size[1] > positioned_list.size[1]
        ), "Large table should be taller than medium list"
        assert (
            positioned_list.size[1] > positioned_text.size[1]
        ), "Medium list should be taller than short text"

        # All should have reasonable, positive heights
        for element in [positioned_text, positioned_list, positioned_table]:
            assert element.size[1] > 10, "Element should have reasonable height"
            assert element.size[1] < 2000, "Element height should not be excessive"

    def test_metrics_with_directives_and_constraints(self, layout_manager):
        """Test that metrics work correctly with various directives and constraints."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Metrics Directives Test"
        )

        # Text with custom font size
        large_font_text = TextElement(
            element_type=ElementType.TEXT,
            text="Text with large font size",
            directives={"fontsize": 20.0},
            object_id="large_font",
        )

        # Text with width constraint
        narrow_text = TextElement(
            element_type=ElementType.TEXT,
            text="This text has a width constraint that should affect its height calculation through the metrics system",
            directives={"width": 0.3},  # 30% width
            object_id="narrow_text",
        )

        # Image with explicit height
        fixed_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"height": 150},
            object_id="fixed_image",
        )

        slide = Slide(
            object_id="metrics_directives_slide",
            elements=[title, large_font_text, narrow_text, fixed_image],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Extract positioned elements from root section
        root_section = result_slide.sections[0]

        positioned_large_font = next(
            e for e in root_section.elements if e.object_id == "large_font"
        )
        positioned_narrow = next(
            e for e in root_section.elements if e.object_id == "narrow_text"
        )
        positioned_image = next(
            e for e in root_section.elements if e.object_id == "fixed_image"
        )

        # Large font text should be taller than normal
        normal_text = TextElement(
            element_type=ElementType.TEXT, text="Text with large font size"
        )
        normal_height = calculate_text_element_height(
            normal_text, positioned_large_font.size[0]
        )
        assert (
            positioned_large_font.size[1] > normal_height
        ), "Large font text should be taller than normal font text"

        # Narrow text should be taller due to wrapping
        wide_text = TextElement(element_type=ElementType.TEXT, text=narrow_text.text)
        wide_height = calculate_text_element_height(
            wide_text, layout_manager.position_calculator.body_width
        )
        assert (
            positioned_narrow.size[1] > wide_height
        ), "Narrow text should be taller due to wrapping"

        # Fixed image should have exact specified height
        assert (
            abs(positioned_image.size[1] - 150) < 1
        ), "Image with height directive should have exact specified height"

    def test_metrics_consistency_in_unified_model(self, layout_manager):
        """Test that metrics produce consistent results in the unified layout model."""

        # Create identical content for both explicit section and root section scenarios
        test_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is test content that should have consistent metrics regardless of section configuration",
            object_id="test_text",
        )

        test_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="Consistent item 1"),
                ListItem(text="Consistent item 2"),
                ListItem(text="Consistent item 3"),
            ],
            object_id="test_list",
        )

        # Test 1: Root section (no explicit sections)
        root_slide = Slide(
            object_id="root_section_slide", elements=[test_text, test_list]
        )

        # Test 2: Explicit section
        test_section = Section(
            id="test_section", type="section", elements=[test_text, test_list]
        )

        explicit_slide = Slide(
            object_id="explicit_section_slide",
            elements=[test_text, test_list],
            sections=[test_section],
        )

        # Calculate both layouts
        root_result = layout_manager.calculate_positions(root_slide)
        explicit_result = layout_manager.calculate_positions(explicit_slide)

        # Extract elements from both results
        root_section = root_result.sections[0]
        root_text = next(e for e in root_section.elements if e.object_id == "test_text")
        root_list = next(e for e in root_section.elements if e.object_id == "test_list")

        explicit_section = explicit_result.sections[0]
        explicit_text = next(
            e for e in explicit_section.elements if e.object_id == "test_text"
        )
        explicit_list = next(
            e for e in explicit_section.elements if e.object_id == "test_list"
        )

        # Heights should be very similar (allowing for small differences in available width)
        assert (
            abs(root_text.size[1] - explicit_text.size[1]) < 5
        ), f"Text height should be consistent: root={root_text.size[1]}, explicit={explicit_text.size[1]}"

        assert (
            abs(root_list.size[1] - explicit_list.size[1]) < 5
        ), f"List height should be consistent: root={root_list.size[1]}, explicit={explicit_list.size[1]}"

    def test_metrics_with_section_constraints(self, layout_manager):
        """Test that metrics work correctly when elements are in constrained sections."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Section Constraints Test"
        )

        # Create content that will be constrained by section width
        wide_content_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a long piece of content that will wrap differently in narrow vs wide sections to test metrics integration",
            object_id="wide_content",
        )

        # Create two sections with different widths
        narrow_section = Section(
            id="narrow_section",
            type="section",
            directives={"width": 0.3},  # 30% width
            elements=[wide_content_text],
        )

        wide_section = Section(
            id="wide_section",
            type="section",
            directives={"width": 0.7},  # 70% width
            elements=[wide_content_text],
        )

        slide = Slide(
            object_id="section_constraints_slide",
            elements=[
                title,
                wide_content_text,
                wide_content_text,
            ],  # Duplicate for both sections
            sections=[narrow_section, wide_section],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Extract elements from sections
        narrow_sec = result_slide.sections[0]
        wide_sec = result_slide.sections[1]

        narrow_text = narrow_sec.elements[0]
        wide_text = wide_sec.elements[0]

        # Narrow section should have taller text due to wrapping
        assert (
            narrow_text.size[1] > wide_text.size[1]
        ), f"Text in narrow section ({narrow_text.size[1]}) should be taller than in wide section ({wide_text.size[1]})"

        # Both should have reasonable dimensions
        assert (
            narrow_text.size[0] < wide_text.size[0]
        ), "Narrow section text should be narrower"
        assert narrow_text.size[1] > 0, "Narrow text should have positive height"
        assert wide_text.size[1] > 0, "Wide text should have positive height"

    def test_metrics_error_handling_and_edge_cases(self, layout_manager):
        """Test that metrics handle error cases and edge conditions gracefully."""

        # Test with very small widths
        text_elem = TextElement(element_type=ElementType.TEXT, text="Test content")
        tiny_width = 5.0

        # Should not crash and should return reasonable height
        height = calculate_text_element_height(text_elem, tiny_width)
        assert height > 0, "Should return positive height even with tiny width"
        assert height < 10000, "Should not return excessive height"

        # Test with very large widths
        huge_width = 10000.0
        height_huge = calculate_text_element_height(text_elem, huge_width)
        assert height_huge > 0, "Should return positive height with huge width"

        # Test with None/invalid elements (should be handled by main dispatcher)
        fallback_height = calculate_element_height(None, 400.0)
        assert fallback_height > 0, "Should return fallback height for None element"

        # Test with missing element_type
        class InvalidElement:
            pass

        invalid_elem = InvalidElement()
        fallback_height_2 = calculate_element_height(invalid_elem, 400.0)
        assert (
            fallback_height_2 > 0
        ), "Should return fallback height for invalid element"

        # Test with zero/negative width
        zero_width_height = calculate_element_height(text_elem, 0.0)
        assert zero_width_height > 0, "Should handle zero width gracefully"

        negative_width_height = calculate_element_height(text_elem, -100.0)
        assert negative_width_height > 0, "Should handle negative width gracefully"

    def test_metrics_performance_characteristics(self, layout_manager):
        """Test that metrics calculations are reasonably efficient in unified model."""

        import time

        # Create a slide with many elements to test performance
        elements = []

        # Add various element types
        for i in range(20):  # 20 text elements
            elements.append(
                TextElement(
                    element_type=ElementType.TEXT,
                    text=f"Performance test text element {i} with some content to measure",
                    object_id=f"perf_text_{i}",
                )
            )

        for i in range(10):  # 10 lists
            elements.append(
                ListElement(
                    element_type=ElementType.BULLET_LIST,
                    items=[ListItem(text=f"List {i} item {j}") for j in range(5)],
                    object_id=f"perf_list_{i}",
                )
            )

        for i in range(5):  # 5 tables
            elements.append(
                TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[[f"R{j}C1", f"R{j}C2"] for j in range(10)],
                    object_id=f"perf_table_{i}",
                )
            )

        # Test with unified model (should create root section)
        slide = Slide(object_id="performance_test_slide", elements=elements)

        # Time the layout calculation
        start_time = time.time()
        result_slide = layout_manager.calculate_positions(slide)
        end_time = time.time()

        calculation_time = end_time - start_time

        # Should complete in reasonable time (adjust threshold based on requirements)
        assert (
            calculation_time < 2.0
        ), f"Layout calculation should complete quickly, took {calculation_time:.2f} seconds"

        # Should have created root section
        assert len(result_slide.sections) == 1, "Should create root section"
        root_section = result_slide.sections[0]

        # All body elements should be in root section
        expected_body_count = len(
            elements
        )  # All elements are body elements (no title/footer)
        assert (
            len(root_section.elements) == expected_body_count
        ), f"Root section should contain all {expected_body_count} body elements"

        for element in root_section.elements:
            assert element.position is not None, "All elements should be positioned"
            assert element.size is not None, "All elements should be sized"

    def test_metrics_with_nested_sections(self, layout_manager):
        """Test that metrics work correctly with nested section layouts."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Nested Sections Metrics Test"
        )

        # Create content for nested sections
        outer_text = TextElement(
            element_type=ElementType.TEXT,
            text="Content in outer section",
            object_id="outer_text",
        )

        inner_text1 = TextElement(
            element_type=ElementType.TEXT,
            text="Content in first inner section",
            object_id="inner_text1",
        )

        inner_text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Content in second inner section with more text to test wrapping behavior",
            object_id="inner_text2",
        )

        # Create nested structure
        inner_section1 = Section(
            id="inner1",
            type="section",
            directives={"height": 0.4},  # 40% of parent height
            elements=[inner_text1],
        )

        inner_section2 = Section(
            id="inner2",
            type="section",
            directives={"height": 0.6},  # 60% of parent height
            elements=[inner_text2],
        )

        outer_section = Section(
            id="outer",
            type="section",
            directives={"width": 0.5},  # 50% of slide width
            subsections=[inner_section1, inner_section2],
        )

        main_section = Section(
            id="main",
            type="section",
            directives={"width": 0.5},  # Other 50% of slide width
            elements=[outer_text],
        )

        slide = Slide(
            object_id="nested_metrics_slide",
            elements=[title, outer_text, inner_text1, inner_text2],
            sections=[main_section, outer_section],
        )

        result_slide = layout_manager.calculate_positions(slide)

        # Verify nested structure is maintained
        assert len(result_slide.sections) == 2, "Should have main sections"

        main_sec = result_slide.sections[0]
        nested_sec = result_slide.sections[1]

        assert len(main_sec.elements) == 1, "Main section should have one element"
        assert (
            len(nested_sec.subsections) == 2
        ), "Nested section should have two subsections"

        # Verify elements are sized appropriately for their containers
        main_element = main_sec.elements[0]
        inner1_element = nested_sec.subsections[0].elements[0]
        inner2_element = nested_sec.subsections[1].elements[0]

        # All should have positive dimensions
        assert main_element.size[0] > 0
        assert main_element.size[1] > 0
        assert inner1_element.size[0] > 0
        assert inner1_element.size[1] > 0
        assert inner2_element.size[0] > 0
        assert inner2_element.size[1] > 0

        # Width should be constrained by section widths
        body_width = layout_manager.position_calculator.body_width
        expected_section_width = body_width * 0.5

        assert (
            abs(main_element.size[0] - expected_section_width) < 20
        ), "Main element width should be constrained by section width"
        assert (
            abs(inner1_element.size[0] - expected_section_width) < 20
        ), "Inner element width should be constrained by section width"

    def test_metrics_integration_with_overflow_scenarios(self, layout_manager):
        """Test metrics integration when content overflows section boundaries."""

        title = TextElement(
            element_type=ElementType.TITLE, text="Overflow Metrics Test"
        )

        # Create very large content
        huge_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column A", "Column B", "Column C", "Column D"],
            rows=[
                [
                    f"Row {i} Cell A with content",
                    f"Row {i} Cell B",
                    f"Row {i} Cell C",
                    f"Row {i} Cell D",
                ]
                for i in range(1, 25)  # 24 rows - will be very tall
            ],
            object_id="huge_table",
        )

        # Put in very small section
        tiny_section = Section(
            id="tiny_section",
            type="section",
            directives={"height": 60, "width": 300},  # Very constrained
            elements=[huge_table],
        )

        slide = Slide(
            object_id="overflow_metrics_slide",
            elements=[title, huge_table],
            sections=[tiny_section],
        )

        # Should not crash despite overflow
        result_slide = layout_manager.calculate_positions(slide)

        section = result_slide.sections[0]
        table_element = section.elements[0]

        # Table should be sized based on content (will overflow)
        assert (
            table_element.size[1] > section.size[1]
        ), f"Table height ({table_element.size[1]}) should exceed section height ({section.size[1]})"

        # Width should be constrained by section
        assert (
            abs(table_element.size[0] - section.size[0]) < 5
        ), "Table width should be constrained by section width"

        # Should have valid position
        assert (
            table_element.position is not None
        ), "Overflowing table should still be positioned"
        assert (
            table_element.position[0] >= section.position[0]
        ), "Table should start within section horizontally"
        assert (
            table_element.position[1] >= section.position[1]
        ), "Table should start within section vertically"
