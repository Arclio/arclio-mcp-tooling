"""Unit tests for individual overflow handler components."""

from copy import deepcopy

import pytest
from markdowndeck.models import (
    ElementType,
    ImageElement,
    Section,
    Slide,
    TextElement,
)
from markdowndeck.overflow.handlers import StandardOverflowHandler


class TestStandardOverflowHandler:
    """Unit tests for the StandardOverflowHandler component."""

    @pytest.fixture
    def handler(self) -> StandardOverflowHandler:
        """Create handler with standard body height."""
        return StandardOverflowHandler(body_height=255.0)

    def test_rule_a_standard_element_partitioning(self, handler):
        """Test Rule A: standard section partitioning with elements."""

        # Create section with multiple text elements
        text1 = TextElement(
            element_type=ElementType.TEXT,
            text="First text element",
            position=(50, 150),
            size=(620, 30),
        )

        text2 = TextElement(
            element_type=ElementType.TEXT,
            text="Second text element that will overflow "
            * 20,  # Much longer text to actually cause overflow
            position=(50, 190),
            size=(620, 100),  # This will cause overflow
        )

        text3 = TextElement(
            element_type=ElementType.TEXT,
            text="Third text element",
            position=(50, 300),
            size=(620, 30),
        )

        overflowing_section = Section(
            id="rule_a_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[text1, text2, text3],
        )

        # Create original slide
        original_slide = Slide(
            object_id="rule_a_slide",
            elements=[text1, text2, text3],
            sections=[overflowing_section],
            title="Rule A Test",
        )

        # Calculate available height (from position 150 to body_height 255)

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, overflowing_section
        )

        # Verify fitted slide
        assert len(fitted_slide.sections) == 1, "Fitted slide should have one section"
        fitted_section = fitted_slide.sections[0]

        # Should contain elements that fit
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

    def test_rule_b_row_column_partitioning(self, handler):
        """Test Rule B: row of columns partitioning."""

        # Create row section with columns
        left_text = TextElement(
            element_type=ElementType.TEXT,
            text="Left column content",
            position=(50, 150),
            size=(300, 50),
        )

        right_text = TextElement(
            element_type=ElementType.TEXT,
            text="Right column content that overflows",
            position=(360, 150),
            size=(310, 150),  # Taller, will cause overflow
        )

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
            size=(310, 100),  # Smaller than content
            elements=[right_text],
        )

        row_section = Section(
            id="row_section",
            type="row",
            position=(50, 150),
            size=(620, 100),
            subsections=[left_column, right_column],
        )

        original_slide = Slide(
            object_id="rule_b_slide",
            elements=[left_text, right_text],
            sections=[row_section],
            title="Rule B Test",
        )

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, row_section
        )

        # Verify that row structure is preserved
        assert len(fitted_slide.sections) == 1, "Fitted slide should have one section"
        fitted_row = fitted_slide.sections[0]

        if fitted_row.type == "row":
            assert len(fitted_row.subsections) >= 1, "Fitted row should have columns"

    def test_threshold_rule_splitting_decision(self, handler):
        """Test that threshold rule correctly determines splitting vs promotion."""

        # Create element that meets threshold for splitting
        threshold_text = TextElement(
            element_type=ElementType.TEXT,
            text="Content for threshold testing " * 10,
            position=(50, 150),
            size=(620, 100),
        )

        # Mock the split method for testing
        def mock_split(available_height):
            if available_height >= 40:  # 40% of 100 = meets threshold
                fitted = TextElement(
                    element_type=ElementType.TEXT,
                    text="Fitted part",
                    position=(50, 150),
                    size=(620, available_height),
                )
                overflowing = TextElement(
                    element_type=ElementType.TEXT,
                    text="Overflowing part",
                    position=(50, 150 + available_height),
                    size=(620, 100 - available_height),
                )
                return fitted, overflowing
            return None, deepcopy(threshold_text)

        threshold_text.split = mock_split

        section = Section(
            id="threshold_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[threshold_text],
        )

        original_slide = Slide(
            object_id="threshold_slide",
            elements=[threshold_text],
            sections=[section],
            title="Threshold Test",
        )

        # Test with exactly threshold amount available
        handler.body_height = 150 + 40  # Available height = 40 (meets threshold)

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        # Should split the element
        assert len(fitted_slide.sections[0].elements) > 0, "Should have fitted part"
        assert (
            len(continuation_slide.sections[0].elements) > 0
        ), "Should have overflowing part"

    def test_unsplittable_element_promotion(self, handler):
        """Test that unsplittable elements are promoted entirely."""

        # Create image element (unsplittable)
        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large.jpg",
            position=(50, 200),
            size=(620, 100),
        )

        text_before = TextElement(
            element_type=ElementType.TEXT,
            text="Text before image",
            position=(50, 150),
            size=(620, 40),
        )

        section = Section(
            id="unsplittable_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[text_before, large_image],
        )

        original_slide = Slide(
            object_id="unsplittable_slide",
            elements=[text_before, large_image],
            sections=[section],
            title="Unsplittable Test",
        )

        # Set body height so image won't fit after text
        handler.body_height = 250  # Available = 100, not enough for text + image

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        # Image should be promoted entirely to continuation slide
        continuation_elements = continuation_slide.sections[0].elements
        image_elements = [
            e for e in continuation_elements if e.element_type == ElementType.IMAGE
        ]

        assert len(image_elements) == 1, "Image should be in continuation slide"

    def test_element_split_method_calls(self, handler):
        """Test that element split methods are called correctly."""

        # Create a text element with a custom split method for testing
        test_text = TextElement(
            element_type=ElementType.TEXT,
            text="Test content for split method "
            * 20,  # Much longer text to force overflow
            position=(50, 150),
            size=(620, 100),
        )

        split_called = False
        split_height = None

        def mock_split(available_height):
            nonlocal split_called, split_height
            split_called = True
            split_height = available_height

            fitted = TextElement(
                element_type=ElementType.TEXT,
                text="Fitted part",
                size=(620, available_height),
            )
            overflowing = TextElement(
                element_type=ElementType.TEXT,
                text="Overflowing part",
                size=(620, 100 - available_height),
            )
            return fitted, overflowing

        test_text.split = mock_split

        section = Section(
            id="split_test_section",
            type="section",
            position=(50, 150),
            size=(620, 200),
            elements=[test_text],
        )

        original_slide = Slide(
            object_id="split_test_slide", elements=[test_text], sections=[section]
        )

        # Set up overflow condition
        handler.body_height = 200  # Available height = 50

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, section
        )

        assert split_called, "Split method should have been called"
        assert (
            split_height is not None
        ), "Split method should have received height parameter"

    def test_section_position_reset_in_continuation(self, handler):
        """Test that section positions are reset in continuation slides."""

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Content that will overflow "
            * 20,  # Much longer text to force overflow
            position=(50, 150),
            size=(620, 200),
        )

        # Mock split method
        def mock_split(available_height):
            fitted = TextElement(
                element_type=ElementType.TEXT,
                text="Fitted",
                size=(620, available_height),
            )
            overflowing = TextElement(
                element_type=ElementType.TEXT,
                text="Overflowing",
                size=(620, 200 - available_height),
            )
            return fitted, overflowing

        text_element.split = mock_split

        original_section = Section(
            id="position_test_section",
            type="section",
            position=(50, 150),  # Original position
            size=(620, 200),
            elements=[text_element],
        )

        original_slide = Slide(
            object_id="position_test_slide",
            elements=[text_element],
            sections=[original_section],
        )

        handler.body_height = 200  # Creates overflow

        fitted_slide, continuation_slide = handler.handle_overflow(
            original_slide, original_section
        )

        # Continuation section should have reset position
        continuation_section = continuation_slide.sections[0]
        assert (
            continuation_section.position is None
        ), "Continuation section position should be reset"
        assert (
            continuation_section.size is None
        ), "Continuation section size should be reset"
