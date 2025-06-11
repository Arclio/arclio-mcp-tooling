"""
Unit tests for the Parser component, ensuring adherence to PARSER_SPEC.md.
"""

import pytest
from markdowndeck.models import SlideLayout, TextFormatType
from markdowndeck.parser import Parser


class TestParser:
    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    def test_parser_c_01(self, parser: Parser):
        """
        Test Case: PARSER-C-01
        Validates parsing a simple slide into the correct "Unpositioned" state.
        """
        deck = parser.parse("# Title\nSome content.")
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        assert len(slide.elements) == 2
        assert slide.layout == SlideLayout.BLANK, "Layout must always be BLANK."
        for element in slide.elements:
            assert element.position is None
            assert element.size is None

    def test_parser_c_02(self, parser: Parser):
        """
        Test Case: PARSER-C-02
        Validates that '===' correctly splits markdown into multiple slides.
        """
        deck = parser.parse("# Slide 1\nContent 1\n===\n# Slide 2\nContent 2")
        assert len(deck.slides) == 2
        assert deck.slides[0].title == "Slide 1"
        assert deck.slides[1].title == "Slide 2"

    def test_parser_c_03(self, parser: Parser):
        """
        Test Case: PARSER-C-03
        Validates correct extraction of title, footer, and notes.
        """
        markdown = (
            "# Title [align=center]\n<!-- notes: My notes -->\nContent\n@@@\nFooter"
        )
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.title == "Title"
        assert slide.title_directives.get("align") == "center"
        assert slide.notes == "My notes"
        assert slide.footer == "Footer"

    def test_parser_c_05(self, parser: Parser):
        """
        Test Case: PARSER-C-05
        Validates that '---' correctly splits content into vertical sections.
        """
        deck = parser.parse("# Vertical Sections\nTop Section\n---\nBottom Section")
        slide = deck.slides[0]
        assert len(slide.sections) == 2
        assert "Top Section" in slide.sections[0].children[0].text
        assert "Bottom Section" in slide.sections[1].children[0].text

    def test_parser_c_06(self, parser: Parser):
        """
        Test Case: PARSER-C-06
        Validates that '***' creates a 'row' section with nested children.
        """
        deck = parser.parse("# Horizontal Sections\nLeft Column\n***\nRight Column")
        slide = deck.slides[0]
        assert len(slide.sections) == 1
        row_section = slide.sections[0]
        assert row_section.type == "row"
        assert len(row_section.children) == 2

    def test_parser_c_12(self, parser: Parser):
        """
        Test Case: PARSER-C-12
        Validates correct creation of TextElement with inline formatting.
        """
        markdown = "Text with **bold**, *italic*, and `code` spans."
        deck = parser.parse(markdown)
        text_element = deck.slides[0].sections[0].children[0]
        assert text_element.text == "Text with bold, italic, and code spans."
        formats = {f.format_type for f in text_element.formatting}
        assert {
            TextFormatType.BOLD,
            TextFormatType.ITALIC,
            TextFormatType.CODE,
        }.issubset(formats)
