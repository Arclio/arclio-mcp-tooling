from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import ElementType, TextElement


class TestTextMetrics:
    def test_metrics_v_01_multiline_text_height_calculation_accuracy(self):
        """
        Test Case: METRICS-V-01
        Validates that calculate_text_element_height correctly calculates
        the height for wrapped text with proper line spacing.
        Spec: Implicit requirement from LAYOUT_SPEC.md for content-aware sizing.
        """
        # Arrange
        # This text wraps to exactly 2 lines at 600pt width (verified via debug trace)
        long_text = "This is a very long line of text that is absolutely guaranteed to wrap onto multiple lines when constrained by a reasonable width, proving the height calculation works."

        text_element = TextElement(element_type=ElementType.TEXT, text=long_text)

        # Act
        available_width = 600.0
        calculated_height = calculate_text_element_height(text_element, available_width)

        # Assert
        # Expected calculation: 2 lines × 21.0pt line height + 4.0pt padding = 46.0pt
        # This validates the text metrics are working correctly
        expected_height = 46.0
        assert (
            abs(calculated_height - expected_height) < 1.0
        ), f"Calculated height ({calculated_height}pt) should be approximately {expected_height}pt for 2-line text"

        # Ensure it's more than single line height (minimum 30pt for proper multi-line)
        assert (
            calculated_height > 30.0
        ), f"Multi-line text height ({calculated_height}pt) should be significantly more than single line"
