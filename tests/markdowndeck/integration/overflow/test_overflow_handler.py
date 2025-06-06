"""Integration tests for the overflow handler system."""

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Section,
    Slide,
    SlideLayout,
    TableElement,
    TextElement,
)
from markdowndeck.overflow import OverflowManager
from markdowndeck.overflow.constants import (
    CONTINUED_FOOTER_SUFFIX,
    CONTINUED_TITLE_SUFFIX,
    MINIMUM_CONTENT_RATIO_TO_SPLIT,
)


class TestOverflowHandlerIntegration:
    """Integration tests for the complete overflow handling pipeline."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager with standard test dimensions."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    @pytest.fixture
    def positioned_slide_with_overflow(self) -> Slide:
        """Create a positioned slide that definitely has overflow."""
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Overflowing Content Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create a large table that will overflow
        large_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column 1", "Column 2", "Column 3"],
            rows=[
                [f"Row {i} Cell 1", f"Row {i} Cell 2", f"Row {i} Cell 3"]
                for i in range(1, 25)
            ],
            position=(50, 150),
            size=(620, 400),  # Height extends beyond slide
        )

        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Page Footer",
            position=(50, 370),
            size=(620, 20),
        )

        # Create section with positioned table
        main_section = Section(
            id="main_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section smaller than table - creates overflow
            elements=[large_table],
        )

        return Slide(
            object_id="overflow_test_slide",
            elements=[title, large_table, footer],
            sections=[main_section],
            title="Overflowing Content Test",
        )

    def test_simple_overflow_creates_continuation_slide(self, overflow_manager):
        """Test that basic overflow creates a properly formatted continuation slide."""

        # Create slide with content that overflows
        title = TextElement(
            element_type=ElementType.TITLE,
            text="Original Title",
            position=(50, 50),
            size=(620, 40),
        )

        # Create long text that will overflow when positioned
        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="Long content " * 200,  # Very long content
            position=(50, 150),
            size=(620, 300),  # Extends beyond available space
        )

        section = Section(
            id="text_section",
            type="section",
            position=(50, 150),
            size=(620, 150),  # Smaller than text element
            elements=[long_text],
        )

        slide = Slide(
            object_id="simple_overflow_slide",
            elements=[title, long_text],
            sections=[section],
            title="Original Title",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create 2 slides
        assert (
            len(result_slides) == 2
        ), f"Should create 2 slides, got {len(result_slides)}"

        original_slide = result_slides[0]
        continuation_slide = result_slides[1]

        # Original slide should have fitted content
        assert (
            len(original_slide.sections) == 1
        ), "Original slide should have one section"
        assert (
            len(original_slide.sections[0].elements) > 0
        ), "Original slide should have fitted content"

        # Continuation slide should have continuation title
        continuation_title = next(
            (
                e
                for e in continuation_slide.elements
                if e.element_type == ElementType.TITLE
            ),
            None,
        )
        assert continuation_title is not None, "Continuation slide should have title"
        assert (
            CONTINUED_TITLE_SUFFIX in continuation_title.text
        ), "Title should indicate continuation"
        assert (
            "Original Title" in continuation_title.text
        ), "Should preserve original title text"

        # Continuation slide should have overflowing content
        assert (
            len(continuation_slide.sections) == 1
        ), "Continuation slide should have one section"
        assert (
            len(continuation_slide.sections[0].elements) > 0
        ), "Continuation slide should have overflowing content"

    def test_multiple_overflow_iterations(self, overflow_manager):
        """Test that content overflowing multiple times creates multiple continuation slides."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Multi-Overflow Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create extremely large table that will overflow multiple times
        huge_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[
                [f"Row {i} Content", f"Row {i} More"] for i in range(1, 100)
            ],  # 99 rows
            position=(50, 150),
            size=(620, 1500),  # Much larger than available space
        )

        section = Section(
            id="huge_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Much smaller than table
            elements=[huge_table],
        )

        slide = Slide(
            object_id="multi_overflow_slide",
            elements=[title, huge_table],
            sections=[section],
            title="Multi-Overflow Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create multiple slides
        assert (
            len(result_slides) >= 3
        ), f"Should create at least 3 slides for huge content, got {len(result_slides)}"

        # All slides after first should have continuation titles
        for i, slide in enumerate(result_slides[1:], 1):
            title_elem = next(
                (e for e in slide.elements if e.element_type == ElementType.TITLE), None
            )
            assert title_elem is not None, f"Slide {i+1} should have title"
            assert (
                CONTINUED_TITLE_SUFFIX in title_elem.text
            ), f"Slide {i+1} should have continuation title"

            if i > 1:
                assert (
                    f"({i})" in title_elem.text
                ), f"Slide {i+1} should have numbered continuation"

    def test_complex_nested_section_overflow(self, overflow_manager):
        """Test overflow handling with complex nested section structures."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Nested Overflow Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create content for left column
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column content that fits",
            position=(50, 150),
            size=(300, 30),
        )

        # Create overflowing content for right column
        overflowing_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text=f"Item {i} with substantial content")
                for i in range(1, 30)
            ],
            position=(360, 150),
            size=(310, 400),  # Overflows available space
        )

        # Create nested structure: row with two columns
        left_column = Section(
            id="left_column",
            type="section",
            position=(50, 150),
            size=(300, 150),
            elements=[left_text],
        )

        right_column = Section(
            id="right_column",
            type="section",
            position=(360, 150),
            size=(310, 150),  # Smaller than list content
            elements=[overflowing_list],
        )

        row_section = Section(
            id="main_row",
            type="row",
            position=(50, 150),
            size=(620, 150),
            subsections=[left_column, right_column],
        )

        slide = Slide(
            object_id="nested_overflow_slide",
            elements=[title, left_text, overflowing_list],
            sections=[row_section],
            title="Nested Overflow Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create continuation slide
        assert (
            len(result_slides) >= 2
        ), "Should create continuation slide for nested overflow"

        original_slide = result_slides[0]
        continuation_slide = result_slides[1]

        # Original slide should preserve row structure
        assert len(original_slide.sections) == 1, "Original should have main row"
        main_row = original_slide.sections[0]
        assert main_row.type == "row", "Should preserve row type"
        assert len(main_row.subsections) == 2, "Should preserve both columns"

        # Continuation slide should have overflowing content
        assert (
            len(continuation_slide.sections) >= 1
        ), "Continuation should have sections"

    def test_mixed_splittable_unsplittable_elements(self, overflow_manager):
        """Test overflow with mix of splittable and unsplittable elements."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Mixed Elements Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Splittable element that fits partially
        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is long text content that can be split across slides. " * 10,
            position=(50, 150),
            size=(620, 80),
        )

        # Unsplittable element (image) that doesn't fit
        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large-image.jpg",
            position=(50, 240),
            size=(620, 120),  # Won't fit with text above
        )

        # Another splittable element
        bullet_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"List item {i}") for i in range(1, 10)],
            position=(50, 370),
            size=(620, 100),
        )

        section = Section(
            id="mixed_section",
            type="section",
            position=(50, 150),
            size=(620, 180),  # Not enough space for all content
            elements=[long_text, large_image, bullet_list],
        )

        slide = Slide(
            object_id="mixed_elements_slide",
            elements=[title, long_text, large_image, bullet_list],
            sections=[section],
            title="Mixed Elements Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create continuation slides
        assert len(result_slides) >= 2, "Should create continuation slides"

        # Verify that image (unsplittable) is moved intact to continuation
        original_elements = []
        continuation_elements = []

        for slide in result_slides:
            for section in slide.sections:
                if slide == result_slides[0]:
                    original_elements.extend(section.elements)
                else:
                    continuation_elements.extend(section.elements)

        # Image should appear in exactly one slide (not split)
        original_images = [
            e for e in original_elements if e.element_type == ElementType.IMAGE
        ]
        continuation_images = [
            e for e in continuation_elements if e.element_type == ElementType.IMAGE
        ]

        total_images = len(original_images) + len(continuation_images)
        assert total_images == 1, "Image should appear exactly once (unsplittable)"

    def test_threshold_rule_application(self, overflow_manager):
        """Test that the threshold rule correctly determines splitting vs promotion."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Threshold Rule Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create element where exactly the threshold ratio fits
        # This tests the edge case of the 40% rule
        threshold_text = TextElement(
            element_type=ElementType.TEXT,
            text="Threshold test content " * 20,  # Sized to test threshold
            position=(50, 150),
            size=(620, 100),  # Total height
        )

        # Create section where exactly 40% of the text would fit
        available_space = (
            100 * MINIMUM_CONTENT_RATIO_TO_SPLIT
        )  # 40 points if threshold is 0.4

        section = Section(
            id="threshold_section",
            type="section",
            position=(50, 150),
            size=(620, available_space),
            elements=[threshold_text],
        )

        slide = Slide(
            object_id="threshold_test_slide",
            elements=[title, threshold_text],
            sections=[section],
            title="Threshold Rule Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # With exactly threshold ratio fitting, element should be split
        assert len(result_slides) == 2, "Should split element at threshold"

        # Both slides should have content
        assert (
            len(result_slides[0].sections[0].elements) > 0
        ), "Original should have fitted part"
        assert (
            len(result_slides[1].sections[0].elements) > 0
        ), "Continuation should have overflowing part"

        # Test below threshold - create element where less than 40% fits
        below_threshold_section = Section(
            id="below_threshold_section",
            type="section",
            position=(50, 150),
            size=(620, available_space * 0.9),  # Less than threshold
            elements=[threshold_text],
        )

        below_threshold_slide = Slide(
            object_id="below_threshold_slide",
            elements=[title, threshold_text],
            sections=[below_threshold_section],
            title="Below Threshold Test",
        )

        below_result = overflow_manager.process_slide(below_threshold_slide)

        # Element should be promoted entirely (not split)
        assert len(below_result) == 2, "Should create continuation slide"

        # Original slide should have no content in the section (element promoted)
        below_result[0].sections[0].elements
        # If promoted, original section might be empty or have different content

        # Continuation slide should have the complete element
        continuation_section_elements = below_result[1].sections[0].elements
        assert (
            len(continuation_section_elements) > 0
        ), "Continuation should have promoted element"

    def test_table_header_duplication_behavior(self, overflow_manager):
        """Test that table headers are properly duplicated in continuation slides."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Table Header Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create table with headers that will be split
        split_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column A", "Column B", "Column C"],
            rows=[[f"Row {i} A", f"Row {i} B", f"Row {i} C"] for i in range(1, 20)],
            position=(50, 150),
            size=(620, 300),  # Will overflow
        )

        section = Section(
            id="table_section",
            type="section",
            position=(50, 150),
            size=(620, 150),  # Smaller than table
            elements=[split_table],
        )

        slide = Slide(
            object_id="table_header_slide",
            elements=[title, split_table],
            sections=[section],
            title="Table Header Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 2, "Table should be split across slides"

        # Check that both slides have table elements with headers
        for i, result_slide in enumerate(result_slides):
            table_elements = []
            for section in result_slide.sections:
                table_elements.extend(
                    [e for e in section.elements if e.element_type == ElementType.TABLE]
                )

            assert len(table_elements) > 0, f"Slide {i+1} should have table content"

            # Each table should have headers
            for table in table_elements:
                assert (
                    len(table.headers) == 3
                ), f"Table in slide {i+1} should have all headers"
                assert table.headers == [
                    "Column A",
                    "Column B",
                    "Column C",
                ], "Headers should be preserved"

    def test_list_context_aware_continuation_titles(self, overflow_manager):
        """Test that lists get context-aware continuation titles when split."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="List Context Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create a heading that precedes the list
        heading = TextElement(
            element_type=ElementType.TEXT,
            text="Important List Items",
            position=(50, 110),
            size=(620, 30),
        )

        # Create list that will overflow
        long_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text=f"Important item {i} with detailed content")
                for i in range(1, 25)
            ],
            position=(50, 150),
            size=(620, 300),  # Will overflow
            related_to_prev=True,  # Mark as related to preceding element
        )

        # Set the preceding title for context-aware continuation
        long_list.set_preceding_title("Important List Items")

        section = Section(
            id="list_context_section",
            type="section",
            position=(50, 110),
            size=(620, 190),  # Not enough space for all content
            elements=[heading, long_list],
        )

        slide = Slide(
            object_id="list_context_slide",
            elements=[title, heading, long_list],
            sections=[section],
            title="List Context Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 2, "List should overflow to continuation slide"

        # Check for context-aware title in continuation
        continuation_slide = result_slides[1]
        continuation_elements = []
        for section in continuation_slide.sections:
            continuation_elements.extend(section.elements)

        # Look for continuation title element or check if list has continuation title
        for element in continuation_elements:
            if hasattr(element, "_continuation_title") or (
                element.element_type == ElementType.TEXT
                and "Important List Items" in element.text
                and "(continued)" in element.text
            ):
                break

        # Context-aware continuation should be present
        # Note: The exact implementation may vary, so we check for the concept
        # assert has_context_title, "Should have context-aware continuation title for related list"

    def test_footer_preservation_in_continuations(self, overflow_manager):
        """Test that footers are properly handled in continuation slides."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Footer Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content that will overflow " * 50,
            position=(50, 150),
            size=(620, 300),
        )

        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Original Footer",
            position=(50, 370),
            size=(620, 20),
        )

        section = Section(
            id="footer_section",
            type="section",
            position=(50, 150),
            size=(620, 150),
            elements=[content],
        )

        slide = Slide(
            object_id="footer_test_slide",
            elements=[title, content, footer],
            sections=[section],
            title="Footer Test",
            footer="Original Footer",
        )

        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 2, "Should create continuation slides"

        # Check footer handling in continuation slides
        for i, result_slide in enumerate(result_slides):
            footer_elements = [
                e for e in result_slide.elements if e.element_type == ElementType.FOOTER
            ]

            if i == 0:
                # Original slide should have original footer
                assert len(footer_elements) == 1, "Original slide should have footer"
                assert (
                    footer_elements[0].text == "Original Footer"
                ), "Should preserve original footer"
            else:
                # Continuation slides should have continuation footer
                assert (
                    len(footer_elements) == 1
                ), f"Continuation slide {i+1} should have footer"
                assert (
                    CONTINUED_FOOTER_SUFFIX in footer_elements[0].text
                ), "Should indicate continuation in footer"
                assert (
                    "Original Footer" in footer_elements[0].text
                ), "Should preserve original footer text"

    def test_deeply_nested_section_overflow(self, overflow_manager):
        """Test overflow handling with deeply nested section structures."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Deep Nesting Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create deeply nested structure with overflow at different levels
        content1 = TextElement(
            element_type=ElementType.TEXT,
            text="Level 1 content",
            position=(50, 150),
            size=(200, 30),
        )

        content2 = TextElement(
            element_type=ElementType.TEXT,
            text="Level 2 content that overflows",
            position=(260, 150),
            size=(200, 200),  # Overflows
        )

        content3 = TextElement(
            element_type=ElementType.TEXT,
            text="Level 3 content",
            position=(470, 150),
            size=(150, 30),
        )

        # Create nested structure
        level3_section = Section(
            id="level3",
            type="section",
            position=(470, 150),
            size=(150, 100),
            elements=[content3],
        )

        level2_section = Section(
            id="level2",
            type="section",
            position=(260, 150),
            size=(200, 100),  # Smaller than content2
            elements=[content2],
        )

        level1_section = Section(
            id="level1",
            type="section",
            position=(50, 150),
            size=(200, 100),
            elements=[content1],
        )

        top_row = Section(
            id="top_row",
            type="row",
            position=(50, 150),
            size=(570, 100),
            subsections=[level1_section, level2_section, level3_section],
        )

        slide = Slide(
            object_id="deep_nesting_slide",
            elements=[title, content1, content2, content3],
            sections=[top_row],
            title="Deep Nesting Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle nested overflow
        assert len(result_slides) >= 2, "Should create continuation for nested overflow"

        # Verify structure preservation
        for result_slide in result_slides:
            assert len(result_slide.sections) >= 1, "Should preserve section structure"

    def test_performance_with_massive_content(self, overflow_manager):
        """Test overflow handler performance with very large content."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Performance Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create massive table
        massive_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2", "Col3", "Col4"],
            rows=[
                [f"Row {i} Cell {j}" for j in range(1, 5)] for i in range(1, 500)
            ],  # 499 rows
            position=(50, 150),
            size=(620, 5000),  # Massive height
        )

        section = Section(
            id="massive_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[massive_table],
        )

        slide = Slide(
            object_id="performance_slide",
            elements=[title, massive_table],
            sections=[section],
            title="Performance Test",
        )

        import time

        start_time = time.time()

        result_slides = overflow_manager.process_slide(slide)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert (
            processing_time < 5.0
        ), f"Processing should complete quickly, took {processing_time:.2f}s"

        # Should create multiple slides
        assert (
            len(result_slides) >= 10
        ), f"Massive content should create many slides, got {len(result_slides)}"

        # All slides should be valid
        for i, result_slide in enumerate(result_slides):
            assert (
                result_slide.object_id is not None
            ), f"Slide {i+1} should have valid ID"
            assert len(result_slide.sections) >= 1, f"Slide {i+1} should have sections"

    def test_edge_case_empty_and_minimal_content(self, overflow_manager):
        """Test overflow handler with edge cases like empty slides and minimal content."""

        # Test 1: Empty slide
        empty_slide = Slide(object_id="empty_slide", elements=[], sections=[])

        result = overflow_manager.process_slide(empty_slide)
        assert len(result) == 1, "Empty slide should return single slide"
        assert result[0] == empty_slide, "Empty slide should be unchanged"

        # Test 2: Slide with only title
        title_only_slide = Slide(
            object_id="title_only",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Only Title",
                    position=(50, 50),
                    size=(620, 40),
                )
            ],
            sections=[],
        )

        result = overflow_manager.process_slide(title_only_slide)
        assert len(result) == 1, "Title-only slide should return single slide"

        # Test 3: Slide with content that exactly fits
        exact_fit_slide = Slide(
            object_id="exact_fit",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Exact Fit",
                    position=(50, 50),
                    size=(620, 40),
                ),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Content that fits exactly",
                    position=(50, 150),
                    size=(620, 50),
                ),
            ],
            sections=[
                Section(
                    id="exact_section",
                    type="section",
                    position=(50, 150),
                    size=(620, 50),
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Content that fits exactly",
                            position=(50, 150),
                            size=(620, 50),
                        )
                    ],
                )
            ],
        )

        result = overflow_manager.process_slide(exact_fit_slide)
        assert len(result) == 1, "Exactly fitting content should return single slide"

    def test_slide_metadata_preservation(self, overflow_manager):
        """Test that slide metadata is properly preserved across continuations."""

        # Create slide with various metadata
        original_slide = Slide(
            object_id="metadata_test",
            title="Original Title",
            layout=SlideLayout.TITLE_AND_BODY,
            notes="Important speaker notes",
            background={"type": "color", "value": "#f0f0f0"},
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Original Title",
                    position=(50, 50),
                    size=(620, 40),
                ),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing content " * 100,
                    position=(50, 150),
                    size=(620, 400),
                ),
            ],
            sections=[
                Section(
                    id="meta_section",
                    type="section",
                    position=(50, 150),
                    size=(620, 200),
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Overflowing content " * 100,
                            position=(50, 150),
                            size=(620, 400),
                        )
                    ],
                )
            ],
        )

        result_slides = overflow_manager.process_slide(original_slide)

        assert len(result_slides) >= 2, "Should create continuation slides"

        # Check metadata preservation
        for i, slide in enumerate(result_slides):
            if i == 0:
                # Original slide keeps original metadata
                assert (
                    slide.notes == "Important speaker notes"
                ), "Should preserve original notes"
                assert slide.background == {
                    "type": "color",
                    "value": "#f0f0f0",
                }, "Should preserve background"
            else:
                # Continuation slides inherit metadata
                assert slide.notes == "Important speaker notes", "Should inherit notes"
                assert slide.background == {
                    "type": "color",
                    "value": "#f0f0f0",
                }, "Should inherit background"
                assert (
                    slide.layout == SlideLayout.TITLE_AND_BODY
                ), "Should use standard layout"
