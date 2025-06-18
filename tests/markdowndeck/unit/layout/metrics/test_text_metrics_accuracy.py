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
        # REFACTORED: Unpack all 3 return values.
        _, accurate_text_height, _ = calculate_text_bbox(
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

    def test_metrics_accuracy_multiple_lines(self):
        """Validates height calculation for text that wraps to multiple lines."""
        text_content = " ".join(
            [
                "This is a test sentence that we will repeat several times to ensure that it wraps to multiple lines for this specific container width and provides better coverage."
            ]
            * 3
        )
        text_element = TextElement(element_type=ElementType.TEXT, text=text_content)
        available_width = 420.0

        calculated_height = calculate_text_element_height(text_element, available_width)

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
            len(line_metrics) >= 5
        ), f"Test setup failed: expected at least 5 lines, but got {len(line_metrics)}."
        assert (
            abs(calculated_height - expected_height) < 2.0
        ), f"Height calculation is inaccurate for multiple lines. Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}"

    def test_metrics_accuracy_with_explicit_newlines(self):
        """Validates height calculation for text containing explicit newlines."""
        text_content = "First line.\nSecond line, which is a bit longer.\nThird line."
        text_element = TextElement(element_type=ElementType.TEXT, text=text_content)
        available_width = 800.0  # Wide enough to not cause wrapping

        calculated_height = calculate_text_element_height(text_element, available_width)

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
            len(line_metrics) == 3
        ), f"Test setup failed: expected 3 lines for explicit newlines, but got {len(line_metrics)}."
        assert (
            abs(calculated_height - expected_height) < 2.0
        ), f"Height calculation is inaccurate for explicit newlines. Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}"

    def test_metrics_accuracy_from_notebook(self):
        """
        Test Case: REPRODUCES NOTEBOOK BUG
        Validates height calculation for multi-line text with a large line-spacing multiplier.
        This test is derived directly from the user-provided diagnostic notebook.
        """
        text_content = "Title\nPress Mentions\nCampaign Benchmarks\nPartnership Information\nAdditional Data\nCampaign Hero Stats\nSocial Media Metrics"
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text=text_content,
            directives={"line-spacing": 1.8},
        )
        available_width = 206.0

        calculated_height = calculate_text_element_height(text_element, available_width)

        font_size, line_height_multiplier, padding, min_height = _get_typography_params(
            ElementType.TEXT, {"line-spacing": 1.8}
        )
        _, accurate_text_height, line_metrics = calculate_text_bbox(
            text_content,
            font_size,
            max_width=(available_width - (padding * 2)),
            line_height_multiplier=line_height_multiplier,
        )
        expected_height = max(accurate_text_height + (padding * 2), min_height)

        assert len(line_metrics) == 7, "Test setup failed: expected 7 lines."
        # Use a slightly larger tolerance for this known-tricky case
        assert (
            abs(calculated_height - expected_height) < 5.0
        ), f"Height is inaccurate for large line-spacing. Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}"

    def test_metrics_accuracy_short_wrap(self):
        """Validates height calculation when only a single short word wraps."""
        text_content = "This line of text will wrap just one single tiny word."
        text_element = TextElement(element_type=ElementType.TEXT, text=text_content)
        available_width = 300.0

        calculated_height = calculate_text_element_height(text_element, available_width)

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

        assert len(line_metrics) > 1, "Test setup failed: text did not wrap."
        assert (
            abs(calculated_height - expected_height) < 2.0
        ), f"Height calculation is inaccurate for short wrap. Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}"

    def test_metrics_accuracy_multiline_text(self):
        """Validates height calculation for text that wraps to multiple lines."""
        text_content = " ".join(
            [
                "This is a test sentence that we will repeat several times to ensure that it wraps to multiple lines for this specific container width."
            ]
            * 2
        )
        text_element = TextElement(element_type=ElementType.TEXT, text=text_content)
        available_width = 450.0

        calculated_height = calculate_text_element_height(text_element, available_width)

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
            len(line_metrics) >= 3
        ), f"Test setup failed: expected at least 3 lines, but got {len(line_metrics)}."
        assert (
            abs(calculated_height - expected_height) < 2.0
        ), f"Height calculation is inaccurate for multiline text. Calculated: {calculated_height:.2f}, Expected: {expected_height:.2f}"
