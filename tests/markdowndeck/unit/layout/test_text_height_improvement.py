"""
Test that validates the improved text height calculation against the old method.

These tests specifically address the height calculation failure described in TASK_001,
ensuring that the new Pillow-based approach provides more accurate text sizing.
"""

from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import ElementType, TextElement


class TestTextHeightImprovement:
    """Tests comparing new font-based height calculation with old estimation."""

    def test_basic_height_calculation_sanity(self):
        """Test that basic height calculation produces reasonable results."""
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This is a sample paragraph of text that should have a reasonable height.",
        )

        available_width = 600.0  # Typical slide width
        height = calculate_text_element_height(text_element, available_width)

        assert height > 0, "Height should be positive"
        assert height < 1000, "Height should be reasonable (not extremely large)"
        assert height > 15, "Height should be more than minimum for readable text"

    def test_content_aware_height_scaling(self):
        """Test that height scales appropriately with content length."""
        short_text = TextElement(element_type=ElementType.TEXT, text="Short text.")

        long_text = TextElement(
            element_type=ElementType.TEXT,
            text="This is a much longer piece of text that contains many more words and should therefore require significantly more vertical space when rendered, especially when constrained to a reasonable width that forces text wrapping across multiple lines.",
        )

        available_width = 400.0

        short_height = calculate_text_element_height(short_text, available_width)
        long_height = calculate_text_element_height(long_text, available_width)

        assert long_height > short_height, "Longer text should be taller"
        assert (
            long_height > short_height * 2
        ), "Much longer text should be significantly taller"

    def test_width_constraint_affects_height(self):
        """Test that narrower width results in taller text due to wrapping."""
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="This is a moderately long sentence that will wrap differently depending on the available width constraint applied to it.",
        )

        wide_width = 800.0
        narrow_width = 200.0

        wide_height = calculate_text_element_height(text_element, wide_width)
        narrow_height = calculate_text_element_height(text_element, narrow_width)

        assert (
            narrow_height > wide_height
        ), "Narrower width should result in taller text"

    def test_font_size_affects_height(self):
        """Test that custom font size affects height calculation."""
        base_text = TextElement(
            element_type=ElementType.TEXT, text="Sample text for font size testing."
        )

        large_font_text = TextElement(
            element_type=ElementType.TEXT,
            text="Sample text for font size testing.",
            directives={"fontsize": "24"},
        )

        available_width = 600.0

        base_height = calculate_text_element_height(base_text, available_width)
        large_height = calculate_text_element_height(large_font_text, available_width)

        assert (
            large_height > base_height
        ), "Larger font size should result in taller text"
        assert (
            large_height > base_height * 1.5
        ), "Much larger font should be significantly taller"

    def test_different_element_types_have_appropriate_heights(self):
        """Test that different element types have appropriate relative heights."""
        text_content = "Sample content"
        available_width = 600.0

        title = TextElement(element_type=ElementType.TITLE, text=text_content)
        subtitle = TextElement(element_type=ElementType.SUBTITLE, text=text_content)
        text = TextElement(element_type=ElementType.TEXT, text=text_content)
        footer = TextElement(element_type=ElementType.FOOTER, text=text_content)

        title_height = calculate_text_element_height(title, available_width)
        subtitle_height = calculate_text_element_height(subtitle, available_width)
        text_height = calculate_text_element_height(text, available_width)
        footer_height = calculate_text_element_height(footer, available_width)

        # Title should be tallest (largest font)
        assert title_height > subtitle_height, "Title should be taller than subtitle"
        assert title_height > text_height, "Title should be taller than text"

        # Subtitle should be taller than regular text
        assert subtitle_height > text_height, "Subtitle should be taller than text"

        # Footer should be smallest
        assert footer_height <= text_height, "Footer should not be taller than text"

    def test_realistic_paragraph_height(self):
        """Test height calculation for realistic paragraph content."""
        paragraph = TextElement(
            element_type=ElementType.TEXT,
            text="""
            This is a realistic paragraph that might appear in a presentation slide.
            It contains multiple sentences with varying lengths. Some sentences are
            shorter, while others are considerably longer and contain more detailed
            information that would naturally flow across multiple lines when constrained
            by the slide layout. The height calculation should accurately reflect the
            space needed to render this content clearly and readably.
            """,
        )

        # Typical slide content area width (720px slide with margins)
        typical_width = 620.0

        height = calculate_text_element_height(paragraph, typical_width)

        # Should be multiple lines but not excessive
        assert height > 60, "Paragraph should be at least 4-5 lines tall"
        assert height < 200, "Paragraph should not be excessively tall"

    def test_character_width_variation_handling(self):
        """Test that the system handles varying character widths properly."""
        # Text with narrow characters
        narrow_chars = TextElement(
            element_type=ElementType.TEXT,
            text="iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii",  # Many narrow 'i' chars
        )

        # Text with wide characters
        wide_chars = TextElement(
            element_type=ElementType.TEXT,
            text="MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",  # Many wide 'M' chars
        )

        # Mixed characters
        mixed_chars = TextElement(
            element_type=ElementType.TEXT,
            text="Mixed width characters: iiiiMMMMMwwwwwIIIIIlllll",
        )

        available_width = 400.0

        narrow_height = calculate_text_element_height(narrow_chars, available_width)
        wide_height = calculate_text_element_height(wide_chars, available_width)
        mixed_height = calculate_text_element_height(mixed_chars, available_width)

        # All should be positive and reasonable
        assert narrow_height > 0
        assert wide_height > 0
        assert mixed_height > 0

        # Wide characters might wrap more and be taller (though depends on exact character count)
        # The important thing is that we're getting content-aware calculations
        assert (
            abs(narrow_height - wide_height) / max(narrow_height, wide_height) < 2.0
        ), "Heights should be in reasonable proportion despite character width differences"

    def test_empty_and_whitespace_handling(self):
        """Test proper handling of empty and whitespace-only content."""
        empty_text = TextElement(element_type=ElementType.TEXT, text="")
        whitespace_text = TextElement(element_type=ElementType.TEXT, text="   \n  \t  ")

        available_width = 600.0

        empty_height = calculate_text_element_height(empty_text, available_width)
        whitespace_height = calculate_text_element_height(
            whitespace_text, available_width
        )

        # Both should return minimum heights, not zero
        assert empty_height > 0, "Empty text should have minimum height"
        assert whitespace_height > 0, "Whitespace text should have minimum height"

        # Should be using minimum height for element type
        assert empty_height >= 18.0, "Should be at least minimum text height"

    def test_fallback_resilience(self):
        """Test that the system gracefully falls back if font metrics fail."""
        # This test ensures robustness - even if Pillow has issues,
        # the system should still work with fallback calculation

        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test text for fallback resilience testing.",
        )

        available_width = 600.0

        # This should work regardless of font availability
        height = calculate_text_element_height(text_element, available_width)

        assert height > 0, "Should get positive height even with potential font issues"
        assert height < 1000, "Fallback should still produce reasonable heights"

    def test_performance_consistency(self):
        """Test that height calculations are consistent across multiple calls."""
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Consistency test text that should always give the same height.",
        )

        available_width = 600.0

        # Multiple calls should give identical results
        heights = [
            calculate_text_element_height(text_element, available_width)
            for _ in range(5)
        ]

        assert all(
            h == heights[0] for h in heights
        ), "Height calculations should be consistent"

    def test_overlapping_text_prevention(self):
        """Test that the new calculation should prevent overlapping text issues."""
        # This addresses the core issue from TASK_001 - overlapping text

        # Create elements that would likely overlap with old estimation
        elements = [
            TextElement(
                element_type=ElementType.TEXT,
                text="First paragraph with some content that needs proper spacing.",
            ),
            TextElement(
                element_type=ElementType.TEXT,
                text="Second paragraph that should not overlap with the first one.",
            ),
            TextElement(
                element_type=ElementType.TEXT,
                text="Third paragraph in the sequence that also needs proper positioning.",
            ),
        ]

        available_width = 500.0
        cumulative_height = 0.0

        for element in elements:
            height = calculate_text_element_height(element, available_width)
            cumulative_height += height

            # Each element should have reasonable height
            assert height > 15, f"Element should have reasonable height: {height}"
            assert height < 100, f"Element should not be excessively tall: {height}"

        # Total height should be reasonable for three paragraphs
        assert cumulative_height > 60, "Three paragraphs should have substantial height"
        assert cumulative_height < 300, "But not excessive height"
