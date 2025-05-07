import pytest
from markdowndeck.parser.directive_parser import DirectiveParser


class TestDirectiveParser:
    """Tests for the DirectiveParser component."""

    @pytest.fixture
    def parser(self):
        """Create a directive parser for testing."""
        return DirectiveParser()

    def test_parse_single_directive(self, parser):
        """Test parsing a single valid directive."""
        section = {
            "content": "[width=1/2]\nRemaining content",
            "directives": {},
            "id": "sec-1",
        }
        parser.parse_directives(section)

        assert "width" in section["directives"]
        assert section["directives"]["width"] == 0.5
        assert section["content"] == "Remaining content"

    def test_parse_multiple_directives(self, parser):
        """Test parsing multiple valid directives on the same line."""
        section = {
            "content": "[width=2/3][align=center][background=#ffffff]\nContent below",
            "directives": {},
            "id": "sec-2",
        }
        parser.parse_directives(section)

        assert "width" in section["directives"]
        assert section["directives"]["width"] == 2 / 3
        assert "align" in section["directives"]
        assert section["directives"]["align"] == "center"
        assert "background" in section["directives"]
        # _convert_style returns a tuple
        assert section["directives"]["background"] == ("color", "#ffffff")
        assert section["content"] == "Content below"

    def test_parse_directives_with_whitespace(self, parser):
        """Test parsing directives with extra whitespace."""
        section = {
            "content": "  [ width = 3/4 ]  [ valign = middle ] \n  Actual content",
            "directives": {},
            "id": "sec-3",
        }
        parser.parse_directives(section)

        assert "width" in section["directives"]
        assert section["directives"]["width"] == 0.75
        assert "valign" in section["directives"]
        assert section["directives"]["valign"] == "middle"
        assert section["content"] == "Actual content"

    def test_no_directives(self, parser):
        """Test parsing content with no directives."""
        original_content = "This content has no directives."
        section = {"content": original_content, "directives": {}, "id": "sec-4"}
        parser.parse_directives(section)

        assert section["directives"] == {}
        assert section["content"] == original_content

    def test_directives_not_at_start(self, parser):
        """Test that directives are only parsed if they are at the start."""
        original_content = "Some text\n[width=1/2]\nMore text"
        section = {"content": original_content, "directives": {}, "id": "sec-5"}
        parser.parse_directives(section)

        assert section["directives"] == {}  # No directives should be parsed
        assert section["content"] == original_content

    def test_parse_unknown_directive(self, parser):
        """Test parsing an unknown directive (should be stored as-is)."""
        section = {
            "content": "[custom=value][width=100%]\nContent",
            "directives": {},
            "id": "sec-6",
        }
        parser.parse_directives(section)

        assert "custom" in section["directives"]
        assert section["directives"]["custom"] == "value"  # Stored as string
        assert "width" in section["directives"]
        assert section["directives"]["width"] == 1.0
        assert section["content"] == "Content"

    # --- Test Converters Directly ---

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1/2", 0.5),
            ("3/4", 0.75),
            ("1/1", 1.0),
            ("75%", 0.75),
            ("100%", 1.0),
            ("50.5%", 0.505),
            ("300", 300),  # Handles pixel values as integers
            ("150.5", 150.5),  # Handles float values
        ],
    )
    def test_convert_dimension_valid(self, parser, value, expected):
        """Test valid dimension conversions."""
        assert parser._convert_dimension(value) == expected

    def test_convert_dimension_invalid(self, parser):
        """Test invalid dimension conversions."""
        with pytest.raises(ValueError):
            parser._convert_dimension("abc")
        with pytest.raises(ValueError):
            parser._convert_dimension("1/0")  # Zero division
        with pytest.raises(ValueError):
            parser._convert_dimension("50 %")  # Space not allowed

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("center", "center"),
            ("RIGHT", "right"),  # Case-insensitive
            ("justify", "justify"),
            ("top", "top"),
            ("MIDDLE", "middle"),
            ("bottom", "bottom"),
            ("start", "left"),  # Alias
            ("end", "right"),  # Alias
            ("unknown", "unknown"),  # Pass through unknown
        ],
    )
    def test_convert_alignment_valid(self, parser, value, expected):
        """Test valid alignment conversions."""
        assert parser._convert_alignment(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected_type", "expected_value"),
        [
            ("#ff0000", "color", "#ff0000"),
            ("white", "color", "white"),
            ("transparent", "color", "transparent"),
            ("url(http://example.com/img.png)", "url", "http://example.com/img.png"),
            (
                "url('http://example.com/img.png')",
                "url",
                "http://example.com/img.png",
            ),  # With quotes
            ("other_value", "value", "other_value"),
        ],
    )
    def test_convert_style_valid(self, parser, value, expected_type, expected_value):
        """Test valid style conversions."""
        assert parser._convert_style(value) == (expected_type, expected_value)
