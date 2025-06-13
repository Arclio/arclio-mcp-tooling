"""
Unit tests for the Parser component, ensuring adherence to PARSER_SPEC.md.
"""

import pytest
from markdowndeck.models import ElementType, SlideLayout, TextFormatType
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

    def test_parser_c_02_slide_splitting(self, parser: Parser):
        """Test Case: PARSER-C-02. Spec: `===` splits markdown into multiple slides."""
        # Arrange
        markdown = "# Slide 1\nContent 1\n===\n# Slide 2\nContent 2"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 2
        assert deck.slides[0].get_title_element().text == "Slide 1"
        assert deck.slides[1].get_title_element().text == "Slide 2"

    def test_parser_c_03_metadata_extraction(self, parser: Parser):
        """Test Case: PARSER-C-03. Spec: Verify extraction of title, footer, notes, and background."""
        # Arrange
        markdown = "[background=#ff0000]\n# Title\n<!-- notes: My notes -->\nContent\n@@@\nFooter"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.get_title_element().text == "Title"
        assert slide.notes == "My notes"
        assert slide.get_footer_element().text == "Footer"
        assert slide.background == {
            "type": "color",
            "value": {"type": "hex", "value": "#ff0000"},
        }
        # Check that metadata is not in the body content
        body_text = slide.root_section.children[0].children[0].text
        assert "My notes" not in body_text
        assert "Footer" not in body_text

    def test_parser_c_04_indented_title(self, parser: Parser):
        """Test Case: PARSER-C-04. Spec: Verify an indented title (H1) is correctly identified."""
        # Arrange
        markdown = "   #   Indented Title\nContent below."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.get_title_element().text == "Indented Title"
        assert slide.root_section.children[0].children[0].text == "Content below."

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

    def test_parser_c_07_mixed_section_parsing(self, parser: Parser):
        """Test Case: PARSER-C-07. Spec: Verify parsing of mixed vertical and horizontal sections."""
        # Arrange
        markdown = "Top\n---\nLeft\n***\nRight\n---\nBottom"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        root_children = slide.root_section.children
        assert len(root_children) == 3
        assert root_children[0].type == "section"
        assert root_children[0].children[0].text == "Top"
        assert root_children[1].type == "row"
        assert len(root_children[1].children) == 2
        assert root_children[1].children[0].children[0].text == "Left"
        assert root_children[1].children[1].children[0].text == "Right"
        assert root_children[2].type == "section"
        assert root_children[2].children[0].text == "Bottom"

    def test_parser_c_08_separators_in_code_blocks(self, parser: Parser):
        """Test Case: PARSER-C-08. Spec: Verify separators within code blocks are ignored."""
        # Arrange
        markdown = "Top\n```\n---\n***\n===\n```\nBottom"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(deck.slides) == 1, "Should not split into multiple slides."
        section = slide.root_section.children[0]
        assert len(section.children) == 3, "Should parse as 3 elements."
        assert section.children[0].element_type == ElementType.TEXT
        assert section.children[1].element_type == ElementType.CODE
        assert "---\n***\n===" in section.children[1].code
        assert section.children[2].element_type == ElementType.TEXT

    def test_parser_c_10_directives_for_block_element(self, parser: Parser):
        """Test Case: PARSER-C-10. Spec: Verify directives on a separate line are associated with a block element."""
        # Arrange
        markdown = "[border=solid]\n- Item 1\n- Item 2"

        # Act
        deck = parser.parse(markdown)
        section = deck.slides[0].root_section.children[0]
        list_element = section.children[0]

        # Assert
        assert len(section.children) == 1
        assert list_element.element_type == ElementType.BULLET_LIST
        assert list_element.directives.get("border") == "solid"

    def test_parser_c_11_same_line_directive_parsing(self, parser: Parser):
        """Test Case: PARSER-C-11. Spec: Verify same-line directives are parsed and removed from text."""
        # Arrange
        markdown = "This text is red. [color=red]"

        # Act
        deck = parser.parse(markdown)
        text_element = deck.slides[0].root_section.children[0].children[0]

        # Assert
        assert text_element.text == "This text is red."
        assert text_element.directives.get("color") == {"type": "named", "value": "red"}

    def test_parser_c_12(self, parser: Parser):
        """Test Case: PARSER-C-12"""
        markdown = "Text with **bold**."
        deck = parser.parse(markdown)
        text_element = deck.slides[0].root_section.children[0].children[0]
        assert text_element.text == "Text with bold."
        assert text_element.formatting[0].format_type == TextFormatType.BOLD

    def test_parser_spec_subtitle_must_follow_title(self, parser: Parser):
        """
        Test Case: PARSER_SPEC.md, 4.3.1
        Spec: A `##` line is only a subtitle if it immediately follows a `#` line.
        """
        # Arrange
        markdown = "# Title\n\n## Not a subtitle"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.get_title_element() is not None
        assert (
            slide.get_subtitle_element() is None
        ), "Subtitle should not be parsed if there's a blank line."
        # It should be a regular H2 text element in the body
        body_elements = slide.root_section.children[0].children
        assert len(body_elements) == 1
        assert body_elements[0].element_type == ElementType.TEXT
        assert body_elements[0].text == "Not a subtitle"
