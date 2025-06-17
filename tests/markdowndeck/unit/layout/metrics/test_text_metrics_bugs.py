from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.layout.metrics.text import (
    _get_typography_params,
    calculate_text_element_height,
)
from markdowndeck.models import ElementType, TextElement


class TestTextMetricsBugReproduction:
    def test_bug_text_element_height_is_one_line_too_short(self):
        """
        Test Case: LAYOUT-BUG-03
        Description: Exposes the bug where the calculated height for a text element is
                     consistently one line less than required, causing the last line to be clipped.
        Expected to Fail: YES. The calculated_height will be smaller than the expected_height.
        """
        # Arrange: A text block that will wrap to exactly two lines.
        text_content = "This is a line of text that is precisely long enough to wrap onto a second line."
        text_element = TextElement(element_type=ElementType.TEXT, text=text_content)
        available_width = 300.0  # A width that forces wrapping

        # Act
        calculated_height = calculate_text_element_height(text_element, available_width)

        # Assert: Compare with a direct, known-accurate calculation.
        font_size, line_height_multiplier, padding, min_height = _get_typography_params(
            ElementType.TEXT, {}
        )
        _, accurate_text_height, line_metrics = calculate_text_bbox(
            text_content,
            font_size,
            max_width=(available_width - (padding * 2)),
            line_height_multiplier=line_height_multiplier,
        )
        expected_height = max(accurate_text_height + (padding * 2), min_height)

        assert (
            len(line_metrics) > 1
        ), "Test setup failed: text did not wrap to multiple lines."

        # The key assertion: the calculated height must be very close to the expected height.
        assert abs(calculated_height - expected_height) < 1.0, (
            "BUG CONFIRMED: Calculated height is inaccurate. "
            f"Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}. "
            "This suggests the height for the last line of text is being omitted."
        )

    def test_bug_heading_typography_is_ignored(self):
        """
        Test Case: LAYOUT-BUG-04
        Description: Exposes the bug where heading levels (###, ####, etc.) are parsed
                     but their specific font sizes are ignored during layout, making them
                     appear the same as regular text.
        Expected to Fail: YES. The height will be calculated using P_FONT_SIZE, not H3_FONT_SIZE.
        """
        from markdowndeck.layout.constants import H3_FONT_SIZE, P_FONT_SIZE

        # Arrange
        heading_element = TextElement(
            element_type=ElementType.TEXT, text="This is an H3", heading_level=3
        )
        # For comparison, a regular text element
        text_element = TextElement(
            element_type=ElementType.TEXT, text="This is regular text"
        )
        available_width = 500.0

        # Act
        heading_height = calculate_text_element_height(heading_element, available_width)
        text_height = calculate_text_element_height(text_element, available_width)

        # Assert
        assert (
            H3_FONT_SIZE > P_FONT_SIZE
        ), "Test constant assumption is wrong: H3 should be larger than P."
        assert heading_height > text_height, (
            "BUG CONFIRMED: Heading element height should be greater than regular text element height "
            "due to larger font size, but they are the same."
        )

    def test_bug_line_spacing_directive_is_ignored_in_height_calculation(self):
        """
        Test Case: LAYOUT-BUG-05 (Custom ID)
        Description: Exposes the bug where the `line-spacing` directive is not factored
        into height calculations by the LayoutManager, leading to clipping.
        Expected to Fail: YES. The calculated height will not reflect the line spacing multiplier.
        """
        # Arrange
        text_content = "First Line\nSecond Line"
        element_with_spacing = TextElement(
            element_type=ElementType.TEXT,
            text=text_content,
            directives={"line-spacing": 2.0},  # 200% line spacing
        )
        element_without_spacing = TextElement(
            element_type=ElementType.TEXT, text=text_content, directives={}
        )
        available_width = 500.0

        # Act
        height_with_spacing = calculate_text_element_height(
            element_with_spacing, available_width
        )
        height_without_spacing = calculate_text_element_height(
            element_without_spacing, available_width
        )

        # Assert
        assert (
            height_with_spacing > height_without_spacing
        ), "BUG CONFIRMED: Element with line-spacing should have a greater height than one without."

        font_size, default_multiplier, padding, _ = _get_typography_params(
            ElementType.TEXT, {}
        )
        # More precise check
        # Expected height should be roughly double (minus padding differences)
        expected_ratio = 2.0 / default_multiplier
        actual_ratio = (height_with_spacing - (padding * 2)) / (
            height_without_spacing - (padding * 2)
        )

        assert (
            abs(actual_ratio - expected_ratio) < 0.1
        ), f"The height ratio ({actual_ratio:.2f}) does not match the expected line-spacing ratio ({expected_ratio:.2f})."
