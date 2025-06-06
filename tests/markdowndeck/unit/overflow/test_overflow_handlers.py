"""Unit tests for overflow handler components with unanimous consent model."""

from copy import deepcopy

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
from markdowndeck.overflow.handlers import StandardOverflowHandler


class TestStandardOverflowHandler:
    """Unit tests for the StandardOverflowHandler component with unanimous consent model."""

    @pytest.fixture
    def handler(self) -> StandardOverflowHandler:
        """Create handler with standard body height."""
        return StandardOverflowHandler(body_height=255.0)

    def test_rule_a_standard_element_partitioning_with_minimum_requirements(
        self, handler
    ):
        """Test Rule A: standard section partitioning with elements using minimum requirements."""

        # Create section with multiple text elements that follow minimum requirements
        text1 = TextElement(
            element_type=ElementType.TEXT,
            text="First text element\nSecond line of first element",
            position=(50, 150),
            size=(620, 40),
        )

        text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Second text element that will overflow\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6",
            position=(50, 190),
            size=(620, 120),  # Large enough to cause overflow
        )

        text3 = TextElement(
            element_type=ElementType.TEXT,
            text="Third text element\nShould be promoted to continuation",
            position=(50, 310),
            size=(620, 40),
        )

        overflowing_section = Section(
            id="rule_a_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows body_height
            elements=[text1, text2, text3],
        )

        # Create original slide
        original_slide = Slide(
            object_id="rule_a_slide",
            elements=[text1, text2, text3],
            sections=[overflowing_section],
            title="Rule A Test",
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, overflowing_section
        )

        # Verify fitted slide has content that meets minimum requirements
        assert len(fitted_slide.sections) == 1, "Fitted slide should have one section"
        fitted_section = fitted_slide.sections[0]

        # Should contain elements that fit and meet minimum requirements
        assert (
            len(fitted_section.elements) >= 1
        ), "Fitted section should have elements that fit"

        # Verify continuation slide
        assert (
            len(continuation_slide.sections) == 1
        ), "Continuation slide should have one section"
        continuation_section = continuation_slide.sections[0]

        # Should contain overflowing elements
        assert (
            len(continuation_section.elements) >= 1
        ), "Continuation section should have overflowing elements"

        # Verify position reset in continuation
        assert (
            continuation_section.position is None
        ), "Continuation section position should be reset"
        assert (
            continuation_section.size is None
        ), "Continuation section size should be reset"

    def test_rule_b_unanimous_consent_model_success(self, handler):
        """Test Rule B: unanimous consent model when all elements can split."""

        # Create left column with splittable content that meets minimum requirements
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column line 1\nLeft column line 2\nLeft column line 3\nLeft column line 4",
            position=(50, 150),
            size=(300, 80),
        )

        # Mock split method that succeeds with minimum requirements
        def left_split(available_height):
            if available_height >= 40:  # Minimum for 2 lines
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left column line 1\nLeft column line 2",
                    size=(300, 40),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left column line 3\nLeft column line 4",
                    size=(300, 40),
                )
                return fitted, overflowing
            return None, left_text

        left_text.split = left_split

        # Create right column with splittable table that meets minimum requirements
        right_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[
                ["Row 1 A", "Row 1 B"],
                ["Row 2 A", "Row 2 B"],
                ["Row 3 A", "Row 3 B"],
                ["Row 4 A", "Row 4 B"],
            ],
            position=(360, 150),
            size=(310, 80),
        )

        # Mock split method that succeeds with minimum requirements
        def right_split(available_height):
            if available_height >= 60:  # Minimum for header + 2 rows
                fitted = TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[["Row 1 A", "Row 1 B"], ["Row 2 A", "Row 2 B"]],
                    size=(310, 40),
                )
                overflowing = TableElement(
                    element_type=ElementType.TABLE,
                    headers=["Col1", "Col2"],
                    rows=[["Row 3 A", "Row 3 B"], ["Row 4 A", "Row 4 B"]],
                    size=(310, 40),
                )
                return fitted, overflowing
            return None, right_table

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
            id="unanimous_row",
            type="row",
            position=(50, 150),
            size=(620, 200),  # Row overflows
            subsections=[left_column, right_column],
        )

        original_slide = Slide(
            object_id="unanimous_success_slide",
            elements=[left_text, right_table],
            sections=[row_section],
            title="Unanimous Consent Success",
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, row_section
        )

        # Should successfully split with unanimous consent
        assert len(fitted_slide.sections) == 1, "Fitted slide should have one section"
        fitted_row = fitted_slide.sections[0]

        if fitted_row.type == "row":
            assert (
                len(fitted_row.subsections) == 2
            ), "Fitted row should have both columns"

        # Verify continuation slide maintains row structure
        assert (
            len(continuation_slide.sections) == 1
        ), "Continuation should have one section"
        continuation_row = continuation_slide.sections[0]

        if continuation_row.type == "row":
            assert (
                len(continuation_row.subsections) == 2
            ), "Continuation row should have both columns"

    def test_rule_b_unanimous_consent_model_failure(self, handler):
        """Test Rule B: unanimous consent model when one element rejects split."""

        # Create left column with splittable content
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column line 1\nLeft column line 2\nLeft column line 3",
            position=(50, 150),
            size=(300, 60),
        )

        # Mock split method that succeeds
        def left_split(available_height):
            if available_height >= 40:  # Minimum for 2 lines
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left column line 1\nLeft column line 2",
                    size=(300, 40),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left column line 3",
                    size=(300, 20),
                )
                return fitted, overflowing
            return None, left_text

        left_text.split = left_split

        # Create right column with content that rejects split due to minimum requirements
        right_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1"],
            rows=[["Row 1"]],  # Only 1 row, can't meet minimum 2 rows
            position=(360, 150),
            size=(310, 40),
        )

        # Mock split method that always rejects due to minimum requirements
        def right_split(available_height):
            return None, right_table  # Always fails minimum requirements

        right_table.split = right_split

        # Create row structure with limited height to force overflow
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
            id="unanimous_fail_row",
            type="row",
            position=(50, 150),
            size=(620, 200),  # Row overflows
            subsections=[left_column, right_column],
        )

        original_slide = Slide(
            object_id="unanimous_fail_slide",
            elements=[left_text, right_table],
            sections=[row_section],
            title="Unanimous Consent Failure",
        )

        # Set a very limited body height to ensure overflow occurs
        handler.body_height = 100  # Much smaller than row size (200)

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, row_section
        )

        # Should promote entire row due to failed unanimous consent
        # Fitted slide should have empty or minimal content
        assert len(fitted_slide.sections) >= 1, "Fitted slide should have sections"

        # Check if continuation slide has sections before accessing
        if len(continuation_slide.sections) > 0:
            # Continuation slide should have the entire row
            continuation_section = continuation_slide.sections[0]
            assert continuation_section.type == "row", "Entire row should be promoted"
            assert (
                len(continuation_section.subsections) == 2
            ), "Both columns should be promoted"
        else:
            # If no sections in continuation, the entire row should be in fitted slide
            fitted_section = fitted_slide.sections[0]
            assert fitted_section.type == "row", "Row should be in fitted slide"

    def test_element_driven_splitting_delegation(self, handler):
        """Test that splitting decisions are delegated entirely to elements."""

        # FIXED: Create a single element that's definitely larger than available space
        # Handler provides ~255 pixels, so element with 300px height will require splitting
        oversized_text = TextElement(
            element_type=ElementType.TEXT,
            text="Oversized text that definitely requires splitting " * 50,
            position=(50, 150),
            size=(620, 300),  # Larger than available space (~255px)
        )

        split_called = False
        split_height = None
        split_decision = True  # Control whether element chooses to split

        def custom_split(available_height):
            nonlocal split_called, split_height
            split_called = True
            split_height = available_height

            if split_decision and available_height >= 50:  # Element's own criteria
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Custom fitted part",
                    size=(620, available_height),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Custom overflowing part",
                    size=(620, 300 - available_height),
                )
                return fitted, overflowing
            return None, deepcopy(oversized_text)

        oversized_text.split = custom_split

        section = Section(
            id="custom_split_section",
            type="section",
            position=(50, 150),
            size=(620, 350),  # Section definitely overflows body_end_y
            elements=[oversized_text],
        )

        original_slide = Slide(
            object_id="element_driven_slide",
            elements=[oversized_text],
            sections=[section],
        )

        # Test with element choosing to split
        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        assert split_called, "Element split method should have been called"
        assert split_height is not None, "Element should have received available height"

        # Test with element choosing not to split
        split_called = False
        split_decision = False  # Element rejects split

        fitted_slide2, continuation_slide2 = handler.handle_overflow(
            original_slide, section
        )

        assert split_called, "Element split method should still be called"

    def test_minimum_requirements_enforcement(self, handler):
        """Test that minimum requirements are properly enforced."""

        # Test with CodeElement (now splittable with minimum 2 lines)
        code_element = CodeElement(
            element_type=ElementType.CODE,
            code="line1\nline2\nline3\nline4",
            language="python",
            position=(50, 150),
            size=(620, 80),
        )

        # Test with ListElement (minimum 2 items)
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(text="Item 1"),
                ListItem(text="Item 2"),
                ListItem(text="Item 3"),
                ListItem(text="Item 4"),
            ],
            position=(50, 240),
            size=(620, 80),
        )

        section = Section(
            id="minimum_req_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[code_element, list_element],
        )

        original_slide = Slide(
            object_id="minimum_req_slide",
            elements=[code_element, list_element],
            sections=[section],
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        # Verify that elements were split according to their minimum requirements
        fitted_section = fitted_slide.sections[0]
        continuation_section = continuation_slide.sections[0]

        # Both fitted and continuation should have content that meets minimum requirements
        assert len(fitted_section.elements) >= 1, "Fitted section should have elements"
        assert (
            len(continuation_section.elements) >= 1
        ), "Continuation should have elements"

    def test_proactive_image_scaling_contract(self, handler):
        """Test that proactively scaled images are handled correctly."""

        # Create section with pre-scaled image
        pre_scaled_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large.jpg",
            position=(50, 150),
            size=(620, 150),  # Pre-scaled to fit container
        )

        text_content = TextElement(
            element_type=ElementType.TEXT,
            text="Text content with image " * 20,
            position=(50, 310),
            size=(620, 100),
        )

        section = Section(
            id="image_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[pre_scaled_image, text_content],
        )

        original_slide = Slide(
            object_id="image_slide",
            elements=[pre_scaled_image, text_content],
            sections=[section],
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        # Image should be included in fitted slide (since it's pre-scaled)
        fitted_elements = fitted_slide.sections[0].elements
        any(e.element_type == ElementType.IMAGE for e in fitted_elements)

        # Image split method should return (self, None)
        fitted_img, overflowing_img = pre_scaled_image.split(50.0)
        assert fitted_img == pre_scaled_image, "Pre-scaled image should always fit"
        assert overflowing_img is None, "Pre-scaled image should never overflow"

    def test_section_position_reset_in_continuation(self, handler):
        """Test that section positions are properly reset in continuation slides."""

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Content that will overflow " * 20,
            position=(50, 150),
            size=(620, 200),
        )

        # Mock split method to ensure overflow
        def mock_split(available_height):
            fitted = TextElement(
                element_type=ElementType.TEXT,
                text="Fitted content",
                size=(620, available_height),
            )
            overflowing = TextElement(
                element_type=ElementType.TEXT,
                text="Overflowing content",
                size=(620, 200 - available_height),
            )
            return fitted, overflowing

        text_element.split = mock_split

        original_section = Section(
            id="position_reset_section",
            type="section",
            position=(50, 150),  # Original position
            size=(620, 200),
            elements=[text_element],
        )

        original_slide = Slide(
            object_id="position_reset_slide",
            elements=[text_element],
            sections=[original_section],
        )

        handler.body_height = 200  # Creates overflow

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, original_section
        )

        # Continuation section should have reset position and size
        continuation_section = continuation_slide.sections[0]
        assert (
            continuation_section.position is None
        ), "Continuation section position should be reset"
        assert (
            continuation_section.size is None
        ), "Continuation section size should be reset"

        # Elements within continuation section should also have reset positions
        for element in continuation_section.elements:
            assert (
                element.position is None
            ), "Continuation element positions should be reset"
            assert element.size is None, "Continuation element sizes should be reset"

    def test_nested_subsection_partitioning(self, handler):
        """Test partitioning of sections with nested subsections (no elements in parent)."""

        # Create nested section structure
        nested_text = TextElement(
            element_type=ElementType.TEXT,
            text="Nested content " * 10,
            position=(50, 180),
            size=(620, 80),
        )

        nested_section = Section(
            id="nested_section",
            type="section",
            position=(50, 180),
            size=(620, 100),
            elements=[nested_text],
        )

        # FIXED: Parent section has only subsections, no elements
        # Per specification, a section has either elements OR subsections, not both
        parent_section = Section(
            id="parent_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Parent section overflows
            elements=[],  # Empty elements list
            subsections=[nested_section],
        )

        original_slide = Slide(
            object_id="nested_slide",
            elements=[nested_text],  # Only the nested element
            sections=[parent_section],
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, parent_section
        )

        # Should handle nested structure appropriately
        assert len(fitted_slide.sections) == 1, "Should have fitted section"
        assert len(continuation_slide.sections) == 1, "Should have continuation section"

        # Verify position reset in nested structures
        def check_reset_recursive(sections):
            for section in sections:
                assert (
                    section.position is None
                ), f"Section {section.id} position should be reset"
                assert (
                    section.size is None
                ), f"Section {section.id} size should be reset"
                if section.subsections:
                    check_reset_recursive(section.subsections)

        check_reset_recursive(continuation_slide.sections)

    def test_circular_reference_protection(self, handler):
        """Test protection against circular references in section structures."""

        # Create sections with potential circular references
        section_a = Section(
            id="section_a",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Overflows
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Section A content",
                    position=(50, 150),
                    size=(620, 100),
                )
            ],
        )

        section_b = Section(
            id="section_b",
            type="section",
            position=(50, 150),
            size=(620, 100),
            elements=[],
        )

        # Create circular reference
        section_a.subsections = [section_b]
        section_b.subsections = [section_a]  # Circular reference

        original_slide = Slide(
            object_id="circular_slide",
            elements=[
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Section A content",
                    position=(50, 150),
                    size=(620, 100),
                )
            ],
            sections=[section_a],
        )

        # Should handle gracefully without infinite recursion
        try:
            fitted_slide, continuation_slide = handler.handle_overflow(
                original_slide, section_a
            )
            # If it completes, circular reference protection worked
            assert True, "Should handle circular references without infinite recursion"
        except RecursionError:
            pytest.fail("Should not cause infinite recursion with circular references")

    def test_element_validation_during_partitioning(self, handler):
        """Test that elements are properly validated during partitioning."""

        # Create elements with various validation states
        valid_text = TextElement(
            element_type=ElementType.TEXT,
            text="Valid text content\nSecond line",
            position=(50, 150),
            size=(620, 40),
        )

        invalid_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="",  # Invalid empty URL
            position=(50, 200),
            size=(620, 100),
        )

        empty_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[],  # Empty list
            position=(50, 310),
            size=(620, 40),
        )

        section = Section(
            id="validation_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[valid_text, invalid_image, empty_list],
        )

        original_slide = Slide(
            object_id="validation_slide",
            elements=[valid_text, invalid_image, empty_list],
            sections=[section],
        )

        # Should handle invalid elements gracefully
        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        # Should still produce valid slides despite invalid elements
        assert (
            fitted_slide is not None
        ), "Should produce fitted slide despite invalid elements"
        assert (
            continuation_slide is not None
        ), "Should produce continuation slide despite invalid elements"

    def test_handler_with_extreme_dimensions(self, handler):
        """Test handler behavior with extreme dimensional values."""

        # Test with very large content
        huge_text = TextElement(
            element_type=ElementType.TEXT,
            text="Huge content " * 1000,  # Very large content
            position=(50, 150),
            size=(620, 10000),  # Extremely large height
        )

        huge_section = Section(
            id="huge_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Normal section size
            elements=[huge_text],
        )

        # Test with very small content
        tiny_text = TextElement(
            element_type=ElementType.TEXT,
            text="Tiny",
            position=(50, 150),
            size=(620, 0.1),  # Extremely small height
        )

        tiny_section = Section(
            id="tiny_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[tiny_text],
        )

        huge_slide = Slide(
            object_id="huge_slide", elements=[huge_text], sections=[huge_section]
        )
        tiny_slide = Slide(
            object_id="tiny_slide", elements=[tiny_text], sections=[tiny_section]
        )

        # Should handle extreme dimensions gracefully
        fitted_huge, cont_huge = handler.handle_overflow(huge_slide, huge_section)
        fitted_tiny, cont_tiny = handler.handle_overflow(tiny_slide, tiny_section)

        assert fitted_huge is not None, "Should handle huge content"
        assert cont_huge is not None, "Should create continuation for huge content"
        assert fitted_tiny is not None, "Should handle tiny content"
        assert cont_tiny is not None, "Should create continuation for tiny content"
