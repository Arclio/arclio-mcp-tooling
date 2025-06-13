from markdowndeck.models import ElementType, TextFormat, TextFormatType
from markdowndeck.models.elements.text import TextElement


class TestTextElementSplit:
    """Unit tests for the TextElement's split method."""

    def test_data_e_01_split_can_wrap_long_line_of_text(self):
        """
        Test Case: DATA-E-01
        Validates that TextElement.split() can split a single long line of text
        by wrapping it, preventing infinite overflow loops.
        Spec: DATA_MODELS.md, .split() Contract for TextElement
        """
        long_text = "This is a single, very long line of text designed to test the wrapping capability of the split method. It should be broken into multiple lines by the split method itself, rather than being treated as an atomic, unsplittable unit."
        available_width = 400.0
        text_element = TextElement(
            element_type=ElementType.TEXT, text=long_text, size=(available_width, 200)
        )

        available_height_for_split = 50.0
        fitted_part, overflowing_part = text_element.split(available_height_for_split)

        assert (
            fitted_part is not None
        ), "The element should have split and returned a fitted part."
        assert (
            overflowing_part is not None
        ), "An overflowing part should have been returned."
        assert (
            fitted_part.text != text_element.text
        ), "Fitted part's text should be shorter."
        assert (
            overflowing_part.text != text_element.text
        ), "Overflowing part's text should be shorter."
        assert (
            fitted_part.size[1] <= available_height_for_split
        ), "Fitted part's height must respect available_height."

    def test_split_preserves_formatting_objects(self):
        """
        Test Case: DATA-E-SPLIT-TEXT-01 (Custom ID)
        Validates that splitting a TextElement preserves the list of TextFormat objects.
        """
        long_text = "This is the first sentence.\nThis is the second sentence which is bold.\nThis is the third line."
        text_element_to_split = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
            size=(400, 100),
            formatting=[
                TextFormat(
                    start=29, end=63, format_type=TextFormatType.BOLD, value=True
                )
            ],
        )

        fitted_part, overflowing_part = text_element_to_split.split(available_height=20)

        assert overflowing_part is not None, "Overflowing part should exist."
        assert isinstance(
            overflowing_part.formatting, list
        ), "Formatting must be a list."
        if overflowing_part.formatting:
            assert all(
                isinstance(item, TextFormat) for item in overflowing_part.formatting
            )
