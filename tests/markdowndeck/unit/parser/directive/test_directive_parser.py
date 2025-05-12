import pytest
from markdowndeck.models.slide import Section
from markdowndeck.parser.directive.directive_parser import DirectiveParser


class TestDirectiveParser:
    """Unit tests for the DirectiveParser component."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        return DirectiveParser()

    def test_parse_no_directives(self, parser: DirectiveParser):
        section = Section(content="Simple content.", id="s1")
        parser.parse_directives(section)
        assert section.directives == {}
        assert section.content == "Simple content."

    def test_parse_single_valid_directive(self, parser: DirectiveParser):
        section = Section(
            content="[width=1/2]\nRemaining content",
            id="s2",
        )
        parser.parse_directives(section)
        assert section.directives == {"width": 0.5}
        assert section.content == "Remaining content"

    def test_parse_multiple_directives_same_line(self, parser: DirectiveParser):
        section = Section(
            content="[width=2/3][align=center][background=#123456]\nContent",
            id="s3",
        )
        parser.parse_directives(section)
        assert section.directives == {
            "width": 2 / 3,
            "align": "center",
            "background": ("color", "#123456"),
        }
        assert section.content == "Content"

    def test_parse_directives_with_whitespace_around(self, parser: DirectiveParser):
        section = Section(
            content="  [ width = 75% ]  [ height = 300 ] \n  Content  ",
            id="s4",
        )
        parser.parse_directives(section)
        assert section.directives == {"width": 0.75, "height": 300}
        assert section.content == "Content  "

    def test_directives_not_at_start_are_ignored(self, parser: DirectiveParser):
        original_content = "Some text\n[width=1/2]\nMore text"
        section = Section(content=original_content, id="s5")
        parser.parse_directives(section)
        assert section.directives == {}
        assert section.content == original_content

    def test_malformed_directives(self, parser: DirectiveParser):
        """Test that malformed directives are handled gracefully (usually ignored or partially parsed)."""
        section1 = Section(
            content="[width:50%] Content",
            id="s6_1",
        )  # Invalid key-value separator
        parser.parse_directives(section1)
        assert not section1.directives
        assert section1.content == "Content"

        section2 = Section(
            content="[align=] Content",
            id="s6_2",
        )  # Empty value
        parser.parse_directives(section2)
        assert section2.directives.get("align") == ""
        assert section2.content == "Content"

        section3 = Section(
            content="[=center] Content",
            id="s6_3",
        )  # Empty key
        parser.parse_directives(section3)
        assert not section3.directives
        assert section3.content == "Content"

        section4 = Section(
            content="[unclosed Content",
            id="s6_4",
        )  # Unclosed bracket
        parser.parse_directives(section4)
        assert not section4.directives
        assert section4.content == "[unclosed Content"

    def test_unknown_directive_key(self, parser: DirectiveParser):
        """Test that unknown directive keys are stored as is (string value)."""
        section = Section(
            content="[customKey=customValue][width=100]\nContent",
            id="s7",
        )
        parser.parse_directives(section)
        assert "customkey" in section.directives
        assert section.directives["customkey"] == "customValue"
        assert section.directives["width"] == 100
        assert section.content == "Content"

    def test_directive_value_conversion_errors_handled(self, parser: DirectiveParser, caplog):
        """Test that errors during value conversion are logged and directive might be skipped."""
        section = Section(
            content="[width=abc][height=1/0]\nContent",
            id="s8",
        )
        parser.parse_directives(section)

        assert "width" not in section.directives
        assert "height" not in section.directives
        assert section.content == "Content"
        assert "Error processing directive width=abc" in caplog.text
        assert "Error processing directive height=1/0" in caplog.text

    def test_empty_section_content(self, parser: DirectiveParser):
        section = Section(content="", id="s9")
        parser.parse_directives(section)
        assert section.directives == {}
        assert section.content == ""

    def test_directives_only_no_content(self, parser: DirectiveParser):
        section = Section(
            content="[width=100%][align=right]",
            id="s10",
        )
        parser.parse_directives(section)
        assert section.directives == {"width": 1.0, "align": "right"}
        assert section.content == ""

    def test_directive_key_case_insensitivity(self, parser: DirectiveParser):
        section = Section(
            content="[WIDTH=200][Align=Left]\nContent",
            id="s11",
        )
        parser.parse_directives(section)
        assert "width" in section.directives
        assert section.directives["width"] == 200
        assert "align" in section.directives
        assert section.directives["align"] == "left"
        assert section.content == "Content"

    def test_float_conversion(self, parser: DirectiveParser):
        """Test float conversion for directives like opacity."""
        section = Section(content="[opacity=0.75]\nContent", id="s12")
        parser.parse_directives(section)
        assert "opacity" in section.directives
        assert section.directives["opacity"] == pytest.approx(0.75)
        assert section.content == "Content"

        section_invalid = Section(
            content="[opacity=abc]\nContent",
            id="s13",
        )
        parser.parse_directives(section_invalid)
        assert "opacity" not in section_invalid.directives
