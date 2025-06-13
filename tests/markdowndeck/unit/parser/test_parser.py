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
        """Test Case: PARSER-C-01"""
        deck = parser.parse("# Title\nSome content.")
        slide = deck.slides[0]
        assert len(slide.elements) == 2
        assert slide.layout == SlideLayout.BLANK
        assert all(el.position is None and el.size is None for el in slide.elements)
        assert slide.root_section is not None
        assert len(slide.root_section.children) == 1
        content_section = slide.root_section.children[0]
        assert content_section.children[0].text == "Some content."

    def test_parser_c_05(self, parser: Parser):
        """Test Case: PARSER-C-05"""
        deck = parser.parse("Top\n---\nBottom")
        slide = deck.slides[0]
        assert slide.root_section is not None
        assert len(slide.root_section.children) == 2
        assert "Top" in slide.root_section.children[0].children[0].text
        assert "Bottom" in slide.root_section.children[1].children[0].text

    def test_parser_c_06(self, parser: Parser):
        """Test Case: PARSER-C-06"""
        deck = parser.parse("Left\n***\nRight")
        slide = deck.slides[0]
        assert slide.root_section is not None
        assert len(slide.root_section.children) == 1
        row = slide.root_section.children[0]
        assert row.type == "row"
        assert len(row.children) == 2

    def test_parser_c_12(self, parser: Parser):
        """Test Case: PARSER-C-12"""
        markdown = "Text with **bold**."
        deck = parser.parse(markdown)
        text_element = deck.slides[0].root_section.children[0].children[0]
        assert text_element.text == "Text with bold."
        assert text_element.formatting[0].format_type == TextFormatType.BOLD
