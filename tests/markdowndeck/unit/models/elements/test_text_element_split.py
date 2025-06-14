from markdowndeck.models import ElementType, TextFormat, TextFormatType
from markdowndeck.models.elements.text import TextElement


class TestTextElementSplit:
    """Unit tests for the TextElement's split method."""

    def test_data_e_01_split_uses_line_metrics(self):
        """
        Test Case: DATA-E-01 (Refactored)
        Validates TextElement.split() uses pre-calculated _line_metrics.
        """
        # Arrange
        long_text = "This is a single, very long line of text. It will be split into two lines based on metrics."
        # Mock pre-calculated line metrics from the LayoutManager
        mock_line_metrics = [
            {
                "start": 0,
                "end": 42,
                "height": 18.0,
            },  # "This is a single, very long line of text."
            {"start": 43, "end": 100, "height": 18.0},  # "It will be split..."
        ]
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
            size=(400, 36),
            _line_metrics=mock_line_metrics,
        )

        # Split at a height that only allows the first line.
        available_height_for_split = 20.0  # Includes padding
        fitted_part, overflowing_part = text_element.split(available_height_for_split)

        assert fitted_part is not None, "Element should have split."
        assert overflowing_part is not None, "An overflowing part should exist."

        # Check that the split happened at the character index from the metrics
        expected_split_point = mock_line_metrics[0]["end"]
        assert fitted_part.text == long_text[:expected_split_point]
        assert overflowing_part.text.strip() == long_text[expected_split_point:].strip()
        assert fitted_part.size[1] <= available_height_for_split

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
            formatting=[TextFormat(start=29, end=63, format_type=TextFormatType.BOLD, value=True)],
            _line_metrics=[
                {"start": 0, "end": 28, "height": 20},
                {"start": 29, "end": 63, "height": 20},
                {"start": 64, "end": 86, "height": 20},
            ],
        )

        fitted_part, overflowing_part = text_element_to_split.split(available_height=25)

        assert overflowing_part is not None, "Overflowing part should exist."
        assert isinstance(overflowing_part.formatting, list), "Formatting must be a list."
        assert len(overflowing_part.formatting) > 0, "Formatting should be propagated to overflow"
        if overflowing_part.formatting:
            assert all(isinstance(item, TextFormat) for item in overflowing_part.formatting)

    def test_data_flow_3_4_split_preserves_directives(self):
        """
        Test Case: DATA_FLOW.md, Sec 3.4
        Spec: `.split()` must deep-copy directives to both fitted and overflowing parts.
        """
        # Arrange
        long_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
            size=(400, 100),
            directives={"color": "red", "align": "center"},
            _line_metrics=[
                {"start": 0, "end": 6, "height": 20},
                {"start": 7, "end": 13, "height": 20},
            ],  # simplified
        )

        # Act
        fitted_part, overflowing_part = text_element.split(available_height=25)

        # Assert
        assert fitted_part is not None, "Fitted part should exist."
        assert overflowing_part is not None, "Overflowing part should exist."

        assert fitted_part.directives == {
            "color": "red",
            "align": "center",
        }, "Fitted part must inherit directives."
        assert overflowing_part.directives == {
            "color": "red",
            "align": "center",
        }, "Overflowing part must inherit directives."
