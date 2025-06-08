"""
Unit tests for the Parser component, ensuring adherence to PARSER_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_PARSER.md`.
"""

import pytest
from markdowndeck.models import ElementType, TextFormatType
from markdowndeck.parser import Parser


class TestParser:
    """Tests the functionality of the MarkdownDeck Parser."""

    @pytest.fixture
    def parser(self) -> Parser:
        """Provides a fresh Parser instance for each test."""
        return Parser()

    def test_parser_c_01(self, parser: Parser):
        """
        Test Case: PARSER-C-01
        Validates parsing a simple slide into the correct "Unpositioned" state.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Title\nSome content."

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 1
        slide = deck.slides[0]

        # Check inventory list
        assert len(slide.elements) == 2
        element_types = [e.element_type for e in slide.elements]
        assert ElementType.TITLE in element_types
        assert ElementType.TEXT in element_types

        # Check sections hierarchy
        assert len(slide.sections) == 1
        root_section = slide.sections[0]
        assert len(root_section.children) == 1
        assert root_section.children[0].element_type == ElementType.TEXT

        # Verify Unpositioned IR state (all spatial attributes must be None)
        for element in slide.elements:
            assert (
                element.position is None
            ), f"Element {element.element_type} should have no position."
            assert (
                element.size is None
            ), f"Element {element.element_type} should have no size."
        for section in slide.sections:
            assert section.position is None, "Section should have no position."
            assert section.size is None, "Section should have no size."

    def test_parser_c_02(self, parser: Parser):
        """
        Test Case: PARSER-C-02
        Validates that '===' correctly splits markdown into multiple slides.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Slide 1\nContent 1\n===\n# Slide 2\nContent 2"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 2
        assert deck.slides[0].title == "Slide 1"
        assert deck.slides[1].title == "Slide 2"
        assert "Content 1" in deck.slides[0].elements[1].text
        assert "Content 2" in deck.slides[1].elements[1].text

    def test_parser_c_03(self, parser: Parser):
        """
        Test Case: PARSER-C-03
        Validates correct extraction of title, footer, notes, and directives.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = (
            "# Title [align=center]\n<!-- notes: My notes -->\nContent\n@@@\nFooter"
        )

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.title == "Title"
        assert slide.title_directives.get("align") == "center"
        assert slide.notes == "My notes"
        assert slide.footer == "Footer"
        assert "Content" in slide.elements[1].text
        # Verify that metadata strings have been properly removed from content elements
        content_text = slide.elements[1].text
        assert "<!-- notes:" not in content_text
        assert "@@@" not in content_text

    def test_parser_c_04(self, parser: Parser):
        """
        Test Case: PARSER-C-04
        Validates that an indented title is correctly identified and removed.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "   #   Indented Title\nContent below."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.title == "Indented Title"
        text_element = next(
            (e for e in slide.elements if e.element_type == ElementType.TEXT), None
        )
        assert text_element is not None
        assert text_element.text == "Content below."

    def test_parser_c_05(self, parser: Parser):
        """
        Test Case: PARSER-C-05
        Validates that '---' correctly splits content into vertical sections.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Vertical Sections\nTop Section\n---\nBottom Section"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 2
        assert "Top Section" in slide.sections[0].children[0].text
        assert "Bottom Section" in slide.sections[1].children[0].text

    def test_parser_c_06(self, parser: Parser):
        """
        Test Case: PARSER-C-06
        Validates that '***' creates a 'row' section with nested children.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Horizontal Sections\nLeft Column\n***\nRight Column"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 1
        row_section = slide.sections[0]
        assert row_section.type == "row"
        assert len(row_section.children) == 2

        left_child_section = row_section.children[0]
        right_child_section = row_section.children[1]
        assert "Left Column" in left_child_section.children[0].text
        assert "Right Column" in right_child_section.children[0].text

    def test_parser_c_07(self, parser: Parser):
        """
        Test Case: PARSER-C-07
        Validates correct parsing of mixed vertical and horizontal sections.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Mixed Layout\nTop\n---\nLeft\n***\nRight\n---\nBottom"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 3
        assert slide.sections[0].type == "section"
        assert "Top" in slide.sections[0].children[0].text
        assert slide.sections[1].type == "row"
        assert len(slide.sections[1].children) == 2
        assert slide.sections[2].type == "section"
        assert "Bottom" in slide.sections[2].children[0].text

    def test_parser_c_08(self, parser: Parser):
        """
        Test Case: PARSER-C-08
        Validates that separators within code blocks are ignored.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "Top\n```\n---\n***\n===\n```\nBottom"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        assert len(slide.sections) == 1
        section_children = slide.sections[0].children
        assert len(section_children) == 3
        assert section_children[0].element_type == ElementType.TEXT
        assert section_children[0].text == "Top"
        assert section_children[1].element_type == ElementType.CODE
        assert section_children[1].code.strip() == "---\n***\n==="
        assert section_children[2].element_type == ElementType.TEXT
        assert section_children[2].text == "Bottom"

    def test_parser_c_09(self, parser: Parser):
        """
        Test Case: PARSER-C-09
        Validates directive association with a section/heading.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[align=center]\n## Centered Section\nContent"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]
        heading_element = next(
            e
            for e in section.children
            if e.element_type == ElementType.TEXT and "Centered Section" in e.text
        )

        # Assert
        assert heading_element is not None
        assert heading_element.directives.get("align") == "center"

    def test_parser_c_10(self, parser: Parser):
        """
        Test Case: PARSER-C-10
        Validates correct directive consumption for block elements.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[border=solid]\n- Item 1\n- Item 2"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]
        list_element = next(
            (e for e in section.children if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        # Assert
        assert list_element is not None
        assert list_element.directives.get("border") == {"style": "solid"}

        # Check for spurious text element
        spurious_text = [
            e
            for e in section.children
            if e.element_type == ElementType.TEXT and e.text.strip() == "[border=solid]"
        ]
        assert len(spurious_text) == 0

    def test_parser_c_11(self, parser: Parser):
        """
        Test Case: PARSER-C-11
        Validates same-line directive parsing and removal from text.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[color=red] This text is red."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        text_element = slide.sections[0].children[0]

        # Assert
        assert text_element.text == "This text is red."
        assert text_element.directives.get("color") == {"type": "named", "value": "red"}

    def test_parser_c_12(self, parser: Parser):
        """
        Test Case: PARSER-C-12
        Validates correct creation of TextElement with inline formatting.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "Text with **bold**, *italic*, and `code` spans."

        # Act
        deck = parser.parse(markdown)
        text_element = deck.slides[0].sections[0].children[0]

        # Assert
        assert text_element.text == "Text with bold, italic, and code spans."
        formats = {f.format_type for f in text_element.formatting}
        assert {
            TextFormatType.BOLD,
            TextFormatType.ITALIC,
            TextFormatType.CODE,
        }.issubset(formats)

        bold_format = next(
            f for f in text_element.formatting if f.format_type == TextFormatType.BOLD
        )
        assert text_element.text[bold_format.start : bold_format.end] == "bold"

    def test_parser_e_01(self, parser: Parser):
        """
        Test Case: PARSER-E-01
        Validates that empty or whitespace-only markdown produces an empty Deck.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Act
        deck1 = parser.parse("")
        deck2 = parser.parse("   \n\t  ")

        # Assert
        assert len(deck1.slides) == 0
        assert len(deck2.slides) == 0

    def test_parser_e_02(self, parser: Parser):
        """
        Test Case: PARSER-E-02
        Validates that markdown with only separators produces an empty Deck.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "===\n---\n***"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 0

    def test_parser_e_03(self, parser: Parser):
        """
        Test Case: PARSER-E-03
        Validates a slide with only directives and no content.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[width=100%][height=100%]"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Assert
        assert len(deck.slides) == 1
        assert len(slide.sections) == 1
        assert len(section.children) == 0
        assert section.directives.get("width") == 1.0
        assert section.directives.get("height") == 1.0
