import pytest
from markdowndeck.parser import Parser
from markdowndeck.parser.errors import GrammarError


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestFencedBlockParser:
    def test_fenced_block_section_creation(self, parser: Parser):
        """Validates that :::section creates a Section object with correct directives and content."""
        markdown = ":::section [padding=20]\nContent\n:::"
        deck = parser.parse(markdown)
        nested_section = deck.slides[0].root_section.children[0]
        assert nested_section.type == "section"
        assert nested_section.children[0].text == "Content"

    def test_fenced_block_row_and_column_creation(self, parser: Parser):
        """Validates that :::row and :::column create the correct nested hierarchy."""
        markdown = ":::row [gap=30]\n:::column [width=40%]\n:::section\nLeft\n:::\n:::\n:::column\n:::section\nRight\n:::\n:::\n:::"
        deck = parser.parse(markdown)
        row = deck.slides[0].root_section.children[0]
        assert row.type == "row"
        col1, _ = row.children
        assert col1.type == "column"
        assert col1.children[0].children[0].text == "Left"

    def test_deeply_nested_fenced_blocks(self, parser: Parser):
        """
        Validates correct parsing of deeply nested fenced blocks.
        """
        markdown = ":::row\n:::column\n:::section\nL2 C1\n:::\n:::\n:::column\n:::section\nL2 C2\n:::\n:::\n:::"
        root = parser.section_parser.parse_sections(markdown)
        assert root is not None
        l2_row = root.children[0]
        assert l2_row.type == "row"
        l2_col2 = l2_row.children[1]
        assert l2_col2.children[0].children[0] == "L2 C2"

    def test_unclosed_fenced_block_raises_error(self, parser: Parser):
        """Validates that unclosed blocks raise a GrammarError."""
        markdown = ":::section\nSome content"
        with pytest.raises(GrammarError, match="Found 1 unclosed section"):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_column_outside_row(self, parser: Parser):
        """Validates that a :::column outside a :::row raises a GrammarError."""
        markdown = ":::column\n:::section\nContent\n:::\n:::"
        with pytest.raises(
            GrammarError,
            match="A ':::column' block can only be a direct child of a ':::row' block",
        ):
            parser.section_parser.parse_sections(markdown)

    def test_fenced_block_with_mixed_content_and_nesting(self, parser: Parser):
        """Tests that a section with both content and nested sections raises an error."""
        markdown = ":::section\nOuter Content\n:::section\nInner Content\n:::\n:::"
        with pytest.raises(
            GrammarError,
            match="A ':::section' block cannot be a child of a ':::section' block",
        ):
            parser.section_parser.parse_sections(markdown)
