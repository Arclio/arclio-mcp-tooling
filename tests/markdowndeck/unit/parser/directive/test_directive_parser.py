"""Updated unit tests for the DirectiveParser with enhanced CSS support."""

import pytest
from markdowndeck.models.slide import Section
from markdowndeck.parser.directive.directive_parser import DirectiveParser


class TestDirectiveParser:
    """Updated unit tests for the DirectiveParser component."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        return DirectiveParser()

    # ========================================================================
    # Basic Directive Parsing Tests (Updated)
    # ========================================================================

    def test_parse_no_directives(self, parser: DirectiveParser):
        """Test parsing content with no directives."""
        section = Section(content="Simple content.", id="s1")
        parser.parse_directives(section)
        assert section.directives == {}
        assert section.content == "Simple content."

    def test_parse_single_valid_directive(self, parser: DirectiveParser):
        """Test parsing a single valid directive."""
        section = Section(content="[width=1/2]\nRemaining content", id="s2")
        parser.parse_directives(section)
        assert section.directives == {"width": 0.5}
        assert section.content == "Remaining content"

    def test_parse_multiple_directives_same_line(self, parser: DirectiveParser):
        """Test parsing multiple directives on the same line."""
        section = Section(
            content="[width=2/3][align=center][background=#123456]\nContent",
            id="s3",
        )
        parser.parse_directives(section)
        expected_directives = {
            "width": 2 / 3,
            "align": "center",
            "background": {"type": "hex", "value": "#123456"},
        }
        assert section.directives == expected_directives
        assert section.content == "Content"

    def test_parse_directives_with_whitespace(self, parser: DirectiveParser):
        """Test parsing directives with various whitespace patterns."""
        section = Section(
            content="  [ width = 75% ]  [ height = 300 ] \n  Content  ",
            id="s4",
        )
        parser.parse_directives(section)
        assert section.directives == {"width": 0.75, "height": 300}
        assert section.content == "Content  "

    def test_directives_not_at_start_ignored(self, parser: DirectiveParser):
        """Test that directives not at the start are ignored."""
        original_content = "Some text\n[width=1/2]\nMore text"
        section = Section(content=original_content, id="s5")
        parser.parse_directives(section)
        assert section.directives == {}
        assert section.content == original_content

    # ========================================================================
    # Enhanced CSS Value Parsing Tests (P8)
    # ========================================================================

    def test_rgba_color_parsing(self, parser: DirectiveParser):
        """Test rgba color parsing."""
        section = Section(content="[background=rgba(255, 128, 0, 0.75)]\nContent", id="rgba_test")
        parser.parse_directives(section)

        bg = section.directives["background"]
        assert bg["type"] == "rgba"
        assert bg["r"] == 255
        assert bg["g"] == 128
        assert bg["b"] == 0
        assert bg["a"] == 0.75
        assert section.content == "Content"

    def test_hsla_color_parsing(self, parser: DirectiveParser):
        """Test hsla color parsing."""
        section = Section(content="[color=hsla(240, 100%, 50%, 0.8)]\nContent", id="hsla_test")
        parser.parse_directives(section)

        color = section.directives["color"]
        assert color["type"] == "hsla"
        assert color["h"] == 240
        assert color["s"] == 100
        assert color["l"] == 50
        assert color["a"] == 0.8

    def test_linear_gradient_parsing(self, parser: DirectiveParser):
        """Test linear gradient parsing."""
        section = Section(
            content="[background=linear-gradient(45deg, red, blue)]\nContent",
            id="gradient_test",
        )
        parser.parse_directives(section)

        bg = section.directives["background"]
        assert "gradient" in bg["type"] or bg["type"] == "linear"
        assert "45deg, red, blue" in bg["definition"]
        assert "linear-gradient" in bg["value"]

    def test_css_dimensions_with_units(self, parser: DirectiveParser):
        """Test CSS dimensions with various units."""
        section = Section(
            content="[padding=1.5em][margin=10px][width=50%][height=100vh]\nContent",
            id="units_test",
        )
        parser.parse_directives(section)

        assert section.directives["padding"] == 1.5  # em unit processed
        assert section.directives["margin"] == 10  # px unit processed
        assert section.directives["width"] == 0.5  # % converted to decimal
        assert section.directives["height"] == 100  # vh unit processed

    def test_complex_border_parsing(self, parser: DirectiveParser):
        """Test complex border value parsing."""
        section = Section(
            content="[border=2pt solid rgba(128, 64, 32, 0.9)]\nContent",
            id="border_test",
        )
        parser.parse_directives(section)

        border = section.directives["border"]
        assert border["width"] == "2pt"
        assert border["style"] == "solid"
        assert border["color"]["type"] == "rgba"
        assert border["color"]["r"] == 128
        assert border["color"]["g"] == 64
        assert border["color"]["b"] == 32
        assert border["color"]["a"] == 0.9

    def test_box_shadow_parsing(self, parser: DirectiveParser):
        """Test box shadow parsing."""
        section = Section(
            content="[box-shadow=2px 4px 8px rgba(0,0,0,0.3)]\nContent",
            id="shadow_test",
        )
        parser.parse_directives(section)

        shadow = section.directives["box-shadow"]
        assert shadow["type"] == "css"
        assert "2px 4px 8px rgba(0,0,0,0.3)" in shadow["value"]

    def test_multiple_css_values(self, parser: DirectiveParser):
        """Test multiple advanced CSS values together."""
        section = Section(
            content="""[background=linear-gradient(180deg, rgba(255,0,0,1), rgba(0,0,255,0.5))]
[border=1px dashed hsla(120, 50%, 60%, 0.8)]
[box-shadow=0 2px 4px rgba(0,0,0,0.1)]
Content""",
            id="multi_css_test",
        )
        parser.parse_directives(section)

        # Check background gradient
        bg = section.directives["background"]
        assert "gradient" in bg["type"] or bg["type"] == "linear"

        # Check border with hsla color
        border = section.directives["border"]
        assert border["color"]["type"] == "hsla"

        # Check box shadow
        shadow = section.directives["box-shadow"]
        assert shadow["type"] == "css"

    # ========================================================================
    # Inline Directive Parsing Tests
    # ========================================================================

    def test_parse_inline_directives_directive_only(self, parser: DirectiveParser):
        """Test parsing inline directives from directive-only lines."""
        directives, remaining = parser.parse_inline_directives("[align=center][color=red]")

        expected = {"align": "center", "color": {"type": "named", "value": "red"}}
        assert directives == expected
        assert remaining == ""

    def test_parse_inline_directives_mixed_content(self, parser: DirectiveParser):
        """Test that mixed directive/content lines are not parsed as pure directives."""
        directives, remaining = parser.parse_inline_directives("[color=blue] Some text")

        # Should not parse as pure directives since there's text content
        assert directives == {}
        assert remaining == "[color=blue] Some text"

    def test_parse_inline_directives_empty_line(self, parser: DirectiveParser):
        """Test parsing empty or whitespace lines."""
        directives, remaining = parser.parse_inline_directives("   ")
        assert directives == {}
        assert remaining == ""

    def test_parse_inline_directives_with_enhanced_css(self, parser: DirectiveParser):
        """Test inline directive parsing with enhanced CSS values."""
        directives, remaining = parser.parse_inline_directives("[background=rgba(255,0,0,0.5)][border=2px solid blue]")

        assert remaining == ""

        # Check rgba background
        bg = directives["background"]
        assert bg["type"] == "rgba"
        assert bg["r"] == 255

        # Check border
        border = directives["border"]
        assert border["width"] == "2px"
        assert border["style"] == "solid"

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    def test_malformed_directives_handled(self, parser: DirectiveParser):
        """Test handling of malformed directives."""
        section = Section(content="[width:50%] Content", id="malformed")  # Invalid separator
        parser.parse_directives(section)

        # Should clean up malformed directive and process content
        assert not section.directives  # No valid directives parsed
        assert section.content == "Content"

    def test_directive_value_conversion_errors(self, parser: DirectiveParser, caplog):
        """Test handling of directive value conversion errors."""
        section = Section(content="[width=invalid][height=1/0]\nContent", id="errors")
        parser.parse_directives(section)

        # Should handle errors gracefully
        assert "width" not in section.directives or section.directives["width"] == "invalid"
        assert "height" not in section.directives or section.directives["height"] == "1/0"
        assert section.content == "Content"

        # Check that errors were logged
        assert "Error processing directive" in caplog.text

    def test_unknown_directive_keys(self, parser: DirectiveParser):
        """Test handling of unknown directive keys."""
        section = Section(
            content="[custom-property=value][unknown=test][width=100]\nContent",
            id="unknown",
        )
        parser.parse_directives(section)

        # Unknown directives should be stored as strings
        assert section.directives["custom-property"] == "value"
        assert section.directives["unknown"] == "test"
        assert section.directives["width"] == 100  # Known directive processed normally

    def test_empty_directive_values(self, parser: DirectiveParser):
        """Test handling of empty directive values."""
        section = Section(content="[align=][color=red]\nContent", id="empty_val")
        parser.parse_directives(section)

        assert section.directives["align"] == ""  # Empty value preserved
        assert section.directives["color"]["value"] == "red"  # Normal value processed

    def test_directive_key_case_insensitivity(self, parser: DirectiveParser):
        """Test that directive keys are case-insensitive."""
        section = Section(
            content="[WIDTH=200][Align=Center][BACKGROUND=#FF0000]\nContent",
            id="case_test",
        )
        parser.parse_directives(section)

        assert "width" in section.directives
        assert section.directives["width"] == 200
        assert "align" in section.directives
        assert section.directives["align"] == "center"
        assert "background" in section.directives

    def test_directive_only_content(self, parser: DirectiveParser):
        """Test content that contains only directives."""
        section = Section(content="[width=100%][height=50%][align=center]", id="directives_only")
        parser.parse_directives(section)

        assert section.directives["width"] == 1.0
        assert section.directives["height"] == 0.5
        assert section.directives["align"] == "center"
        assert section.content == ""

    def test_complex_nested_values(self, parser: DirectiveParser):
        """Test complex nested CSS values."""
        section = Section(
            content="[transform=translateX(50px) rotate(45deg)][transition=all 0.3s ease-in-out]\nContent",
            id="complex",
        )
        parser.parse_directives(section)

        # Transform should be parsed as CSS transform
        transform = section.directives["transform"]
        assert transform["type"] == "css"
        assert "translateX(50px) rotate(45deg)" in transform["value"]

        # Transition should be parsed as CSS animation
        transition = section.directives["transition"]
        assert transition["type"] == "css"
        assert "all 0.3s ease-in-out" in transition["value"]

    def test_float_directive_with_safe_conversion(self, parser: DirectiveParser):
        """Test float directive conversion with error handling."""
        section = Section(
            content="[opacity=0.75][line-spacing=invalid_float]\nContent",
            id="float_test",
        )
        parser.parse_directives(section)

        assert section.directives["opacity"] == 0.75
        # Invalid float should default to 0.0 with safe conversion
        assert section.directives["line-spacing"] == 0.0

    def test_directive_removal_verification(self, parser: DirectiveParser):
        """Test that directive removal is properly verified."""
        # Content with potential residual directive patterns
        section = Section(
            content="[width=100%] [height=50%]\n[color=red] Some content with [brackets]",
            id="removal_test",
        )
        parser.parse_directives(section)

        # All directives in the contiguous block should be parsed
        assert "width" in section.directives
        assert "height" in section.directives
        assert "color" in section.directives  # Part of contiguous directive block
        assert section.directives["color"] == {"type": "named", "value": "red"}

        # Content should have all directives removed, leaving only the text
        assert section.content == "Some content with [brackets]"

    def test_enhanced_css_alias_support(self, parser: DirectiveParser):
        """Test enhanced CSS property aliases."""
        section = Section(
            content="[font-size=16][border-radius=5px][margin-top=10px]\nContent",
            id="alias_test",
        )
        parser.parse_directives(section)

        # Should recognize CSS aliases
        assert "font-size" in section.directives
        assert section.directives["font-size"] == 16
        assert "border-radius" in section.directives
        assert section.directives["border-radius"] == 5
        assert "margin-top" in section.directives
        assert section.directives["margin-top"] == 10
