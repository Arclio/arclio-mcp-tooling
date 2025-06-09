from markdowndeck.models import ElementType, TextFormat, TextFormatType
from markdowndeck.models.elements.text import TextElement


class TestTextElementSplit:
    def test_split_preserves_formatting_objects(self):
        """
        Test Case: OVERFLOW-C-05
        Validates that splitting a TextElement preserves the list of TextFormat objects,
        preventing data corruption into booleans or other types.
        Spec: DATA_MODELS.md, section 3.5 TextFormat
        """
        # Arrange - Use multi-line text to enable splitting
        long_text = "This is the first sentence.\nThis is the second sentence which is bold.\nThis is the third line."
        text_element_to_split = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
            size=(400, 100),  # A size that will force a split
            formatting=[
                # Bold formatting for "second sentence which is bold" in line 2
                TextFormat(
                    start=29, end=63, format_type=TextFormatType.BOLD, value=True
                )
            ],
        )

        # Act: Split the element at a height that will bisect the text
        fitted_part, overflowing_part = text_element_to_split.split(available_height=20)

        # Assert
        assert overflowing_part is not None, "Overflowing part should exist."
        # The overflowing part should contain the lines that didn't fit
        assert (
            "second sentence which is bold" in overflowing_part.text
            or "third line" in overflowing_part.text
        ), "Overflowing part should contain later lines."

        assert isinstance(
            overflowing_part.formatting, list
        ), "Formatting must be a list."
        assert (
            len(overflowing_part.formatting) > 0
        ), "Overflowing part should have formatting."

        # This is the key assertion. It fails if the list contains anything other than TextFormat objects.
        for item in overflowing_part.formatting:
            assert isinstance(
                item, TextFormat
            ), f"Formatting list contains invalid type: {type(item)}. Item: {item}"
            assert (
                item.start >= 0
            ), "Start index of formatting in overflowing part should be non-negative."

    def test_split_formatting_corruption_detection(self):
        """
        Test Case: OVERFLOW-C-06
        Specific test to detect the exact formatting corruption described in TASK_005:
        formatting: [true, true] instead of proper TextFormat objects.
        """
        # Arrange: Create text that will definitely overflow and has multiple formatting
        text_with_formatting = (
            "This section also contains a bolded word and an italicized one."
        )
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=text_with_formatting,
            size=(400, 40),
            formatting=[
                TextFormat(
                    start=30, end=36, format_type=TextFormatType.BOLD, value=True
                ),  # "bolded"
                TextFormat(
                    start=50, end=61, format_type=TextFormatType.ITALIC, value=True
                ),  # "italicized"
            ],
        )

        # Act: Force a split
        fitted_part, overflowing_part = text_element.split(available_height=20)

        # Assert: Check for the specific corruption mentioned in TASK_005
        if overflowing_part is not None and overflowing_part.formatting:
            # Check if we have the corruption: [true, true] instead of TextFormat objects
            if len(overflowing_part.formatting) == 2:
                # This is the exact scenario from TASK_005
                first_item = overflowing_part.formatting[0]
                second_item = overflowing_part.formatting[1]

                # If we see [true, true] this is the corruption bug
                if first_item is True and second_item is True:
                    raise AssertionError(
                        "CORRUPTION DETECTED: formatting contains [true, true] instead of TextFormat objects!"
                    )

                # Check for other types of corruption
                if not isinstance(first_item, TextFormat) or not isinstance(
                    second_item, TextFormat
                ):
                    raise AssertionError(
                        f"CORRUPTION DETECTED: formatting contains non-TextFormat objects: [{type(first_item)}, {type(second_item)}]"
                    )
