"""
Unit tests for font metrics functionality using Pillow.
"""

from markdowndeck.layout.metrics.font_metrics import (
    calculate_text_bbox,
    clear_font_cache,
)


class TestFontMetrics:
    """Tests for the Pillow-based font metrics functionality."""

    def teardown_method(self):
        """Clear font cache after each test."""
        clear_font_cache()

    def test_calculate_text_bbox_basic(self):
        """Test basic text bounding box calculation."""
        width, height = calculate_text_bbox("Hello World", 12.0)
        assert width > 0, "Text width should be positive"
        assert height > 0, "Text height should be positive"
        assert height >= 12.0, "Height should be at least the font size"

    def test_calculate_text_bbox_with_wrapping(self):
        """Test text measurement with line wrapping."""
        long_text = "This is a very long piece of text that should definitely wrap across multiple lines."
        width_no_wrap, height_no_wrap = calculate_text_bbox(long_text, 12.0)
        width_wrap, height_wrap = calculate_text_bbox(long_text, 12.0, max_width=200.0)

        assert width_wrap <= 200.0, "Wrapped text width should respect max_width"
        assert width_wrap < width_no_wrap, "Wrapped text should be narrower"
        assert height_wrap > height_no_wrap, "Wrapped text should be taller"
