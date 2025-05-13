from typing import Any

import pytest
from markdowndeck.parser.directive.converters import (
    convert_alignment,
    convert_dimension,
    convert_style,
    get_color_names,  # Helper, can be tested indirectly or directly
)


class TestDirectiveConverters:
    """Unit tests for directive value converter functions."""

    # --- Test convert_dimension ---
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1/2", 0.5),
            (" 2/3 ", 2 / 3),
            ("100%", 1.0),
            (" 50% ", 0.5),
            ("25.5%", 0.255),
            ("300", 300),
            (" 150 ", 150),
            ("75.5", 75.5),
            ("0", 0),
            ("0.0", 0.0),
            ("1", 1),
            ("0.9", 0.9),
        ],
    )
    def test_convert_dimension_valid(self, value: str, expected: float):
        assert convert_dimension(value) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("invalid_value", "error_message_match"),
        [
            ("abc", "Invalid dimension format"),
            ("1/2/3", "Invalid fraction format"),
            ("1 / abc", "Invalid fraction format"),
            ("50%abc", "Invalid dimension format"),
            ("abc%", "Invalid dimension format"),
            ("--50", "Invalid dimension format"),
            ("", "Invalid dimension format"),  # Empty string
        ],
    )
    def test_convert_dimension_invalid_format(self, invalid_value: str, error_message_match: str):
        with pytest.raises(ValueError, match=error_message_match):
            convert_dimension(invalid_value)

    def test_convert_dimension_division_by_zero(self):
        with pytest.raises(ValueError, match="division by zero"):
            convert_dimension("1/0")
        with pytest.raises(ValueError, match="division by zero"):
            convert_dimension(" 3 / 0.0 ")

    # --- Test convert_alignment ---
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("left", "left"),
            ("CENTER", "center"),
            (" right ", "right"),
            ("justify", "justify"),
            ("top", "top"),
            ("middle", "middle"),
            ("bottom", "bottom"),
            ("start", "left"),  # Alias
            ("END", "right"),  # Alias, case-insensitive
            ("centered", "center"),
            ("justified", "justify"),
        ],
    )
    def test_convert_alignment_valid(self, value: str, expected: str):
        assert convert_alignment(value) == expected

    def test_convert_alignment_unknown(self):
        """Test that unknown alignment values are passed through (as per current implementation)."""
        assert convert_alignment("unknown_align") == "unknown_align"
        assert convert_alignment(" spaced unknown ") == "spaced unknown"

    # --- Test convert_style ---
    @pytest.mark.parametrize(
        ("value", "expected_type", "expected_value"),
        [
            ("#FF0000", "color", "#FF0000"),
            (" #f00 ", "color", "#f00"),
            ("blue", "color", "blue"),
            ("transparent", "color", "transparent"),
            (
                "url(http://example.com/image.jpg)",
                "url",
                "http://example.com/image.jpg",
            ),
            ("url('path/to/img.png')", "url", "path/to/img.png"),
            (
                'url( "another/img with spaces.gif" )',
                "url",
                "another/img with spaces.gif",
            ),
            ("solid", "border-style", "solid"),
            ("dotted", "border-style", "dotted"),
            ("custom_value", "value", "custom_value"),  # Generic value
            ("123", "value", "123"),  # Numeric string not matching other patterns
        ],
    )
    def test_convert_style_valid(self, value: str, expected_type: str, expected_value: Any):
        assert convert_style(value) == (expected_type, expected_value)

    def test_convert_style_invalid_hex(self):
        """Test that invalid hex colors are still returned as type 'color' but value as is."""
        # The current convert_style logs a warning for invalid hex but returns it.
        # This test verifies that behavior.
        assert convert_style("#12345G") == ("color", "#12345G")  # Invalid hex char G
        assert convert_style("#1234") == ("color", "#1234")  # Invalid length
        # Double hash now treated as a color
        assert convert_style("##123456") == ("color", "##123456")

    def test_get_color_names(self):
        """Test the helper for color names (simple check)."""
        names = get_color_names()
        assert "red" in names
        assert "fuchsia" in names
        assert "nonexistentcolor" not in names
