import pytest
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestFencedBlockParser:
    def test_fenced_block_section_creation(self, parser: Parser):
        """Validates that :::section creates a Section object with correct directives and content."""
        markdown = ":::section [padding=20]\nContent\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        root_section = slide.root_section
        assert len(root_section.children) == 1, "Root should have one child section"
        nested_section = root_section.children[0]
        assert nested_section.type == "section"
        assert nested_section.directives.get("padding") == 20.0
        assert (
            nested_section.children[0].text == "Content"
        ), "Content was not correctly placed in section"

    def test_fenced_block_row_and_column_creation(self, parser: Parser):
        """Validates that :::row and :::column create the correct nested hierarchy."""
        markdown = ":::row [gap=30]\n:::column [width=40%]\nLeft\n:::\n:::column\nRight\n:::\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        row = slide.root_section.children[0]
        assert row.type == "row"
        assert row.directives.get("gap") == 30.0
        assert len(row.children) == 2, "Row should have two columns"
        col1, col2 = row.children
        assert col1.type == "section"
        assert col1.directives.get("width") == 0.4
        assert col1.children[0].text == "Left"
        assert col2.children[0].text == "Right"

    def test_deeply_nested_fenced_blocks(self, parser: Parser):
        """Validates correct parsing of deeply nested fenced blocks."""
        markdown = ":::section\nL1\n:::row\n:::column\nL2 C1\n:::\n:::column\nL2 C2\n:::section\nL3\n:::\n:::\n:::\n:::"
        deck = parser.parse(markdown)
        l1_section = deck.slides[0].root_section.children[0]
        assert l1_section.children[0].text == "L1"
        l2_row = l1_section.children[1]
        assert l2_row.type == "row"
        assert len(l2_row.children) == 2
        l2_col2 = l2_row.children[1]
        assert l2_col2.children[0].text == "L2 C2"
        l3_section = l2_col2.children[1]
        assert l3_section.type == "section"
        assert l3_section.children[0].text == "L3"

    def test_unclosed_fenced_block(self, parser: Parser, caplog):
        """Validates that unclosed blocks are handled gracefully with a warning."""
        markdown = ":::section\nSome content"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert len(slide.root_section.children) == 1
        section = slide.root_section.children[0]
        assert section.children[0].text == "Some content"
        assert "Found 1 unclosed section(s). Auto-closing." in caplog.text

    def test_column_outside_row_is_just_a_section(self, parser: Parser):
        """Validates that a :::column outside a :::row is treated as a regular section."""
        markdown = ":::column\nContent\n:::"
        deck = parser.parse(markdown)
        section = deck.slides[0].root_section.children[0]
        assert section.type == "section"
        assert section.directives.get("_is_column") is True
        assert section.children[0].text == "Content"

    def test_fenced_block_with_mixed_content_and_nesting(self, parser: Parser):
        """Tests a section that contains both its own text content and a nested section."""
        markdown = ":::section\nOuter Content\n:::section\nInner Content\n:::\n:::"
        deck = parser.parse(markdown)
        outer_section = deck.slides[0].root_section.children[0]
        assert (
            len(outer_section.children) == 2
        ), "Outer section should have two children: a TextElement and a Section"
        assert outer_section.children[0].text == "Outer Content"
        assert outer_section.children[1].type == "section"
        inner_section = outer_section.children[1]
        assert inner_section.children[0].text == "Inner Content"
