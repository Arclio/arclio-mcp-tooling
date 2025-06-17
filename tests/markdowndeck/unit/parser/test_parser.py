import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser
from markdowndeck.parser.errors import GrammarError


class TestParser:
    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    def test_parser_parses_all_content_blocks(self, parser: Parser):
        """Test Case: PARSER-C-11 (Custom ID)"""
        # REFACTORED: Added blank lines between blocks. This is the correct
        # CommonMark syntax to create separate blocks, which markdown-it will
        # now correctly tokenize.
        markdown = """
:::section
# First Block (H1)

This is the second block (paragraph).

- This is the third block (list).
:::
"""
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        parsed_elements = slide.root_section.children[0].children
        assert (
            len(parsed_elements) == 3
        ), "Parser should have created 3 distinct elements."
        element_types = [el.element_type for el in parsed_elements]
        assert ElementType.TEXT in element_types
        assert ElementType.BULLET_LIST in element_types

    def test_fenced_block_section_creation(self, parser: Parser):
        """Test Case: PARSER-C-04"""
        markdown = ":::section [padding=20]\nContent\n:::"
        deck = parser.parse(markdown)
        nested_section = deck.slides[0].root_section.children[0]
        assert nested_section.type == "section"
        assert nested_section.children[0].text == "Content"

    def test_fenced_block_row_and_column_creation(self, parser: Parser):
        """Test Case: PARSER-C-05"""
        markdown = ":::row [gap=30]\n:::column [width=40%]\n:::section\nLeft\n:::\n:::\n:::column\n:::section\nRight\n:::\n:::\n:::"
        deck = parser.parse(markdown)
        row = deck.slides[0].root_section.children[0]
        assert row.type == "row"
        col1, _ = row.children
        assert col1.type == "column"
        assert col1.children[0].children[0].text == "Left"

    def test_fenced_block_nesting(self, parser: Parser):
        """Test Case: PARSER-C-06"""
        markdown = ":::row\n:::column\n:::section\nOuter\n:::\n:::section\nInner\n:::\n:::\n:::"
        deck = parser.parse(markdown)
        column = deck.slides[0].root_section.children[0].children[0]
        assert len(column.children) == 2
        assert column.children[0].children[0].text == "Outer"
        assert column.children[1].type == "section"

    def test_deprecated_separators_are_ignored_for_layout(self, parser: Parser):
        """Test Case: PARSER-E-03"""
        markdown = ":::section\nTop\n---\nBottom\n***\nRight\n:::"
        deck = parser.parse(markdown)
        section = deck.slides[0].root_section.children[0]
        # This will now be one single text element.
        assert len(section.children) == 1
        assert "---" in section.children[0].text

    def test_table_with_row_directives(self, parser: Parser):
        """Test Case: PARSER-C-09"""
        markdown = ":::section\n| Header | Data | Directives |\n|---|---|---|\n| | | [background=gray] |\n| R1 | D1 | |\n| R2 | D2 | [color=red] |\n:::"
        deck = parser.parse(markdown)
        table = deck.slides[0].root_section.children[0].children[0]
        assert table.element_type == ElementType.TABLE
        assert table.row_directives[0] is not None

    def test_image_with_required_dimensions_succeeds_in_paragraph(self, parser: Parser):
        """Validates that an image with width and height directives is parsed correctly."""
        markdown = ":::section\n![alt](url.png) [width=100][height=50]\n:::"
        deck = parser.parse(markdown)
        element = deck.slides[0].root_section.children[0].children[0]
        assert element.element_type == ElementType.IMAGE

    def test_image_missing_dimensions_raises_error(self, parser: Parser):
        """Test Case: Updated per PARSER_SPEC.md Rule #4.2"""
        markdown_no_height = ":::section\n![alt](url.png) [width=100]\n:::"
        deck = parser.parse(markdown_no_height)
        assert "Error" in deck.slides[0].get_title_element().text

    def test_slide_with_base_directives(self, parser: Parser):
        """Test Case: Implied by PARSER_SPEC.md Rule #4.4"""
        markdown = "[color=blue][fontsize=12]\n# My Title\n\n:::section\nSome Text\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.base_directives.get("color") is not None
        assert slide.base_directives.get("fontsize") == 12.0
        text_element = slide.root_section.children[0].children[0]
        assert text_element.text == "Some Text"

    def test_image_with_caption_creates_two_elements(self, parser: Parser):
        """Tests new functionality for mixed image/text paragraphs."""
        markdown = ":::section\n![alt text](url.png)[width=100][height=50] This is a caption.\n:::"
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children
        assert len(elements) == 2
        assert elements[0].element_type == ElementType.IMAGE
        assert elements[1].element_type == ElementType.TEXT
        assert elements[1].text == "This is a caption."

    def test_column_with_content_and_nested_row(self, parser: Parser):
        """Tests a column with both its own content and a nested row."""
        markdown = ":::row\n:::column\n:::section\nOuter Content\n:::\n:::row\n:::column\n:::section\nInner\n:::\n:::\n:::\n:::\n:::"
        deck = parser.parse(markdown)
        column = deck.slides[0].root_section.children[0].children[0]
        assert len(column.children) == 2
        assert column.children[0].children[0].text == "Outer Content"
        assert column.children[1].type == "row"

    def test_paragraph_with_text_image_and_caption(self, parser: Parser):
        """NEW TEST: Validates a paragraph with leading text, an image, and a caption."""
        markdown = ":::section\nSome leading text. ![alt text](url.png)[width=100][height=50] This is a caption.\n:::"
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children
        assert len(elements) == 3
        assert elements[0].element_type == ElementType.TEXT
        assert elements[1].element_type == ElementType.IMAGE
        assert elements[2].element_type == ElementType.TEXT


class TestParserGrammarV2:
    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    def test_grammar_error_on_content_outside_section(self, parser: Parser):
        """Test Case: PARSER-C-14"""
        markdown = "This text is floating and illegal."
        with pytest.raises(
            GrammarError, match="Found body content outside of a ':::section' block"
        ):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_content_in_column(self, parser: Parser):
        """Test Case: PARSER-C-12 (for columns)"""
        markdown = ":::row\n:::column\nThis text is illegal.\n:::\n:::"
        with pytest.raises(GrammarError, match="directly inside a ':::column' block"):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_content_in_row(self, parser: Parser):
        """Test Case: PARSER-C-12 (for rows)"""
        markdown = ":::row\nThis text is illegal.\n:::"
        with pytest.raises(GrammarError, match="directly inside a ':::row' block"):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_column_outside_row(self, parser: Parser):
        """Test Case: PARSER-C-13"""
        markdown = ":::column\n:::section\nA lonely column.\n:::\n:::"
        with pytest.raises(
            GrammarError,
            match="A ':::column' block can only be a direct child of a ':::row' block",
        ):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_row_inside_section(self, parser: Parser):
        """NEW TEST: Validates hierarchy rule: section cannot contain row."""
        markdown = ":::section\n:::row\n:::column\n:::\n:::\n:::"
        with pytest.raises(
            GrammarError,
            match="A ':::row' block cannot be a child of a ':::section' block",
        ):
            parser.section_parser.parse_sections(markdown)

    def test_grammar_error_on_unclosed_block(self, parser: Parser):
        """Test Case: PARSER-E-01"""
        markdown = ":::section\nSome content"
        with pytest.raises(GrammarError, match="Found 1 unclosed section"):
            parser.section_parser.parse_sections(markdown)
