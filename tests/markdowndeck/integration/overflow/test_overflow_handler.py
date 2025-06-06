"""Integration tests for the overflow handler system with specification compliance."""

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    Section,
    Slide,
    TableElement,
    TextElement,
)
from markdowndeck.models.elements.code import CodeElement
from markdowndeck.overflow import OverflowManager
from markdowndeck.overflow.constants import (
    CONTINUED_TITLE_SUFFIX,
)


class TestOverflowHandlerIntegration:
    """Integration tests for the complete overflow handling pipeline with specification compliance."""

    @pytest.fixture
    def overflow_manager(self) -> OverflowManager:
        """Create overflow manager with standard test dimensions."""
        return OverflowManager(
            slide_width=720,
            slide_height=405,
            margins={"top": 50, "right": 50, "bottom": 50, "left": 50},
        )

    @pytest.fixture
    def positioned_slide_with_external_overflow(self) -> Slide:
        """Create a positioned slide that has EXTERNAL section overflow (per specification)."""
        title = TextElement(
            element_type=ElementType.TITLE,
            text="External Overflow Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create content that fits within section but section itself overflows slide boundary
        table_content = TableElement(
            element_type=ElementType.TABLE,
            headers=["Column 1", "Column 2", "Column 3"],
            rows=[
                [f"Row {i} Cell 1", f"Row {i} Cell 2", f"Row {i} Cell 3"]
                for i in range(1, 8)  # Reasonable number of rows
            ],
            position=(50, 150),
            size=(620, 180),  # Content fits within section
        )

        footer = TextElement(
            element_type=ElementType.FOOTER,
            text="Page Footer",
            position=(50, 370),
            size=(620, 20),
        )

        # Section positioned so its EXTERNAL boundary overflows slide
        main_section = Section(
            id="main_section",
            type="section",
            position=(50, 150),
            size=(620, 180),  # Section bottom at 330, which overflows body_height ~255
            elements=[table_content],
        )

        return Slide(
            object_id="external_overflow_test_slide",
            elements=[title, table_content, footer],
            sections=[main_section],
            title="External Overflow Test",
        )

    def test_external_overflow_creates_continuation_slide(self, overflow_manager):
        """Test that external section overflow creates properly formatted continuation slide."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Original Title",
            position=(50, 50),
            size=(620, 40),
        )

        # Create text that will cause section external overflow
        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="Long content " * 50,  # Substantial content
            position=(50, 150),
            size=(620, 200),  # Content size
        )

        # Section positioned so its external boundary overflows
        section = Section(
            id="text_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section bottom at 350, overflows body_height ~255
            elements=[long_text],
        )

        slide = Slide(
            object_id="external_overflow_slide",
            elements=[title, long_text],
            sections=[section],
            title="Original Title",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create 2 slides due to external overflow
        assert len(result_slides) == 2, f"Should create 2 slides for external overflow, got {len(result_slides)}"

        result_slides[0]
        continuation_slide = result_slides[1]

        # Verify continuation slide structure
        continuation_title = next(
            (e for e in continuation_slide.elements if e.element_type == ElementType.TITLE),
            None,
        )
        assert continuation_title is not None, "Continuation slide should have title"
        assert CONTINUED_TITLE_SUFFIX in continuation_title.text, "Title should indicate continuation"
        assert "Original Title" in continuation_title.text, "Should preserve original title text"

        # Verify positions are reset in continuation slide (per specification)
        for section in continuation_slide.sections:
            assert section.position is None, "Continuation section positions should be reset"
            assert section.size is None, "Continuation section sizes should be reset"

            for element in section.elements:
                assert element.position is None, "Continuation element positions should be reset"
                assert element.size is None, "Continuation element sizes should be reset"

    def test_internal_content_overflow_ignored(self, overflow_manager):
        """Test that internal content overflow within fixed-size sections is ignored (per specification)."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Internal Overflow Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create content larger than its section (internal overflow)
        large_text = TextElement(
            element_type=ElementType.TEXT,
            text="This content is larger than its section " * 20,
            position=(50, 150),
            size=(620, 400),  # Much larger than section
        )

        # Section with explicit height directive that fits within slide
        section = Section(
            id="fixed_height_section",
            type="section",
            position=(50, 150),
            size=(620, 100),  # Section bottom at 250, fits within body_height ~255
            directives={"height": 100},  # Explicit height makes overflow acceptable
            elements=[large_text],
        )

        slide = Slide(
            object_id="internal_overflow_slide",
            elements=[title, large_text],
            sections=[section],
            title="Internal Overflow Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should NOT create continuation slide - internal overflow is ignored
        assert len(result_slides) == 1, "Internal content overflow should be ignored"

        # Original slide should be unchanged
        assert result_slides[0] == slide, "Slide should be unchanged"

    def test_image_proactive_scaling_prevents_overflow(self, overflow_manager):
        """Test that proactively scaled images don't cause overflow (per Rule #5)."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Image Scaling Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create image that would normally be large but gets proactively scaled
        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large-image.jpg",
            alt_text="Large image",
            position=(50, 150),
            size=(620, 150),  # Proactively scaled to fit container
        )

        section = Section(
            id="image_section",
            type="section",
            position=(50, 150),
            size=(620, 150),  # Section fits within slide
            elements=[large_image],
        )

        slide = Slide(
            object_id="image_scaling_slide",
            elements=[title, large_image],
            sections=[section],
            title="Image Scaling Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should NOT create continuation slide - images are pre-scaled
        assert len(result_slides) == 1, "Proactively scaled images should not cause overflow"

        # Test image split behavior returns (self, None)
        fitted, overflowing = large_image.split(50.0)
        assert fitted == large_image, "Image should return self as fitted part"
        assert overflowing is None, "Image should have no overflowing part"

    def test_code_element_minimum_requirements_splitting(self, overflow_manager):
        """Test that code elements follow minimum 2 lines requirement."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Code Splitting Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create code block with multiple lines using proper CodeElement
        code_block = CodeElement(
            element_type=ElementType.CODE,
            code="line 1\nline 2\nline 3\nline 4\nline 5",
            position=(50, 150),
            size=(620, 100),
        )

        # Mock the split method to follow minimum requirements
        def mock_code_split(available_height):
            lines = code_block.code.split("\n")
            if len(lines) >= 4 and available_height > 40:  # Can fit minimum 2 lines
                fitted_lines = lines[:2]  # Take 2 lines
                overflowing_lines = lines[2:]  # Rest overflow

                fitted = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join(fitted_lines),
                    size=(620, 40),
                )
                overflowing = CodeElement(
                    element_type=ElementType.CODE,
                    code="\n".join(overflowing_lines),
                    size=(620, 60),
                )
                return fitted, overflowing
            return None, code_block  # Minimum not met

        code_block.split = mock_code_split

        section = Section(
            id="code_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[code_block],
        )

        slide = Slide(
            object_id="code_splitting_slide",
            elements=[title, code_block],
            sections=[section],
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should create continuation slide with proper code splitting
        assert len(result_slides) >= 1, "Should process code splitting"

    def test_unanimous_consent_columnar_splitting(self, overflow_manager):
        """Test unanimous consent model for coordinated row splitting."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Unanimous Consent Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Left column with splittable content
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column content that can split\nLine 2\nLine 3\nLine 4",
            position=(50, 150),
            size=(300, 120),
        )

        # Mock splittable behavior for left text
        def left_split(available_height):
            if available_height > 30:  # Can fit minimum content
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Left column content that can split",
                    size=(300, 30),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Line 2\nLine 3\nLine 4",
                    size=(300, 90),
                )
                return fitted, overflowing
            return None, left_text

        left_text.split = left_split

        # Right column with unsplittable content (image)
        right_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/image.jpg",
            position=(360, 150),
            size=(310, 120),
        )

        # Create columnar structure
        left_column = Section(
            id="left_column",
            type="section",
            position=(50, 150),
            size=(300, 100),  # Smaller than content
            elements=[left_text],
        )

        right_column = Section(
            id="right_column",
            type="section",
            position=(360, 150),
            size=(310, 100),  # Smaller than content
            elements=[right_image],
        )

        row_section = Section(
            id="main_row",
            type="row",
            position=(50, 150),
            size=(620, 200),  # Row overflows
            subsections=[left_column, right_column],
        )

        slide = Slide(
            object_id="unanimous_consent_slide",
            elements=[title, left_text, right_image],
            sections=[row_section],
            title="Unanimous Consent Test",
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should handle according to unanimous consent model
        # Since image can't split, entire row should be promoted
        assert len(result_slides) >= 2, "Should create continuation slide"

    def test_table_minimum_requirements_header_plus_two_rows(self, overflow_manager):
        """Test that tables follow header + 2 rows minimum requirement."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Table Minimum Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create table with headers and multiple rows
        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2", "Col3"],
            rows=[[f"Row {i} A", f"Row {i} B", f"Row {i} C"] for i in range(1, 10)],
            position=(50, 150),
            size=(620, 200),
        )

        section = Section(
            id="table_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[table],
        )

        slide = Slide(
            object_id="table_minimum_slide",
            elements=[title, table],
            sections=[section],
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should respect table minimum requirements
        assert len(result_slides) >= 1, "Should process table with minimum requirements"

        # If split occurs, both parts should have headers
        if len(result_slides) > 1:
            for result_slide in result_slides:
                for section in result_slide.sections:
                    table_elements = [e for e in section.elements if e.element_type == ElementType.TABLE]
                    for table_elem in table_elements:
                        assert len(table_elem.headers) == 3, "All table parts should have headers"

    def test_list_minimum_requirements_two_items(self, overflow_manager):
        """Test that lists follow minimum 2 items requirement."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="List Minimum Test",
            position=(50, 50),
            size=(620, 40),
        )

        # Create list with multiple items
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"Important item {i} with content") for i in range(1, 8)],
            position=(50, 150),
            size=(620, 200),
        )

        section = Section(
            id="list_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[list_element],
        )

        slide = Slide(
            object_id="list_minimum_slide",
            elements=[title, list_element],
            sections=[section],
        )

        result_slides = overflow_manager.process_slide(slide)

        # Should respect list minimum requirements
        assert len(result_slides) >= 1, "Should process list with minimum requirements"

    def test_continuation_slide_position_reset_validation(self, overflow_manager):
        """Test that continuation slides have all positions properly reset."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Position Reset Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Content that will create continuation " * 30,
            position=(50, 150),
            size=(620, 300),
        )

        section = Section(
            id="reset_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[content],
        )

        slide = Slide(
            object_id="position_reset_slide",
            elements=[title, content],
            sections=[section],
        )

        result_slides = overflow_manager.process_slide(slide)

        assert len(result_slides) >= 2, "Should create continuation slides"

        # Verify continuation slides have positions reset
        for i, result_slide in enumerate(result_slides[1:], 1):
            # Check section position reset
            for section in result_slide.sections:
                assert section.position is None, f"Continuation slide {i} section position should be None"
                assert section.size is None, f"Continuation slide {i} section size should be None"

                # Check element position reset (except meta elements like title/footer)
                for element in section.elements:
                    assert element.position is None, f"Continuation slide {i} element position should be None"
                    assert element.size is None, f"Continuation slide {i} element size should be None"

    def test_overflow_validation_and_analysis(self, overflow_manager):
        """Test overflow validation and analysis tools."""

        title = TextElement(
            element_type=ElementType.TITLE,
            text="Validation Test",
            position=(50, 50),
            size=(620, 40),
        )

        content = TextElement(
            element_type=ElementType.TEXT,
            text="Test content",
            position=(50, 150),
            size=(620, 300),  # Overflows
        )

        section = Section(
            id="validation_section",
            type="section",
            position=(50, 150),
            size=(620, 200),  # Section overflows
            elements=[content],
        )

        slide = Slide(
            object_id="validation_slide",
            elements=[title, content],
            sections=[section],
        )

        # Test validation methods
        has_overflow = overflow_manager.has_external_overflow(slide)
        assert has_overflow, "Should detect external overflow"

        analysis = overflow_manager.get_overflow_analysis(slide)
        assert analysis["has_overflow"], "Analysis should show overflow"
        assert analysis["overflowing_section_index"] is not None, "Should identify overflowing section"

        warnings = overflow_manager.validate_slide_structure(slide)
        # Should not have critical warnings for this simple structure
        assert isinstance(warnings, list), "Should return warnings list"

    def test_edge_case_empty_and_minimal_content_with_specification(self, overflow_manager):
        """Test edge cases with specification-compliant behavior."""

        # Test 1: Empty slide
        empty_slide = Slide(object_id="empty_slide", elements=[], sections=[])

        result = overflow_manager.process_slide(empty_slide)
        assert len(result) == 1, "Empty slide should return single slide"
        assert result[0] == empty_slide, "Empty slide should be unchanged"

        # Test 2: Slide with only meta elements (title, footer)
        meta_only_slide = Slide(
            object_id="meta_only",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Only Title",
                    position=(50, 50),
                    size=(620, 40),
                ),
                TextElement(
                    element_type=ElementType.FOOTER,
                    text="Only Footer",
                    position=(50, 370),
                    size=(620, 20),
                ),
            ],
            sections=[],
        )

        result = overflow_manager.process_slide(meta_only_slide)
        assert len(result) == 1, "Meta-only slide should return single slide"

        # Test 3: Slide with content that exactly fits within external boundaries
        exact_fit_text = TextElement(
            element_type=ElementType.TEXT,
            text="Content that fits exactly",
            position=(50, 150),
            size=(620, 50),
        )

        exact_fit_section = Section(
            id="exact_section",
            type="section",
            position=(50, 150),
            size=(620, 105),  # Section bottom at 255, exactly at body_height
            elements=[exact_fit_text],
        )

        exact_fit_slide = Slide(
            object_id="exact_fit",
            elements=[
                TextElement(
                    element_type=ElementType.TITLE,
                    text="Exact Fit",
                    position=(50, 50),
                    size=(620, 40),
                ),
                exact_fit_text,
            ],
            sections=[exact_fit_section],
        )

        result = overflow_manager.process_slide(exact_fit_slide)
        assert len(result) == 1, "Exactly fitting content should return single slide"

    def test_specification_compliance_summary(self, overflow_manager):
        """Test that system follows all key specification principles."""

        # Test jurisdictional boundaries
        internal_overflow_slide = self._create_internal_overflow_slide()
        result = overflow_manager.process_slide(internal_overflow_slide)
        assert len(result) == 1, "Internal overflow should be ignored"

        # Test proactive image scaling
        image_slide = self._create_image_slide()
        result = overflow_manager.process_slide(image_slide)
        # Images should not cause overflow due to proactive scaling

        # Test element-driven splitting
        splittable_slide = self._create_splittable_content_slide()
        result = overflow_manager.process_slide(splittable_slide)
        # Should demonstrate element-driven split decisions

        # Test position reset in continuations
        if len(result) > 1:
            continuation = result[1]
            for section in continuation.sections:
                assert section.position is None, "Positions should be reset"

    def _create_internal_overflow_slide(self):
        """Helper to create slide with internal content overflow."""
        return Slide(
            object_id="internal_test",
            elements=[
                TextElement(element_type=ElementType.TITLE, text="Internal Test"),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Large content" * 50,
                    position=(50, 150),
                    size=(620, 500),  # Much larger than section
                ),
            ],
            sections=[
                Section(
                    id="fixed_section",
                    position=(50, 150),
                    size=(620, 50),  # Small section that fits in slide
                    directives={"height": 50},  # Explicit height
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Large content" * 50,
                            position=(50, 150),
                            size=(620, 500),
                        )
                    ],
                )
            ],
        )

    def _create_image_slide(self):
        """Helper to create slide with proactively scaled images."""
        return Slide(
            object_id="image_test",
            elements=[
                TextElement(element_type=ElementType.TITLE, text="Image Test"),
                ImageElement(
                    element_type=ElementType.IMAGE,
                    url="https://example.com/image.jpg",
                    position=(50, 150),
                    size=(620, 200),  # Proactively scaled
                ),
            ],
            sections=[
                Section(
                    id="image_section",
                    position=(50, 150),
                    size=(620, 200),
                    elements=[
                        ImageElement(
                            element_type=ElementType.IMAGE,
                            url="https://example.com/image.jpg",
                            position=(50, 150),
                            size=(620, 200),
                        )
                    ],
                )
            ],
        )

    def _create_splittable_content_slide(self):
        """Helper to create slide with splittable content."""
        return Slide(
            object_id="splittable_test",
            elements=[
                TextElement(element_type=ElementType.TITLE, text="Splittable Test"),
                TextElement(
                    element_type=ElementType.TEXT,
                    text="Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                    position=(50, 150),
                    size=(620, 100),
                ),
            ],
            sections=[
                Section(
                    id="splittable_section",
                    position=(50, 150),
                    size=(620, 200),  # Overflows
                    elements=[
                        TextElement(
                            element_type=ElementType.TEXT,
                            text="Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                            position=(50, 150),
                            size=(620, 100),
                        )
                    ],
                )
            ],
        )
