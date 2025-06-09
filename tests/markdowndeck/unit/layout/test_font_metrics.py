"""
Unit tests for font metrics functionality using Pillow.

These tests validate that the new Pillow-based font metrics provide
more accurate text measurement than the old character width estimation.
"""

import pytest
from markdowndeck.layout.metrics.font_metrics import (
    calculate_text_bbox,
    clear_font_cache,
    get_font_metrics,
)


class TestFontMetrics:
    """Tests for the Pillow-based font metrics functionality."""

    def teardown_method(self):
        """Clear font cache after each test."""
        clear_font_cache()

    def test_calculate_text_bbox_basic(self):
        """Test basic text bounding box calculation."""
        # Test basic text measurement
        width, height = calculate_text_bbox("Hello World", 12.0)

        assert width > 0, "Text width should be positive"
        assert height > 0, "Text height should be positive"
        assert height >= 12.0, "Height should be at least the font size"

    def test_calculate_text_bbox_empty_text(self):
        """Test handling of empty text."""
        width, height = calculate_text_bbox("", 12.0)

        assert width == 0.0, "Empty text should have zero width"
        assert height > 0, "Empty text should still have some height"

    def test_calculate_text_bbox_with_wrapping(self):
        """Test text measurement with line wrapping."""
        # Long text that should wrap
        long_text = "This is a very long piece of text that should definitely wrap across multiple lines when constrained to a narrow width"

        # Measure without wrapping
        width_no_wrap, height_no_wrap = calculate_text_bbox(long_text, 12.0)

        # Measure with wrapping constraint
        width_wrap, height_wrap = calculate_text_bbox(long_text, 12.0, max_width=200.0)

        assert width_wrap <= 200.0, "Wrapped text width should respect max_width"
        assert width_wrap < width_no_wrap, "Wrapped text should be narrower"
        assert height_wrap > height_no_wrap, "Wrapped text should be taller"

    def test_calculate_text_bbox_different_font_sizes(self):
        """Test that larger font sizes produce larger text."""
        text = "Sample Text"

        width_12, height_12 = calculate_text_bbox(text, 12.0)
        width_24, height_24 = calculate_text_bbox(text, 24.0)

        assert width_24 > width_12, "Larger font should have greater width"
        assert height_24 > height_12, "Larger font should have greater height"

        # Check approximate scaling relationship
        assert 1.8 < width_24 / width_12 < 2.2, "Width should roughly double"
        assert 1.8 < height_24 / height_12 < 2.2, "Height should roughly double"

    def test_get_font_metrics(self):
        """Test font metrics retrieval."""
        metrics = get_font_metrics(12.0)

        assert "ascent" in metrics, "Metrics should include ascent"
        assert "descent" in metrics, "Metrics should include descent"
        assert "line_height" in metrics, "Metrics should include line_height"
        assert "font_size" in metrics, "Metrics should include font_size"

        assert metrics["ascent"] > 0, "Ascent should be positive"
        assert metrics["descent"] >= 0, "Descent should be non-negative"
        assert metrics["font_size"] == 12.0, "Font size should match input"
        assert metrics["line_height"] > 0, "Line height should be positive"

    def test_font_metrics_different_sizes(self):
        """Test that font metrics scale appropriately with size."""
        metrics_12 = get_font_metrics(12.0)
        metrics_24 = get_font_metrics(24.0)

        # Larger font should have larger metrics
        assert metrics_24["ascent"] > metrics_12["ascent"]
        assert metrics_24["line_height"] > metrics_12["line_height"]

        # Check approximate scaling
        ascent_ratio = metrics_24["ascent"] / metrics_12["ascent"]
        assert 1.8 < ascent_ratio < 2.2, "Ascent should roughly scale with font size"

    def test_newline_handling(self):
        """Test that explicit newlines are handled correctly."""
        single_line = "First line"
        multi_line = "First line\nSecond line\nThird line"

        width_single, height_single = calculate_text_bbox(single_line, 12.0)
        width_multi, height_multi = calculate_text_bbox(multi_line, 12.0)

        assert height_multi > height_single, "Multi-line text should be taller"
        # Width could be larger or smaller depending on line lengths

    def test_font_cache_functionality(self):
        """Test that font caching works correctly."""
        # First call should load the font
        width1, height1 = calculate_text_bbox("Test", 12.0)

        # Second call should use cached font
        width2, height2 = calculate_text_bbox("Test", 12.0)

        assert width1 == width2, "Cached font should give same width"
        assert height1 == height2, "Cached font should give same height"

        # Clear cache and try again
        clear_font_cache()
        width3, height3 = calculate_text_bbox("Test", 12.0)

        assert width1 == width3, "Results should be consistent after cache clear"
        assert height1 == height3, "Results should be consistent after cache clear"

    def test_accuracy_vs_estimation(self):
        """Test that font metrics are more accurate than character width estimation."""
        text = "This text has varying character widths: iii vs WWW"
        font_size = 14.0
        available_width = 300.0

        # Get accurate measurement using font metrics
        accurate_width, accurate_height = calculate_text_bbox(
            text, font_size, max_width=available_width
        )

        # Simulate old character width estimation
        CHAR_WIDTH = 5.0  # Old estimation
        estimated_width = len(text) * CHAR_WIDTH

        # Font-based measurement should be more precise
        assert (
            accurate_width != estimated_width
        ), "Font metrics should differ from estimation"

        # The accurate measurement should account for actual character widths
        # 'i' characters are narrower than 'W' characters in most fonts
        narrow_text = "iiiiiiiiiiiiiiiiii"  # 18 i's
        wide_text = "WWWWWWWWWWWWWWWWWW"  # 18 W's

        narrow_width, _ = calculate_text_bbox(narrow_text, font_size)
        wide_width, _ = calculate_text_bbox(wide_text, font_size)

        assert (
            wide_width > narrow_width
        ), "Wide characters should be wider than narrow ones"

    def test_robustness_with_special_characters(self):
        """Test handling of special characters and unicode."""
        special_texts = [
            "Hello 世界",  # Mixed ASCII and Unicode
            "Héllö Wörld",  # Accented characters
            "Text with\ttabs",  # Tab characters
            "Line 1\n\nLine 3",  # Multiple newlines
            "Émojis: 😀🎉🚀",  # Emoji characters
        ]

        for text in special_texts:
            try:
                width, height = calculate_text_bbox(text, 12.0)
                assert width >= 0, f"Width should be non-negative for: {text!r}"
                assert height > 0, f"Height should be positive for: {text!r}"
            except Exception as e:
                pytest.fail(f"Failed to measure text {text!r}: {e}")

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Very small font size
        width, height = calculate_text_bbox("Test", 1.0)
        assert width > 0 and height > 0, "Very small font should still work"

        # Very large font size
        width, height = calculate_text_bbox("Test", 100.0)
        assert width > 0 and height > 0, "Very large font should still work"

        # Single character
        width, height = calculate_text_bbox("A", 12.0)
        assert width > 0 and height > 0, "Single character should work"

        # Only whitespace
        width, height = calculate_text_bbox("   ", 12.0)
        assert width >= 0, "Whitespace should have non-negative width"
        assert height > 0, "Whitespace should have positive height"
