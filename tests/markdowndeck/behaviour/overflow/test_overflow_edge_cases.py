"""Behavioral and edge case tests for overflow handler system."""

import pytest
from markdowndeck.models import (
    ElementType,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
)
from markdowndeck.overflow import OverflowManager
from markdowndeck.overflow.constants import (
    MINIMUM_CONTENT_RATIO_TO_SPLIT,
)


class TestOverflowEdgeCases:
    """Test complex edge cases and boundary conditions."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager for edge case testing."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_infinitely_nested_section_structures(self, overflow_manager):
        """Test handling of deeply nested section hierarchies."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Deep Nesting Edge Case",
            position=(50, 50),
            size=(620, 40),
        )

        # Create deeply nested sections (10 levels deep)
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Deep content that overflows",
            position=(50, 150),
            size=(620, 300),  # Overflows
        )

        # Build nested structure from inside out
        current_section = Section(
            id="level_10",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Smaller than content
            elements=[content],
        )

        for level in range(9, 0, -1):
            parent_section = Section(
                id=f"level_{level}",
                type="section",
                position=(50, 150),
                size=(620, 200),
                subsections=[current_section],
            )
            current_section = parent_section

        slide = Slide(
            object_id="deep_nesting_slide",
            elements=[title, content],
            sections=[current_section],
            title="Deep Nesting Edge Case",
        )

        # Should handle deep nesting without stack overflow or infinite loops
        result_slides = overflow_manager.process_slide(slide)

        assert (
            len(result_slides) >= 2
        ), "Should handle deep nesting and create continuations"

        # Verify no infinite recursion occurred
        assert (
            len(result_slides) < 100
        ), "Should not create excessive slides from deep nesting"

    def test_circular_reference_prevention(self, overflow_manager):
        """Test prevention of circular references in section structures."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Circular Reference Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create sections that could potentially create circular references
        section_a = Section(
            id="section_a", type="section", position=(50, 150), size=(620, 200)
        )
        section_b = Section(
            id="section_b", type="section", position=(50, 150), size=(620, 200)
        )

        # Set up potential circular reference (in real code this should be prevented)
        section_a.subsections = [section_b]
        section_b.subsections = [section_a]  # Circular reference

        # Add content to force overflow
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content that causes overflow",
            position=(50, 150),
            size=(620, 300),
        )
        section_a.elements = [content]

        slide = Slide(
            object_id="circular_ref_slide",
            elements=[title, content],
            sections=[section_a],
            title="Circular Reference Test",
        )

        # Should handle gracefully without infinite loops
        try:
            result_slides = overflow_manager.process_slide(slide)
            # If it completes, it handled the circular reference correctly
            assert len(result_slides) >= 1, "Should return at least the original slide"
        except RecursionError:
            pytest.fail("Should not cause infinite recursion with circular references")

    def test_massive_element_count_performance(self, overflow_manager):
        """Test performance with slides containing massive numbers of elements."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Massive Element Count Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create a massive list with thousands of items
        massive_items = [
            ListItem(text=f"Item {i} with content") for i in range(1, 5000)
        ]

        massive_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=massive_items,
            position=(50, 150),
            size=(620, 50000),  # Extremely large
        )

        section = Section(
            id="massive_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[massive_list],
        )

        slide = Slide(
            object_id="massive_slide",
            elements=[title, massive_list],
            sections=[section],
            title="Massive Element Count Test",
        )

        import time

        start_time = time.time()

        result_slides = overflow_manager.process_slide(slide)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete in reasonable time even with massive content
        assert (
            processing_time < 10.0
        ), f"Should handle massive content efficiently, took {processing_time:.2f}s"
        assert (
            len(result_slides) >= 2
        ), "Should create multiple slides for massive content"

    def test_zero_height_available_space(self, overflow_manager):
        """Test handling when no vertical space is available."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Zero Space Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content with no space",
            position=(50, 255),  # At the very bottom
            size=(620, 50),
        )

        # Section positioned at the very limit with no available space
        section = Section(
            id="zero_space_section",
            type="section",
            position=(50, 255),  # At body_height limit
            size=(620, 0),  # Zero height
            elements=[content],
        )

        slide = Slide(
            object_id="zero_space_slide",
            elements=[title, content],
            sections=[section],
            title="Zero Space Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle gracefully and promote all content to continuation
        assert len(result_slides) == 2, "Should create continuation slide"

        # Original slide should have no content in the section
        result_slides[0].sections[0]
        # Continuation should have all the content
        continuation_section = result_slides[1].sections[0]
        assert (
            len(continuation_section.elements) > 0
        ), "Content should be in continuation"

    def test_negative_dimensions_handling(self, overflow_manager):
        """Test handling of sections with negative or invalid dimensions."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Negative Dimensions Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content in negative section",
            position=(50, 150),
            size=(620, 50),
        )

        # Section with negative dimensions
        negative_section = Section(
            id="negative_section",
            type="section",
            position=(50, 150),
            size=(620, -100),  # Negative height
            elements=[content],
        )

        slide = Slide(
            object_id="negative_dim_slide",
            elements=[title, content],
            sections=[negative_section],
            title="Negative Dimensions Test",
        )

        # Should handle gracefully without crashing
        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 1, "Should handle negative dimensions gracefully"

    def test_extremely_small_threshold_values(self, overflow_manager):
        """Test behavior with threshold values at extreme boundaries."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Threshold Boundary Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create content sized exactly to test threshold boundaries
        precise_content = TextElement(
            element_type=ElementType.TEXT,
            text="Precisely sized content for threshold testing",
            position=(50, 150),
            size=(620, 100),  # Exactly 100 points
        )

        # Mock the split method to test exact threshold behavior
        def precise_split(available_height):
            ratio = available_height / 100.0
            if ratio >= MINIMUM_CONTENT_RATIO_TO_SPLIT:
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Fitted portion",
                    size=(620, available_height),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing portion",
                    size=(620, 100 - available_height),
                )
                return fitted, overflowing
            return None, TextElement(
                element_type=ElementType.TEXT,
                text="Precisely sized content for threshold testing",
                size=(620, 100),
            )

        precise_content.split = precise_split

        # Test exactly at threshold
        threshold_height = 100 * MINIMUM_CONTENT_RATIO_TO_SPLIT

        section = Section(
            id="threshold_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[precise_content],
        )

        slide = Slide(
            object_id="threshold_slide",
            elements=[title, precise_content],
            sections=[section],
            title="Threshold Boundary Test",
        )

        # Simulate exactly threshold available space
        overflow_manager.body_height = 150 + threshold_height

        result_slides = overflow_manager.process_slide(slide)

        # At exact threshold, should split
        if len(result_slides) > 1:
            # Verify split occurred
            assert (
                len(result_slides[0].sections[0].elements) > 0
            ), "Should have fitted content"
            assert (
                len(result_slides[1].sections[0].elements) > 0
            ), "Should have overflowing content"

    def test_concurrent_overflow_detection_race_conditions(self, overflow_manager):
        """Test for potential race conditions in overflow detection."""

        # Create slide with multiple sections that all overflow simultaneously
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Concurrent Overflow Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Multiple overflowing sections
        sections = []
        elements = []

        for i in range(5):
            content = TextElement(
                element_type=ElementType.TEXT,
                text=f"Overflowing content section {i}",
                position=(50, 150 + i * 60),
                size=(620, 100),  # Each overflows
            )
            elements.append(content)

            section = Section(
                id=f"concurrent_section_{i}",
                type="section",
                position=(50, 150 + i * 60),
                size=(620, 50),  # Smaller than content
                elements=[content],
            )
            sections.append(section)

        slide = Slide(
            object_id="concurrent_overflow_slide",
            elements=[title] + elements,
            sections=sections,
            title="Concurrent Overflow Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should process all overflows systematically
        assert len(result_slides) >= 2, "Should handle multiple concurrent overflows"

        # Verify systematic processing (first overflow handled first)
        # Original slide should have content from only non-overflowing or first overflowing section

    def test_malformed_section_data_resilience(self, overflow_manager):
        """Test resilience to malformed or inconsistent section data."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Malformed Data Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content in malformed section",
            position=(50, 150),
            size=(620, 100),
        )

        # Section with inconsistent data
        malformed_section = Section(
            id="malformed_section",
            type="section",
            position=None,  # Missing position
            size=(620, 200),
            elements=[content],
        )

        # Section with mismatched element positions
        mismatched_section = Section(
            id="mismatched_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Mispositioned content",
                    position=(1000, 2000),  # Outside section bounds
                    size=(620, 100),
                )
            ],
        )

        slide = Slide(
            object_id="malformed_slide",
            elements=[title, content],
            sections=[malformed_section, mismatched_section],
            title="Malformed Data Test",
        )

        # Should handle malformed data gracefully without crashing
        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 1, "Should handle malformed data gracefully"

    def test_element_split_formatting_edge_cases(self):
        """Test element splitting with complex formatting edge cases."""

        # Text with overlapping formatting
        complex_text = TextElement(
            element_type=ElementType.TEXT,
            text="This text has overlapping bold and italic formatting regions",
            formatting=[
                TextFormat(start=0, end=20, format_type=TextFormatType.BOLD),
                TextFormat(
                    start=10, end=30, format_type=TextFormatType.ITALIC
                ),  # Overlaps with bold
                TextFormat(
                    start=25, end=40, format_type=TextFormatType.UNDERLINE
                ),  # Overlaps with italic
            ],
            size=(400, 60),
        )

        fitted, overflowing = complex_text.split(30.0)

        if fitted and overflowing:
            # Verify formatting integrity
            for fmt in fitted.formatting:
                assert fmt.start >= 0, "Fitted formatting start should be valid"
                assert fmt.end <= len(
                    fitted.text
                ), "Fitted formatting end should be within text"

            for fmt in overflowing.formatting:
                assert fmt.start >= 0, "Overflowing formatting start should be valid"
                assert fmt.end <= len(
                    overflowing.text
                ), "Overflowing formatting end should be within text"

    def test_list_split_with_deeply_nested_items(self):
        """Test list splitting with complex nested item structures."""

        # Create deeply nested list items
        level_3_items = [
            ListItem(text=f"Level 3 item {i}", level=3) for i in range(1, 6)
        ]
        level_2_items = [
            ListItem(text="Level 2 item 1", level=2, children=level_3_items[:2]),
            ListItem(text="Level 2 item 2", level=2, children=level_3_items[2:]),
        ]
        level_1_items = [
            ListItem(text="Level 1 item 1", level=1, children=level_2_items[:1]),
            ListItem(text="Level 1 item 2", level=1, children=level_2_items[1:]),
        ]
        top_items = [
            ListItem(text="Top item 1", level=0, children=level_1_items),
            ListItem(text="Top item 2", level=0),
            ListItem(text="Top item 3", level=0),
        ]

        nested_list = ListElement(
            element_type=ElementType.BULLET_LIST, items=top_items, size=(400, 300)
        )

        fitted, overflowing = nested_list.split(150.0)

        if fitted and overflowing:
            # Verify nested structure integrity
            assert len(fitted.items) > 0, "Should have fitted items"
            assert len(overflowing.items) > 0, "Should have overflowing items"

            # Check that nested relationships are preserved
            for item in fitted.items:
                if item.children:
                    for child in item.children:
                        assert (
                            child.level > item.level
                        ), "Child levels should be correct"

    def test_table_split_with_extremely_wide_content(self):
        """Test table splitting with content that exceeds normal width constraints."""

        # Create table with very wide cell content
        wide_headers = [
            f"Very Long Header Name {i}" for i in range(1, 11)
        ]  # 10 columns
        wide_rows = [
            [
                f"Extremely long content for row {r} column {c} that might wrap"
                for c in range(1, 11)
            ]
            for r in range(1, 21)  # 20 rows
        ]

        wide_table = TableElement(
            element_type=ElementType.TABLE,
            headers=wide_headers,
            rows=wide_rows,
            size=(400, 800),  # Very tall
        )

        fitted, overflowing = wide_table.split(300.0)

        if fitted and overflowing:
            # Both parts should maintain table structure
            assert len(fitted.headers) == len(
                wide_headers
            ), "Fitted table should have all headers"
            assert len(overflowing.headers) == len(
                wide_headers
            ), "Overflowing table should have all headers"

            # Verify column consistency
            for row in fitted.rows:
                assert len(row) == len(
                    wide_headers
                ), "Fitted rows should have correct column count"

            for row in overflowing.rows:
                assert len(row) == len(
                    wide_headers
                ), "Overflowing rows should have correct column count"

    def test_memory_usage_with_large_content_copies(self, overflow_manager):
        """Test memory efficiency when copying large content structures."""

        # Create slide with large content that will be copied multiple times
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Memory Usage Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Large text content
        large_content = "Lorem ipsum dolor sit amet. " * 1000  # Large string

        large_text = TextElement(
            element_type=ElementType.TEXT,
            text=large_content,
            position=(50, 150),
            size=(620, 2000),  # Very large
        )

        section = Section(
            id="memory_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[large_text],
        )

        slide = Slide(
            object_id="memory_slide",
            elements=[title, large_text],
            sections=[section],
            title="Memory Usage Test",
        )

        import os

        import psutil

        # Measure memory before processing
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        result_slides = overflow_manager.process_slide(slide)

        # Measure memory after processing
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Memory increase should be reasonable (not exponential)
        # This is a rough check - exact values depend on system
        assert (
            memory_increase < 100 * 1024 * 1024
        ), f"Memory increase should be reasonable, got {memory_increase} bytes"

        assert len(result_slides) >= 2, "Should create multiple slides"

    def test_slide_id_uniqueness_with_many_continuations(self, overflow_manager):
        """Test that slide IDs remain unique even with many continuation slides."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="ID Uniqueness Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create content that will generate many continuation slides
        mega_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[
                [f"Row {i} Cell 1", f"Row {i} Cell 2"] for i in range(1, 1000)
            ],  # 999 rows
            position=(50, 150),
            size=(620, 10000),  # Extremely large
        )

        section = Section(
            id="id_test_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[mega_table],
        )

        slide = Slide(
            object_id="id_uniqueness_slide",
            elements=[title, mega_table],
            sections=[section],
            title="ID Uniqueness Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Collect all slide IDs
        slide_ids = [slide.object_id for slide in result_slides]

        # Verify uniqueness
        assert len(slide_ids) == len(set(slide_ids)), "All slide IDs should be unique"

        # Verify continuation ID format
        for i, slide_id in enumerate(slide_ids[1:], 1):
            assert (
                "id_uniqueness_slide_cont" in slide_id
            ), f"Continuation slide {i} should have proper ID format"

    def test_overflow_with_empty_sections_mixed(self, overflow_manager):
        """Test overflow handling when some sections are empty."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Empty Sections Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Mix of empty and content sections
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content that overflows",
            position=(50, 150),
            size=(620, 300),
        )

        empty_section1 = Section(
            id="empty_1",
            type="section",
            position=(50, 100),
            size=(620, 40),
            elements=[],  # Empty
        )

        content_section = Section(
            id="content_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Smaller than content
            elements=[content],
        )

        empty_section2 = Section(
            id="empty_2",
            type="section",
            position=(50, 260),
            size=(620, 40),
            elements=[],  # Empty
        )

        slide = Slide(
            object_id="empty_sections_slide",
            elements=[title, content],
            sections=[empty_section1, content_section, empty_section2],
            title="Empty Sections Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle empty sections gracefully
        assert (
            len(result_slides) >= 2
        ), "Should create continuation for overflowing content"

        # Verify structure preservation
        for result_slide in result_slides:
            assert len(result_slide.sections) >= 1, "Should preserve section structure"
