from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.layout.metrics.text import (
    _get_typography_params,
    calculate_text_element_height,
)
from markdowndeck.models import ElementType, TextElement


class TestTextMetricsAccuracy:
    def test_metrics_accuracy_for_wrapped_text(self):
        """
        Test Case: LAYOUT-C-METRICS-01 (Custom ID)
        Validates that calculate_text_element_height provides an accurate,
        not overestimated, height for a single long line of text that requires wrapping.
        This test directly validates the fix for the text clipping bug.
        Spec: Implicit requirement from LAYOUT_SPEC.md for content-aware sizing.
        """
        # Arrange
        long_text = "This is a single, very long line of text designed to test the wrapping capability of the text metrics. It should be broken into multiple lines by the font engine, and the resulting height should be accurate."
        text_element = TextElement(element_type=ElementType.TEXT, text=long_text)
        available_width = 400.0

        # Act
        calculated_height = calculate_text_element_height(text_element, available_width)

        # Assert
        # For comparison, get a more accurate height using the underlying font metrics directly.
        font_size, line_height_multiplier, padding, min_height = _get_typography_params(
            ElementType.TEXT, {}
        )
        _, accurate_text_height = calculate_text_bbox(
            long_text,
            font_size,
            max_width=(available_width - (padding * 2)),
            line_height_multiplier=line_height_multiplier,
        )
        expected_height = max(accurate_text_height + (padding * 2), min_height)

        # A small tolerance accounts for minor floating point differences.
        assert abs(calculated_height - expected_height) < 1.0, (
            f"Height calculation is inaccurate. "
            f"Calculated: {calculated_height:.2f}pt, Expected (approx): {expected_height:.2f}pt."
        )
