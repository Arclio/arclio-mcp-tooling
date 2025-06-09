# File: tests/markdowndeck/unit/models/elements/test_text_element_wrap.py

from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import ElementType, TextElement


class TestTextElementWrap:
    def test_split_can_wrap_long_line_of_text(self):
        """
        Test Case: OVERFLOW-C-07 (new)
        Validates that TextElement.split() can split a single long line of text
        by wrapping it, not just by splitting on '\\n'. This is critical to
        preventing infinite overflow loops.
        Spec: DATA_MODELS.md, .split() Contract
        """
        # Arrange
        # A long line of text with no explicit newlines.
        long_text = "This is a single, very long line of text designed to test the wrapping capability of the split method. It should be broken into multiple lines by the split method itself, rather than being treated as an atomic, unsplittable unit."

        # Simulate the state of the element after layout calculation
        # The layout manager would have calculated an (incorrectly large) size.
        # We provide a realistic width for the split method to use.
        available_width = 400.0
        # The full height would be large, but we pass a small available_height to split()
        # to force a split.
        initial_height = calculate_text_element_height(
            TextElement(element_type=ElementType.TEXT, text=long_text), available_width
        )

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
            size=(available_width, initial_height),
        )

        # Act
        # Provide a height that can fit 2-3 lines but not all 4 lines.
        # Based on the debug output, each line is ~22pt, so 50pt should fit 2 lines
        available_height_for_split = 50.0
        fitted_part, overflowing_part = text_element.split(available_height_for_split)

        # Assert
        # The current implementation will fail this test because it will return (None, self).
        assert (
            fitted_part is not None
        ), "The element should have split and returned a fitted part."
        assert (
            overflowing_part is not None
        ), "An overflowing part should have been returned."

        # Verify that the split actually happened and content was moved.
        assert (
            fitted_part.text != text_element.text
        ), "Fitted part's text should be shorter than the original."
        assert (
            overflowing_part.text != text_element.text
        ), "Overflowing part's text should be shorter than the original."
        assert (
            len(fitted_part.text) + len(overflowing_part.text)
            >= len(text_element.text) - 1
        )  # Allow for space removal

        # The height of the fitted part should be less than or equal to the available height.
        assert (
            fitted_part.size[1] <= available_height_for_split
        ), "Fitted part's height should respect available_height."
