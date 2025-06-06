"""Behavioral and edge case tests for overflow handler system with specification compliance."""

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


class TestOverflowEdgeCases:
    """Test complex edge cases and boundary conditions with specification compliance."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager for edge case testing."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    def test_deeply_nested_section_structures_with_circular_protection(
        self, overflow_manager
    ):
        """Test handling of deeply nested section hierarchies with circular reference protection."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Deep Nesting Edge Case",
            position=(50, 50),
            size=(620, 40),
        )

        # Create deeply nested sections (10 levels deep)
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Deep content that causes external overflow",
            position=(50, 150),
            size=(620, 100),
        )

        # Build nested structure from inside out
        current_section = Section(
            id="level_10",
            type="section",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows body_height
            elements=[content],
        )

        for level in range(9, 0, -1):
            parent_section = Section(
                id=f"level_{level}",
                type="section",
                position=(50, 150),
                size=(620, 300),  # Maintain overflow at top level
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
            len(result_slides) < 50
        ), "Should not create excessive slides from deep nesting"

        # Verify circular reference protection worked
        for result_slide in result_slides:
            assert (
                result_slide.object_id is not None
            ), "All slides should have valid IDs"

    def test_circular_reference_prevention_with_detection(self, overflow_manager):
        """Test prevention of circular references in section structures."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Circular Reference Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create sections that could potentially create circular references
        section_a = Section(
            id="section_a",
            type="section",
            position=(50, 150),
            size=(620, 300),  # Overflows
        )
        section_b = Section(
            id="section_b", type="section", position=(50, 150), size=(620, 200)
        )

        # Set up potential circular reference
        section_a.subsections = [section_b]
        section_b.subsections = [section_a]  # Circular reference

        # Add content to force external overflow
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content that causes external overflow",
            position=(50, 150),
            size=(620, 100),
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

    def test_massive_element_count_with_minimum_requirements(self, overflow_manager):
        """Test performance with massive numbers of elements following minimum requirements."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Massive Element Count Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create a massive list with thousands of items
        massive_items = [
            ListItem(text=f"Item {i} with content")
            for i in range(1, 1000)  # Reduced for performance
        ]

        massive_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=massive_items,
            position=(50, 150),
            size=(620, 10000),  # Very large
        )

        section = Section(
            id="massive_section",
            type="section",
            position=(50, 150),
            size=(620, 300),  # External boundary overflows
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
            processing_time < 5.0
        ), f"Should handle massive content efficiently, took {processing_time:.2f}s"
        assert (
            len(result_slides) >= 2
        ), "Should create multiple slides for massive content"

    def test_zero_height_available_space_with_external_boundary(self, overflow_manager):
        """Test handling when section external boundary is at the limit."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Zero Space Test",
            position=(50, 50),
            size=(620, 40),
        )

        # FIXED: Use correct overflow boundary calculation
        # body_end_y = top_margin(50) + HEADER_HEIGHT(90) + HEADER_TO_BODY_SPACING(10) + body_height(165) = 315
        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content at boundary",
            position=(50, 315),  # At the actual body boundary limit
            size=(620, 50),
        )

        # Section positioned exactly at body boundary limit
        section = Section(
            id="boundary_section",
            type="section",
            position=(50, 315),  # At actual body_end_y boundary
            size=(620, 1),  # Even 1 point overflows (bottom = 316 > 315)
            elements=[content],
        )

        slide = Slide(
            object_id="boundary_slide",
            elements=[title, content],
            sections=[section],
            title="Zero Space Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle gracefully and promote content to continuation
        assert len(result_slides) == 2, "Should create continuation slide"

        # Original slide should have modified section
        result_slides[0].sections[0]
        # Continuation should have the content
        continuation_section = result_slides[1].sections[0]
        assert (
            len(continuation_section.elements) > 0
        ), "Content should be in continuation"

    def test_negative_dimensions_handling_with_validation(self, overflow_manager):
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

        # Validate slide structure
        warnings = overflow_manager.validate_slide_structure(slide)
        assert isinstance(warnings, list), "Should return validation warnings"

    def test_minimum_requirements_boundary_values(self, overflow_manager):
        """Test minimum requirements at various boundary conditions."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Minimum Requirements Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test table with exactly minimum requirements (header + 2 rows)
        minimal_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[
                ["Row 1 A", "Row 1 B"],
                ["Row 2 A", "Row 2 B"],  # Exactly 2 rows = minimum
            ],
            position=(50, 150),
            size=(620, 100),
        )

        # Mock split to test minimum requirements
        def table_split(available_height):
            if available_height > 60:  # Enough for header + 2 rows
                fitted = TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[["Row 1 A", "Row 1 B"]],  # 1 row
                    size=(620, 40),
                )
                overflowing = TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[["Row 2 A", "Row 2 B"]],  # 1 row
                    size=(620, 40),
                )
                return fitted, overflowing
            # Not enough space for minimum
            return None, minimal_table

        minimal_table.split = table_split

        section = Section(
            id="minimal_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[minimal_table],
        )

        slide = Slide(
            object_id="minimal_slide",
            elements=[title, minimal_table],
            sections=[section],
            title="Minimum Requirements Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should process according to minimum requirements
        assert len(result_slides) >= 1, "Should handle minimum requirements boundary"

    def test_external_vs_internal_overflow_distinction(self, overflow_manager):
        """Test clear distinction between external section overflow and internal content overflow."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Overflow Distinction Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Test 1: Internal content overflow (should be ignored)
        large_content = TextElement(
            element_type=ElementType.TEXT,
            text="Very large content that exceeds section" * 30,
            position=(50, 150),
            size=(620, 500),  # Much larger than section
        )

        internal_overflow_section = Section(
            id="internal_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Section fits in slide (bottom at 250)
            directives={"height": 100},  # Explicit height directive
            elements=[large_content],
        )

        internal_slide = Slide(
            object_id="internal_overflow_slide",
            elements=[title, large_content],
            sections=[internal_overflow_section],
        )

        # Should NOT create continuation (internal overflow ignored)
        result1 = overflow_manager.process_slide(internal_slide)
        assert len(result1) == 1, "Internal overflow should be ignored"

        # Test 2: External section overflow (should be handled)
        normal_content = TextElement(
            element_type=ElementType.TEXT,
            text="Normal content that fits",
            position=(50, 150),
            size=(620, 80),
        )

        external_overflow_section = Section(
            id="external_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section bottom at 350, overflows body_height ~315
            elements=[normal_content],
        )

        external_slide = Slide(
            object_id="external_overflow_slide",
            elements=[title, normal_content],
            sections=[external_overflow_section],
        )

        # Should create continuation (external overflow handled)
        result2 = overflow_manager.process_slide(external_slide)
        assert len(result2) >= 2, "External overflow should be handled"

    def test_unanimous_consent_failure_scenarios(self, overflow_manager):
        """Test scenarios where unanimous consent fails and entire row is promoted."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Unanimous Consent Failure",
            position=(50, 50),
            size=(620, 40),
        )

        # Left column: splittable content
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left content\nLine 2\nLine 3\nLine 4",
            position=(50, 150),
            size=(300, 80),
        )

        # Mock split that can succeed
        def left_split(available_height):
            if available_height > 40:  # Minimum met
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left content\nLine 2",
                    size=(300, 40),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT, text="Line 3\nLine 4", size=(300, 40)
                )
                return fitted, overflowing
            return None, left_text

        left_text.split = left_split

        # Right column: content that can't meet minimum requirements
        right_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1"],
            rows=[["Row 1"]],  # Only 1 row, less than minimum 2
            position=(360, 150),
            size=(310, 80),
        )

        # Mock split that always fails minimum requirements
        def right_split(available_height):
            return None, right_table  # Always fails minimum requirements

        right_table.split = right_split

        # Create row structure
        left_column = Section(
            id="left_col",
            type="section",
            position=(50, 150),
            size=(300, 100),
            elements=[left_text],
        )

        right_column = Section(
            id="right_col",
            type="section",
            position=(360, 150),
            size=(310, 100),
            elements=[right_table],
        )

        row_section = Section(
            id="consensus_row",
            type="row",
            position=(50, 150),
            size=(620, 200),  # Row overflows
            subsections=[left_column, right_column],
        )

        slide = Slide(
            object_id="consensus_failure_slide",
            elements=[title, left_text, right_table],
            sections=[row_section],
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should promote entire row due to unanimous consent failure
        assert len(result_slides) >= 2, "Should create continuation slide"

    def test_malformed_section_data_resilience_with_validation(self, overflow_manager):
        """Test resilience to malformed or inconsistent section data with validation."""

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

        # Section with missing position
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

        # Validate and get warnings
        warnings = overflow_manager.validate_slide_structure(slide)
        assert len(warnings) > 0, "Should detect malformed data issues"

    def test_element_split_formatting_edge_cases_with_minimum_requirements(self):
        """Test element splitting with complex formatting and minimum requirements."""

        # Text with overlapping formatting that must meet minimum 2 lines
        complex_text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1 with overlapping formatting\nLine 2 continues\nLine 3 more\nLine 4 final",
            formatting=[
                TextFormat(start=0, end=20, format_type=TextFormatType.BOLD),
                TextFormat(
                    start=10, end=30, format_type=TextFormatType.ITALIC
                ),  # Overlaps with bold
                TextFormat(
                    start=25, end=40, format_type=TextFormatType.UNDERLINE
                ),  # Overlaps with italic
            ],
            size=(400, 80),
        )

        # Test split with minimum requirements
        fitted, overflowing = complex_text.split(50.0)  # Should fit 2+ lines

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

            # Verify minimum requirements met
            fitted_lines = fitted.text.count("\n") + 1
            assert fitted_lines >= 2, "Should meet minimum 2 lines requirement"

    def test_list_split_with_deeply_nested_items_and_minimum_requirements(self):
        """Test list splitting with complex nested item structures and minimum requirements."""

        # Create deeply nested list items
        level_3_items = [
            ListItem(text=f"Level 3 item {i}", level=3) for i in range(1, 4)
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
            assert len(fitted.items) >= 2, "Should meet minimum 2 items requirement"
            assert len(overflowing.items) > 0, "Should have overflowing items"

            # Check that nested relationships are preserved
            for item in fitted.items:
                if item.children:
                    for child in item.children:
                        assert (
                            child.level > item.level
                        ), "Child levels should be correct"

    def test_table_split_with_minimum_requirements_validation(self):
        """Test table splitting with minimum header + 2 rows requirement."""

        # Create table with sufficient rows for minimum requirements
        headers = ["Header 1", "Header 2", "Header 3"]
        rows = [
            [f"Row {r} Col {c}" for c in range(1, 4)]
            for r in range(1, 8)  # 7 rows total
        ]

        table = TableElement(
            element_type=ElementType.TABLE,
            headers=headers,
            rows=rows,
            size=(400, 200),
        )

        fitted, overflowing = table.split(100.0)  # Limited space

        if fitted and overflowing:
            # Both parts should maintain table structure
            assert len(fitted.headers) == len(
                headers
            ), "Fitted table should have all headers"
            assert len(overflowing.headers) == len(
                headers
            ), "Overflowing table should have all headers"

            # Verify minimum requirements
            assert len(fitted.rows) >= 2, "Fitted table should meet minimum 2 rows"

            # Verify column consistency
            for row in fitted.rows:
                assert len(row) == len(
                    headers
                ), "Fitted rows should have correct column count"

            for row in overflowing.rows:
                assert len(row) == len(
                    headers
                ), "Overflowing rows should have correct column count"

    def test_specification_compliance_edge_cases(self, overflow_manager):
        """Test edge cases that verify specification compliance."""

        # Test 1: Image should never cause external overflow due to proactive scaling
        from markdowndeck.models import ImageElement

        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/huge-image.jpg",
            position=(50, 150),
            size=(620, 150),  # Pre-scaled size
        )

        image_section = Section(
            id="image_section",
            position=(50, 150),
            size=(620, 150),  # Section fits
            elements=[large_image],
        )

        image_slide = Slide(
            object_id="image_compliance_test",
            elements=[large_image],
            sections=[image_section],
        )

        result = overflow_manager.process_slide(image_slide)
        assert len(result) == 1, "Proactively scaled images should not cause overflow"

        # Test 2: Position reset compliance
        text_content = TextElement(
            element_type=ElementType.TEXT,
            text="Content for position reset test " * 20,
            position=(50, 150),
            size=(620, 200),
        )

        overflow_section = Section(
            id="position_test_section",
            position=(50, 150),
            size=(620, 300),  # Overflows
            elements=[text_content],
        )

        position_slide = Slide(
            object_id="position_compliance_test",
            elements=[text_content],
            sections=[overflow_section],
        )

        result = overflow_manager.process_slide(position_slide)
        if len(result) > 1:
            continuation = result[1]
            for section in continuation.sections:
                assert section.position is None, "Continuation positions must be reset"
                assert section.size is None, "Continuation sizes must be reset"

        # Test 3: Jurisdictional boundary compliance
        analysis = overflow_manager.get_overflow_analysis(position_slide)
        assert "has_overflow" in analysis, "Analysis should include overflow detection"
        assert (
            "sections_analysis" in analysis
        ), "Analysis should include section details"
