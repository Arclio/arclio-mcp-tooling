# File: tests/markdowndeck/unit/layout/metrics/test_text_metrics_accuracy.py

from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.layout.metrics.text import (
    _get_typography_params,
    calculate_text_element_height,
)
from markdowndeck.models import ElementType, TextElement


class TestTextMetricsAccuracy:
    def test_metrics_v_02_long_line_height_is_accurate(self):
        """
        Test Case: METRICS-V-02 (new)
        Validates that calculate_text_element_height provides an accurate,
        not overestimated, height for a single long line of text that requires wrapping.
        Spec: Implicit requirement from LAYOUT_SPEC.md for content-aware sizing.
        """
        # Arrange
        # A long line of text similar to the one that caused the original issue.
        long_text = "This is a single, very long line of text designed to test the wrapping capability of the split method. It should be broken into multiple lines by the split method itself, rather than being treated as an atomic, unsplittable unit."

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=long_text,
        )

        available_width = 400.0

        # Act
        # Calculate the height using the function under test.
        calculated_height = calculate_text_element_height(text_element, available_width)

        # For comparison, get a more accurate height using the underlying font metrics directly.
        # This gives us a baseline for what a "reasonable" height should be.
        # We assume the font metrics themselves are accurate.
        font_size, line_height_multiplier, _, padding, min_height = (
            _get_typography_params(ElementType.TEXT)
        )
        _, accurate_text_height = calculate_text_bbox(
            long_text,
            font_size,
            max_width=(available_width - padding),
            line_height_multiplier=line_height_multiplier,
        )
        expected_height = max(accurate_text_height + padding, min_height)

        # Verify calculations are reasonable (for debugging if needed)
        # calculated_height: 88.0pt, expected_height: 88.0pt, ratio: 1.00 (accurate!)

        # Assert
        # The calculated height should not be drastically larger than the expected height.
        # We allow a generous tolerance (e.g., 50%) to account for minor differences,
        # but this will catch the absurd overestimations like 235pt for a few lines of text.
        assert calculated_height < expected_height * 1.5, (
            f"Height calculation is likely inaccurate. "
            f"Calculated: {calculated_height:.2f}pt, Expected (approx): {expected_height:.2f}pt. "
            f"The calculated height is more than 50% larger than the baseline."
        )

        # Also assert that the height is not absurdly large in absolute terms.
        assert (
            calculated_height < 100.0
        ), f"Calculated height ({calculated_height:.2f}pt) is absurdly large for the given text."
