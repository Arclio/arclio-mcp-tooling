"""Updated unit tests for directive value converters with P8 enhancements."""

from typing import Any

import pytest
from markdowndeck.parser.directive.converters import (
    convert_alignment,
    convert_dimension,
    convert_style,
    get_color_names,
    get_theme_colors,
)


class TestDirectiveConverters:
    """Updated unit tests for directive value converter functions."""

    # ========================================================================
    # Dimension Conversion Tests (Enhanced for P8)
    # ========================================================================

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # Fractions
            ("1/2", 0.5),
            (" 2/3 ", 2 / 3),
            ("3/4", 0.75),
            # Percentages
            ("100%", 1.0),
            (" 50% ", 0.5),
            ("25.5%", 0.255),
            ("0%", 0.0),
            # Absolute values
            ("300", 300),
            (" 150 ", 150),
            ("75.5", 75.5),
            ("0", 0),
            ("1", 1),
            # CSS units (P8 enhancement)
            ("16px", 16),
            ("1.5em", 1.5),
            ("2rem", 2),
            ("10pt", 10),
            ("1in", 1),
            ("2.5cm", 2.5),
            ("100vh", 100),
            ("50vw", 50),
        ],
    )
    def test_convert_dimension_valid(self, value: str, expected: float):
        """Test valid dimension conversions including CSS units."""
        result = convert_dimension(value)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("invalid_value", "error_message_match"),
        [
            ("abc", "Invalid dimension format"),
            ("1/2/3", "Invalid fraction format"),
            ("1 / abc", "Invalid fraction format"),
            ("50%abc", "Invalid dimension format"),
            ("abc%", "Invalid dimension format"),
            ("--50", "Invalid dimension format"),
            ("", "Invalid dimension format"),
            ("px", "Invalid dimension format"),  # Unit without number
            ("1/0", "division by zero"),
        ],
    )
    def test_convert_dimension_invalid_format(self, invalid_value: str, error_message_match: str):
        """Test invalid dimension formats raise appropriate errors."""
        with pytest.raises(ValueError, match=error_message_match):
            convert_dimension(invalid_value)

    # ========================================================================
    # Alignment Conversion Tests (Enhanced)
    # ========================================================================

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # Standard alignments
            ("left", "left"),
            ("CENTER", "center"),
            (" right ", "right"),
            ("justify", "justify"),
            ("top", "top"),
            ("middle", "middle"),
            ("bottom", "bottom"),
            ("baseline", "baseline"),
            # Aliases (P8 enhancement)
            ("start", "left"),
            ("END", "right"),
            ("centered", "center"),
            ("justified", "justify"),
            ("flex-start", "left"),
            ("flex-end", "right"),
            ("space-between", "justify"),
        ],
    )
    def test_convert_alignment_valid(self, value: str, expected: str):
        """Test valid alignment conversions including CSS aliases."""
        assert convert_alignment(value) == expected

    def test_convert_alignment_unknown(self):
        """Test unknown alignment values are passed through."""
        result = convert_alignment("unknown_align")
        assert result == "unknown_align"

    # ========================================================================
    # Style Conversion Tests (Comprehensive P8 Enhancements)
    # ========================================================================

    @pytest.mark.parametrize(
        ("value", "expected_type", "expected_properties"),
        [
            # Hex colors
            ("#FF0000", "color", {"type": "hex", "value": "#FF0000"}),
            ("#f00", "color", {"type": "hex", "value": "#f00"}),
            ("#FF0000FF", "color", {"type": "hex", "value": "#FF0000FF"}),  # With alpha
            # Named colors
            ("blue", "color", {"type": "named", "value": "blue"}),
            ("transparent", "color", {"type": "named", "value": "transparent"}),
            ("darkred", "color", {"type": "named", "value": "darkred"}),
            # Theme colors
            ("ACCENT1", "color", {"type": "theme", "themeColor": "ACCENT1"}),
            ("text1", "color", {"type": "theme", "themeColor": "TEXT1"}),
            # URLs
            ("url(image.jpg)", "url", {"type": "url", "value": "image.jpg"}),
            ("url('path/img.png')", "url", {"type": "url", "value": "path/img.png"}),
            # Border styles
            ("solid", "border_style", "solid"),
            ("dashed", "border_style", "dashed"),
            ("dotted", "border_style", "dotted"),
            # Generic values
            ("custom_value", "value", "custom_value"),
        ],
    )
    def test_convert_style_basic_values(self, value: str, expected_type: str, expected_properties: Any):
        """Test basic style value conversions."""
        result_type, result_value = convert_style(value)
        assert result_type == expected_type

        if isinstance(expected_properties, dict):
            for key, expected_val in expected_properties.items():
                assert result_value[key] == expected_val
        else:
            assert result_value == expected_properties

    def test_convert_style_rgba_colors(self):
        """Test rgba color parsing (P8 enhancement)."""
        test_cases = [
            ("rgba(255, 0, 0, 1)", {"r": 255, "g": 0, "b": 0, "a": 1.0}),
            ("rgba(128, 64, 32, 0.5)", {"r": 128, "g": 64, "b": 32, "a": 0.5}),
            ("rgb(255, 255, 255)", {"r": 255, "g": 255, "b": 255, "a": 1.0}),
        ]

        for value, expected in test_cases:
            result_type, result_value = convert_style(value)
            assert result_type == "color"
            assert result_value["type"] == "rgba"
            for key, expected_val in expected.items():
                assert result_value[key] == expected_val

    def test_convert_style_hsla_colors(self):
        """Test hsla color parsing (P8 enhancement)."""
        test_cases = [
            ("hsla(240, 100%, 50%, 1)", {"h": 240, "s": 100, "l": 50, "a": 1.0}),
            ("hsla(120, 60%, 70%, 0.8)", {"h": 120, "s": 60, "l": 70, "a": 0.8}),
            ("hsl(0, 100%, 50%)", {"h": 0, "s": 100, "l": 50, "a": 1.0}),
        ]

        for value, expected in test_cases:
            result_type, result_value = convert_style(value)
            assert result_type == "color"
            assert result_value["type"] == "hsla"
            for key, expected_val in expected.items():
                assert result_value[key] == expected_val

    def test_convert_style_gradients(self):
        """Test CSS gradient parsing (P8 enhancement)."""
        test_cases = [
            "linear-gradient(45deg, red, blue)",
            "radial-gradient(circle, white, black)",
            "conic-gradient(from 0deg, red, yellow, green, red)",
        ]

        for gradient in test_cases:
            result_type, result_value = convert_style(gradient)
            assert result_type == "gradient"
            assert "value" in result_value
            assert gradient in result_value["value"]
            assert "definition" in result_value

    def test_convert_style_complex_borders(self):
        """Test complex border parsing (P8 enhancement)."""
        test_cases = [
            {
                "value": "2px solid #FF0000",
                "expected": {
                    "width": "2px",
                    "style": "solid",
                    "color": {"type": "hex", "value": "#FF0000"},
                },
            },
            {
                "value": "1pt dashed blue",
                "expected": {
                    "width": "1pt",
                    "style": "dashed",
                    "color": {"type": "named", "value": "blue"},
                },
            },
            {
                "value": "3px dotted rgba(255,0,0,0.5)",
                "expected": {
                    "width": "3px",
                    "style": "dotted",
                    "color": {"type": "rgba"},  # Just check type, rgba details tested elsewhere
                },
            },
        ]

        for test_case in test_cases:
            result_type, result_value = convert_style(test_case["value"])
            assert result_type == "border"

            expected = test_case["expected"]
            assert result_value["width"] == expected["width"]
            assert result_value["style"] == expected["style"]
            assert result_value["color"]["type"] == expected["color"]["type"]

    def test_convert_style_shadows(self):
        """Test box shadow parsing (P8 enhancement)."""
        shadow_values = [
            "0 2px 4px rgba(0,0,0,0.1)",
            "2px 4px 8px #333333",
            "inset 0 1px 2px rgba(0,0,0,0.2)",
        ]

        for shadow in shadow_values:
            # Direct shadow parsing
            result_type, result_value = convert_style(shadow)
            assert result_type == "shadow"
            assert result_value["type"] == "css"
            assert shadow in result_value["value"]

    def test_convert_style_transforms(self):
        """Test CSS transform parsing (P8 enhancement)."""
        transforms = [
            "translateX(50px)",
            "rotate(45deg)",
            "scale(1.5)",
            "matrix(1, 0, 0, 1, 50, 50)",
        ]

        for transform in transforms:
            result_type, result_value = convert_style(transform)
            assert result_type == "transform"
            assert result_value["type"] == "css"
            assert transform in result_value["value"]

    def test_convert_style_animations(self):
        """Test CSS animation/transition parsing (P8 enhancement)."""
        animations = [
            "transition: all 0.3s ease",
            "animation: fadeIn 1s ease-out",
        ]

        for animation in animations:
            result_type, result_value = convert_style(animation)
            assert result_type == "animation"
            assert result_value["type"] == "css"
            assert animation in result_value["value"]

    def test_convert_style_invalid_hex_colors(self):
        """Test handling of invalid hex colors."""
        invalid_hex_values = [
            "#12345G",  # Invalid character
            "#1234",  # Invalid length
            "##123456",  # Double hash
        ]

        for invalid_hex in invalid_hex_values:
            result_type, result_value = convert_style(invalid_hex)
            assert result_type == "color"
            assert result_value["type"] == "hex"
            assert result_value["value"] == invalid_hex  # Preserved as-is

    def test_convert_style_malformed_functions(self):
        """Test handling of malformed CSS functions."""
        malformed_values = [
            "rgba(255, 0, 0)",  # Missing alpha
            "rgba(255, 0, 0, 1, 0)",  # Too many values
            "hsla(360, 50%)",  # Missing values
            "linear-gradient()",  # Empty gradient
        ]

        for malformed in malformed_values:
            # Should not crash, should handle gracefully
            result_type, result_value = convert_style(malformed)
            # Exact behavior may vary, but should not raise exception
            assert result_type is not None
            assert result_value is not None

    # ========================================================================
    # Helper Function Tests
    # ========================================================================

    def test_get_theme_colors(self):
        """Test theme color retrieval."""
        colors = get_theme_colors()

        # Check expected theme colors
        expected_colors = [
            "TEXT1",
            "TEXT2",
            "BACKGROUND1",
            "BACKGROUND2",
            "ACCENT1",
            "ACCENT2",
            "ACCENT3",
            "ACCENT4",
            "ACCENT5",
            "ACCENT6",
            "HYPERLINK",
            "FOLLOWED_HYPERLINK",
            "DARK1",
            "LIGHT1",
        ]

        for color in expected_colors:
            assert color in colors

        # Should be a set
        assert isinstance(colors, set)

    def test_get_color_names(self):
        """Test extended color name retrieval (P8 enhancement)."""
        colors = get_color_names()

        # Check basic colors
        basic_colors = ["red", "green", "blue", "black", "white"]
        for color in basic_colors:
            assert color in colors

        # Check extended colors (P8)
        extended_colors = ["darkred", "lightblue", "crimson", "turquoise", "khaki"]
        for color in extended_colors:
            assert color in colors

        # Should be a set
        assert isinstance(colors, set)

        # Should have more colors than basic set
        assert len(colors) > 20

    # ========================================================================
    # Integration and Edge Case Tests
    # ========================================================================

    def test_style_conversion_integration(self):
        """Test integration of multiple style conversion features."""
        complex_styles = [
            {
                "input": "2pt solid rgba(128, 64, 32, 0.75)",
                "expected_type": "border",
                "checks": [
                    lambda v: v["width"] == "2pt",
                    lambda v: v["style"] == "solid",
                    lambda v: v["color"]["type"] == "rgba",
                    lambda v: v["color"]["r"] == 128,
                ],
            },
            {
                "input": "linear-gradient(180deg, hsla(240,100%,50%,1), rgba(255,0,0,0.5))",
                "expected_type": "gradient",
                "checks": [
                    lambda v: "linear-gradient" in v["value"],
                    lambda v: "hsla(240,100%,50%,1)" in v["definition"],
                    lambda v: "rgba(255,0,0,0.5)" in v["definition"],
                ],
            },
        ]

        for test_case in complex_styles:
            result_type, result_value = convert_style(test_case["input"])
            assert result_type == test_case["expected_type"]

            for check in test_case["checks"]:
                assert check(result_value), f"Check failed for {test_case['input']}"

    def test_dimension_edge_cases(self):
        """Test dimension conversion edge cases."""
        edge_cases = [
            ("0/1", 0.0),  # Zero numerator
            ("1/1", 1.0),  # Equal numerator/denominator
            ("0%", 0.0),  # Zero percentage
            ("0", 0),  # Zero value
            ("0.0", 0.0),  # Zero float
            ("1000000", 1000000),  # Large number
        ]

        for value, expected in edge_cases:
            result = convert_dimension(value)
            assert result == expected

    def test_alignment_case_sensitivity(self):
        """Test alignment conversion case handling."""
        test_cases = [
            ("LEFT", "left"),
            ("Center", "center"),
            ("RIGHT", "right"),
            ("FLEX-START", "left"),
            ("Justified", "justify"),
        ]

        for input_val, expected in test_cases:
            result = convert_alignment(input_val)
            assert result == expected

    def test_converter_error_recovery(self):
        """Test that converters handle errors gracefully."""
        import contextlib

        # Dimension converter with extreme values
        with contextlib.suppress(ValueError, OverflowError):
            convert_dimension("1e100/1e-100")  # May cause overflow

        # Style converter with very long inputs
        very_long_input = "a" * 10000
        result_type, result_value = convert_style(very_long_input)
        assert result_type == "value"
        assert result_value == very_long_input

        # Alignment with unicode characters
        unicode_alignment = "左"  # Left in Chinese
        result = convert_alignment(unicode_alignment)
        assert result == unicode_alignment  # Should pass through
