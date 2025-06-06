"""Unit tests for SlideBuilder component with enhanced position reset and continuation features."""

import pytest
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
from markdowndeck.models.constants import SlideLayout
from markdowndeck.overflow.constants import (
    CONTINUED_FOOTER_SUFFIX,
    CONTINUED_TITLE_SUFFIX,
)
from markdowndeck.overflow.slide_builder import SlideBuilder


class TestSlideBuilder:
    """Unit tests for the SlideBuilder component with enhanced position reset and continuation features."""

    @pytest.fixture
    def original_slide(self) -> Slide:
        """Create a sample original slide for testing."""
        return Slide(
            object_id="original_slide_123",
            title="Original Slide Title",
            layout=SlideLayout.TITLE_AND_BODY,
            notes="Important speaker notes",
            background={"type": "color", "value": "#ffffff"},
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Original Slide Title",
                    position=(50, 50),
                    size=(620, 40),
                ),
                TextElement(
                    element_type=ElementType.FOOTER,
                    text="Page Footer",
                    position=(50, 370),
                    size=(620, 20),
                ),
            ],
        )

    @pytest.fixture
    def slide_builder(self, original_slide) -> SlideBuilder:
        """Create slide builder with original slide."""
        return SlideBuilder(original_slide)

    def test_continuation_slide_id_generation_uniqueness(self, slide_builder):
        """Test that continuation slides get unique IDs with proper sequencing."""

        new_sections = [Section(id="test_section", elements=[])]

        slide1 = slide_builder.create_continuation_slide(new_sections, 1)
        slide2 = slide_builder.create_continuation_slide(new_sections, 2)
        slide3 = slide_builder.create_continuation_slide(new_sections, 10)

        # Verify uniqueness
        assert slide1.object_id != slide2.object_id, "Continuation slides should have unique IDs"
        assert slide2.object_id != slide3.object_id, "All continuation slides should have unique IDs"

        # Verify sequencing in IDs
        assert "original_slide_123_cont_1" in slide1.object_id, "Should include original ID and sequence number"
        assert "original_slide_123_cont_2" in slide2.object_id, "Should include correct sequence number"
        assert "original_slide_123_cont_10" in slide3.object_id, "Should handle multi-digit sequence numbers"

        # Verify unique suffixes
        id_parts_1 = slide1.object_id.split("_")
        id_parts_2 = slide2.object_id.split("_")
        assert id_parts_1[-1] != id_parts_2[-1], "Should have unique suffix components"

    def test_continuation_title_creation_with_numbering(self, slide_builder):
        """Test creation of continuation titles with proper numbering."""

        new_sections = [Section(id="test_section", elements=[])]

        # Test first continuation
        continuation1 = slide_builder.create_continuation_slide(new_sections, 1)

        title_elements = [e for e in continuation1.elements if e.element_type == ElementType.TITLE]
        assert len(title_elements) == 1, "Should have exactly one title element"

        title1 = title_elements[0]
        assert CONTINUED_TITLE_SUFFIX in title1.text, "Should include continuation suffix"
        assert "Original Slide Title" in title1.text, "Should preserve original title"
        assert title1.text.count(CONTINUED_TITLE_SUFFIX) == 1, "Should have suffix exactly once"

        # Test numbered continuation (second slide)
        continuation2 = slide_builder.create_continuation_slide(new_sections, 2)

        title_elements2 = [e for e in continuation2.elements if e.element_type == ElementType.TITLE]
        title2 = title_elements2[0]
        assert "(2)" in title2.text, "Should include slide number for multiple continuations"
        assert "Original Slide Title" in title2.text, "Should preserve original title"

        # Test higher numbered continuation
        continuation5 = slide_builder.create_continuation_slide(new_sections, 5)
        title_elements5 = [e for e in continuation5.elements if e.element_type == ElementType.TITLE]
        title5 = title_elements5[0]
        assert "(5)" in title5.text, "Should handle higher sequence numbers"

    def test_continuation_title_cleanup_from_existing_markers(self, slide_builder):
        """Test that existing continuation markers are properly cleaned up."""

        # Create slide builder with slide that already has continuation markers
        original_with_marker = Slide(
            object_id="marker_slide",
            title="Previous Title (continued)",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Previous Title (continued)",
                    position=(50, 50),
                    size=(620, 40),
                )
            ],
        )

        builder_with_marker = SlideBuilder(original_with_marker)
        new_sections = [Section(id="test_section", elements=[])]

        continuation = builder_with_marker.create_continuation_slide(new_sections, 1)

        title_elements = [e for e in continuation.elements if e.element_type == ElementType.TITLE]
        title = title_elements[0]

        # Should clean up old marker and add new one
        assert "Previous Title" in title.text, "Should preserve base title"
        assert title.text.count(CONTINUED_TITLE_SUFFIX) == 1, "Should have exactly one continuation marker"

    def test_continuation_footer_creation_and_preservation(self, slide_builder):
        """Test creation of continuation footers with content preservation."""

        new_sections = [Section(id="test_section", elements=[])]

        continuation = slide_builder.create_continuation_slide(new_sections, 1)

        footer_elements = [e for e in continuation.elements if e.element_type == ElementType.FOOTER]
        assert len(footer_elements) == 1, "Should have exactly one footer element"

        footer = footer_elements[0]
        assert CONTINUED_FOOTER_SUFFIX in footer.text, "Should include continuation suffix"
        assert "Page Footer" in footer.text, "Should preserve original footer text"

        # Verify footer doesn't duplicate continuation markers
        continuation2 = slide_builder.create_continuation_slide(new_sections, 2)
        footer_elements2 = [e for e in continuation2.elements if e.element_type == ElementType.FOOTER]
        footer2 = footer_elements2[0]
        assert footer2.text.count(CONTINUED_FOOTER_SUFFIX) == 1, "Should not duplicate footer markers"

    def test_metadata_preservation_comprehensive(self, slide_builder):
        """Test comprehensive preservation of slide metadata."""

        new_sections = [Section(id="test_section", elements=[])]

        continuation = slide_builder.create_continuation_slide(new_sections, 1)

        # Verify layout
        assert continuation.layout == SlideLayout.TITLE_AND_BODY, "Should use standard layout for continuations"

        # Verify notes preservation
        assert continuation.notes == "Important speaker notes", "Should preserve speaker notes"

        # Verify background preservation (deep copy)
        assert continuation.background == {
            "type": "color",
            "value": "#ffffff",
        }, "Should preserve background settings"

        # Verify it's a deep copy, not reference
        assert continuation.background is not slide_builder.original_slide.background, "Should be deep copy"

        # Verify slide structure
        assert hasattr(continuation, "sections"), "Should have sections attribute"
        assert hasattr(continuation, "elements"), "Should have elements attribute"
        assert hasattr(continuation, "object_id"), "Should have unique object_id"

    def test_comprehensive_position_reset_validation(self, slide_builder):
        """Test comprehensive position and size reset for all elements and sections."""

        # Create complex nested sections with positioned elements
        text1 = TextElement(
            element_type=ElementType.TEXT,
            text="Section 1 text",
            position=(50, 150),
            size=(620, 40),
        )

        code_element = CodeElement(
            element_type=ElementType.CODE,
            code="print('hello')\nprint('world')",
            language="python",
            position=(50, 200),
            size=(620, 60),
        )

        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="Item 1"),
                ListItem(text="Item 2"),
            ],
            position=(50, 270),
            size=(620, 50),
        )

        nested_section = Section(
            id="nested_section",
            type="section",
            position=(50, 200),
            size=(620, 120),
            elements=[code_element, list_element],
        )

        parent_section = Section(
            id="parent_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[text1],
            subsections=[nested_section],
        )

        # Create row section with columns
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column",
            position=(50, 150),
            size=(300, 40),
        )

        right_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["A1", "A2"], ["B1", "B2"]],
            position=(360, 150),
            size=(310, 60),
        )

        left_column = Section(
            id="left_column",
            type="section",
            position=(50, 150),
            size=(300, 100),
            elements=[left_text],
        )

        right_column = Section(
            id="right_column",
            type="section",
            position=(360, 150),
            size=(310, 100),
            elements=[right_table],
        )

        row_section = Section(
            id="row_section",
            type="row",
            position=(50, 150),
            size=(620, 100),
            subsections=[left_column, right_column],
        )

        all_sections = [parent_section, row_section]

        continuation = slide_builder.create_continuation_slide(all_sections, 1)

        # Verify all positions and sizes are reset
        def check_reset_recursive(sections, path=""):
            for i, section in enumerate(sections):
                section_path = f"{path}section[{i}]({section.id})"
                assert section.position is None, f"{section_path} position should be reset"
                assert section.size is None, f"{section_path} size should be reset"

                # Check elements within section
                for j, element in enumerate(section.elements):
                    element_path = f"{section_path}.element[{j}]({element.element_type})"
                    assert element.position is None, f"{element_path} position should be reset"
                    assert element.size is None, f"{element_path} size should be reset"

                # Recursively check subsections
                if section.subsections:
                    check_reset_recursive(section.subsections, f"{section_path}.")

        check_reset_recursive(continuation.sections)

    def test_element_extraction_from_complex_sections(self, slide_builder):
        """Test extraction of elements from complex nested section structures."""

        # Create diverse element types
        text_elem = TextElement(
            element_type=ElementType.TEXT,
            text="Regular text",
            position=(50, 150),
            size=(620, 30),
        )

        code_elem = CodeElement(
            element_type=ElementType.CODE,
            code="def hello():\n    print('world')",
            language="python",
            position=(50, 180),
            size=(620, 40),
        )

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="List item 1"), ListItem(text="List item 2")],
            position=(50, 220),
            size=(620, 40),
        )

        table_elem = TableElement(
            element_type=ElementType.TABLE,
            headers=["Name", "Value"],
            rows=[["Item 1", "100"], ["Item 2", "200"]],
            position=(50, 260),
            size=(620, 60),
        )

        image_elem = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/image.jpg",
            alt_text="Test image",
            position=(50, 320),
            size=(620, 100),
        )

        # Create nested section structure
        level3_section = Section(
            id="level3",
            elements=[image_elem],
            position=(50, 320),
            size=(620, 100),
        )

        level2_section = Section(
            id="level2",
            elements=[table_elem],
            subsections=[level3_section],
            position=(50, 260),
            size=(620, 160),
        )

        level1_section = Section(
            id="level1",
            elements=[text_elem, code_elem, list_elem],
            subsections=[level2_section],
            position=(50, 150),
            size=(620, 250),
        )

        continuation = slide_builder.create_continuation_slide([level1_section], 1)

        # Count extracted elements (excluding title and footer)
        content_elements = [e for e in continuation.elements if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)]

        # Should have extracted all 5 content elements
        assert len(content_elements) == 5, f"Should extract all 5 elements, got {len(content_elements)}"

        # Verify all element types are present
        element_types = {e.element_type for e in content_elements}
        expected_types = {
            ElementType.TEXT,
            ElementType.CODE,
            ElementType.BULLET_LIST,
            ElementType.TABLE,
            ElementType.IMAGE,
        }
        assert element_types == expected_types, "Should extract all element types"

        # Verify all elements have reset positions
        for element in content_elements:
            assert element.position is None, f"{element.element_type} position should be reset"
            assert element.size is None, f"{element.element_type} size should be reset"

    def test_unique_element_id_generation_prevention_conflicts(self, slide_builder):
        """Test that elements get unique IDs to prevent conflicts in continuation slides."""

        # Create elements with existing IDs that might conflict
        text_element1 = TextElement(
            element_type=ElementType.TEXT,
            text="Text 1",
            object_id="text_123",
            position=(50, 150),
            size=(620, 30),
        )

        text_element2 = TextElement(
            element_type=ElementType.TEXT,
            text="Text 2",
            object_id="text_123",  # Same ID - should be made unique
            position=(50, 180),
            size=(620, 30),
        )

        section1 = Section(id="section1", elements=[text_element1])
        section2 = Section(id="section2", elements=[text_element2])

        continuation = slide_builder.create_continuation_slide([section1, section2], 1)

        # Find extracted text elements
        text_elements = [
            e for e in continuation.elements if e.element_type == ElementType.TEXT and e.text in ["Text 1", "Text 2"]
        ]

        assert len(text_elements) == 2, "Should have both text elements"

        # Verify unique IDs
        ids = [e.object_id for e in text_elements]
        assert len(set(ids)) == len(ids), "All element IDs should be unique"
        assert all(element_id is not None for element_id in ids), "All elements should have IDs"

        # Verify IDs are different from originals
        original_ids = {"text_123"}
        extracted_ids = set(ids)
        assert original_ids.isdisjoint(extracted_ids), "New IDs should be different from originals"

    def test_original_slide_without_title_graceful_handling(self):
        """Test slide builder with original slide that has no title element."""

        original_without_title = Slide(
            object_id="no_title_slide",
            elements=[TextElement(element_type=ElementType.TEXT, text="Just content")],
        )

        builder = SlideBuilder(original_without_title)
        new_sections = [Section(id="test_section", elements=[])]

        continuation = builder.create_continuation_slide(new_sections, 1)

        # Should create generic continuation title
        title_elements = [e for e in continuation.elements if e.element_type == ElementType.TITLE]
        assert len(title_elements) == 1, "Should create title even if original had none"

        title = title_elements[0]
        assert "Content" in title.text, "Should use generic title base"
        assert CONTINUED_TITLE_SUFFIX in title.text, "Should include continuation suffix"

        # Verify title has proper reset state
        assert title.position is None, "Created title position should be None"
        assert title.size is None, "Created title size should be None"

    def test_original_slide_without_footer_graceful_handling(self):
        """Test slide builder with original slide that has no footer element."""

        original_without_footer = Slide(
            object_id="no_footer_slide",
            elements=[TextElement(element_type=ElementType.TITLE, text="Title Only")],
        )

        builder = SlideBuilder(original_without_footer)
        new_sections = [Section(id="test_section", elements=[])]

        continuation = builder.create_continuation_slide(new_sections, 1)

        # Should not create footer if original had none
        footer_elements = [e for e in continuation.elements if e.element_type == ElementType.FOOTER]
        assert len(footer_elements) == 0, "Should not create footer if original had none"

        # But should still create title
        title_elements = [e for e in continuation.elements if e.element_type == ElementType.TITLE]
        assert len(title_elements) == 1, "Should create continuation title"

    def test_continuation_metadata_generation(self, slide_builder):
        """Test metadata generation for continuation slides."""

        metadata1 = slide_builder.get_continuation_metadata(1)
        metadata3 = slide_builder.get_continuation_metadata(3)

        # Verify metadata structure
        expected_keys = {
            "original_slide_id",
            "original_title",
            "continuation_number",
            "has_original_footer",
            "original_layout",
            "original_element_count",
            "original_section_count",
        }
        assert set(metadata1.keys()) == expected_keys, "Should have all expected metadata keys"

        # Verify metadata content
        assert metadata1["original_slide_id"] == "original_slide_123"
        assert metadata1["original_title"] == "Original Slide Title"
        assert metadata1["continuation_number"] == 1
        assert metadata1["has_original_footer"]
        assert metadata1["original_element_count"] == 2

        # Verify different continuation numbers
        assert metadata3["continuation_number"] == 3

    def test_continuation_slide_validation_comprehensive(self, slide_builder):
        """Test comprehensive validation of continuation slides."""

        # Create continuation with positioned elements (should be invalid)
        positioned_text = TextElement(
            element_type=ElementType.TEXT,
            text="Positioned text",
            position=(50, 150),  # Should be None
            size=(620, 30),  # Should be None
        )

        positioned_section = Section(
            id="positioned_section",
            position=(50, 150),  # Should be None
            size=(620, 100),  # Should be None
            elements=[positioned_text],
        )

        continuation = slide_builder.create_continuation_slide([positioned_section], 1)

        # Validate the continuation slide
        warnings = slide_builder.validate_continuation_slide(continuation)

        # Should have warnings about positions not being reset
        position_warnings = [w for w in warnings if "position" in w.lower()]
        size_warnings = [w for w in warnings if "size" in w.lower()]

        # Note: The create_continuation_slide method should reset positions,
        # so these warnings should not occur if implementation is correct
        assert len(position_warnings) == 0, "Positions should be properly reset"
        assert len(size_warnings) == 0, "Sizes should be properly reset"

        # Should have continuation title marker
        continuation_warnings = [w for w in warnings if "continuation" in w.lower()]
        assert len(continuation_warnings) == 0, "Should have proper continuation title"

    def test_slide_builder_error_handling(self, slide_builder):
        """Test error handling in slide builder operations."""

        # Test with None sections - should raise TypeError or AttributeError
        with pytest.raises((TypeError, AttributeError)):
            slide_builder.create_continuation_slide(None, 1)

        # Test with empty sections
        continuation_empty = slide_builder.create_continuation_slide([], 1)
        assert continuation_empty is not None, "Should handle empty sections list"

        # Test with malformed sections
        malformed_section = Section(id=None)  # Missing required ID
        try:
            continuation_malformed = slide_builder.create_continuation_slide([malformed_section], 1)
            assert continuation_malformed is not None, "Should handle malformed sections"
        except Exception:
            # If it fails, that's acceptable for malformed input
            pass

    def test_slide_builder_with_complex_original_backgrounds(self):
        """Test slide builder with complex background configurations."""

        # Test with gradient background
        gradient_slide = Slide(
            object_id="gradient_slide",
            title="Gradient Test",
            background={
                "type": "gradient",
                "colors": ["#ff0000", "#00ff00", "#0000ff"],
                "direction": "diagonal",
                "settings": {"opacity": 0.8},
            },
            elements=[TextElement(element_type=ElementType.TITLE, text="Gradient Test")],
        )

        gradient_builder = SlideBuilder(gradient_slide)
        continuation = gradient_builder.create_continuation_slide([Section(id="test")], 1)

        # Should preserve complex background
        assert continuation.background["type"] == "gradient", "Should preserve background type"
        assert len(continuation.background["colors"]) == 3, "Should preserve background colors"
        assert continuation.background["settings"]["opacity"] == 0.8, "Should preserve nested settings"

        # Should be deep copy
        assert continuation.background is not gradient_slide.background, "Should be deep copy"

    def test_position_reset_section_validation_recursive(self, slide_builder):
        """Test recursive position reset validation for deeply nested sections."""

        # Create 5 levels of nesting
        level5_section = Section(
            id="level5",
            position=(50, 400),
            size=(620, 50),
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Level 5",
                    position=(50, 400),
                    size=(620, 30),
                )
            ],
        )

        level4_section = Section(
            id="level4",
            position=(50, 350),
            size=(620, 100),
            subsections=[level5_section],
        )

        level3_section = Section(
            id="level3",
            position=(50, 300),
            size=(620, 150),
            subsections=[level4_section],
        )

        level2_section = Section(
            id="level2",
            position=(50, 250),
            size=(620, 200),
            subsections=[level3_section],
        )

        level1_section = Section(
            id="level1",
            position=(50, 200),
            size=(620, 250),
            subsections=[level2_section],
        )

        continuation = slide_builder.create_continuation_slide([level1_section], 1)

        # Validate recursive position reset
        warnings = slide_builder.validate_continuation_slide(continuation)

        # Should have no warnings about positions - all should be reset
        position_warnings = [w for w in warnings if "position" in w]
        size_warnings = [w for w in warnings if "size" in w]

        assert len(position_warnings) == 0, f"All positions should be reset, got warnings: {position_warnings}"
        assert len(size_warnings) == 0, f"All sizes should be reset, got warnings: {size_warnings}"

    def test_slide_builder_performance_with_large_structures(self, slide_builder):
        """Test slide builder performance with large section structures."""

        import time

        # Create a large number of sections and elements
        large_sections = []
        for i in range(100):  # Create 100 sections
            elements = []
            for j in range(10):  # 10 elements per section
                elements.append(
                    TextElement(
                        element_type=ElementType.TEXT,
                        text=f"Section {i} Element {j}",
                        position=(50, 150 + j * 30),
                        size=(620, 25),
                    )
                )

            section = Section(
                id=f"section_{i}",
                position=(50, 150),
                size=(620, 300),
                elements=elements,
            )
            large_sections.append(section)

        # Measure performance
        start_time = time.time()
        continuation = slide_builder.create_continuation_slide(large_sections, 1)
        end_time = time.time()

        processing_time = end_time - start_time

        # Should complete in reasonable time
        assert processing_time < 5.0, f"Should handle large structures efficiently, took {processing_time:.2f}s"

        # Verify all elements were processed
        content_elements = [e for e in continuation.elements if e.element_type not in (ElementType.TITLE, ElementType.FOOTER)]
        expected_count = 100 * 10  # 100 sections * 10 elements each
        assert len(content_elements) == expected_count, f"Should process all {expected_count} elements"

        # Verify all positions are reset
        for element in content_elements:
            assert element.position is None, "All element positions should be reset"
            assert element.size is None, "All element sizes should be reset"
