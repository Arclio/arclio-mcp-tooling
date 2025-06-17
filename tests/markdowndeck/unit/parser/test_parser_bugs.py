import pytest
from markdowndeck.models import ListElement
from markdowndeck.parser import Parser
from markdowndeck.parser.errors import GrammarError


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestParserBugReproduction:
    """Tests designed to fail, exposing known bugs in the Parser and its formatters."""

    def test_bug_list_item_directive_not_parsed(self, parser: Parser):
        """Test Case: PARSER-BUG-01"""
        markdown = ":::section\n- List Item [color=red]\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        content_section = slide.root_section.children[0]
        list_element = next(
            (c for c in content_section.children if isinstance(c, ListElement)), None
        )
        assert list_element is not None
        item = list_element.items[0]
        assert item.text == "List Item"
        assert item.directives.get("color") is not None

    def test_feature_indented_fenced_blocks_is_now_illegal(self, parser: Parser):
        """
        Test Case: PARSER-FEATURE-01
        REFACTORED: The markdown is now correctly identified as grammatically illegal
        because a :::section cannot be inside another :::section.
        """
        markdown = """
    :::section [padding=10]
      :::section
        Content in an indented section.
      :::
      :::row
        :::column
            :::section
            Indented column.
            :::
        :::
      :::
    :::
"""
        with pytest.raises(
            GrammarError,
            match="A ':::section' block cannot be a child of a ':::section' block",
        ):
            parser.section_parser.parse_sections(markdown)
