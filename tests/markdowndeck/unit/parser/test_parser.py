import pytest
from markdowndeck.models import ElementType, ListElement
from markdowndeck.parser import Parser


class TestParser:
    @pytest.fixture
    def parser(self) -> Parser:
        return Parser()

    def test_parser_parses_all_content_blocks(self, parser: Parser):
        """
        Test Case: PARSER-C-11 (Custom ID)
        Description: Validates that the parser processes all distinct content blocks within
                     a single section, not just the first one. This directly targets the
                     content loss bug.
        """
        # Arrange
        markdown = """
        :::section
        # First Block (H1)
        This is the second block (paragraph).
        - This is the third block (list).
        :::
        """

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # The content is inside root_section -> section
        parsed_elements = slide.root_section.children[0].children

        # Assert
        assert (
            len(parsed_elements) == 3
        ), "Parser should have created 3 distinct elements."

        element_types = [el.element_type for el in parsed_elements]
        assert (
            ElementType.TEXT in element_types
        ), "A TextElement for the heading should exist."
        assert ElementType.BULLET_LIST in element_types, "A ListElement should exist."

        heading = next(
            el
            for el in parsed_elements
            if el.element_type == ElementType.TEXT and el.heading_level == 1
        )
        paragraph = next(
            el
            for el in parsed_elements
            if el.element_type == ElementType.TEXT and el.heading_level is None
        )
        list_element = next(el for el in parsed_elements if isinstance(el, ListElement))

        assert "First Block" in heading.text
        assert "second block" in paragraph.text
        assert "third block" in list_element.items[0].text

    def test_fenced_block_section_creation(self, parser: Parser):
        """Test Case: PARSER-C-04"""
        markdown = ":::section [padding=20]\nContent\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        root_section = slide.root_section
        assert len(root_section.children) == 1
        nested_section = root_section.children[0]
        assert nested_section.type == "section"
        assert nested_section.directives.get("padding") == 20.0
        assert nested_section.children[0].element_type == ElementType.TEXT
        assert nested_section.children[0].text == "Content"

    def test_fenced_block_row_and_column_creation(self, parser: Parser):
        """Test Case: PARSER-C-05"""
        markdown = ":::row [gap=30]\n:::column [width=40%]\nLeft\n:::\n:::column\nRight\n:::\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        row = slide.root_section.children[0]
        assert row.type == "row"
        assert row.directives.get("gap") == 30.0
        assert len(row.children) == 2
        col1, col2 = row.children
        assert col1.type == "section"
        assert col1.directives.get("width") == 0.4
        assert col1.children[0].text == "Left"
        assert col2.children[0].text == "Right"

    def test_fenced_block_nesting(self, parser: Parser):
        """Test Case: PARSER-C-06"""
        markdown = ":::section\nOuter\n:::section [padding=10]\nInner\n:::\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        outer_section = slide.root_section.children[0]
        assert len(outer_section.children) == 2
        assert outer_section.children[0].element_type == ElementType.TEXT
        assert outer_section.children[0].text == "Outer"
        inner_section = outer_section.children[1]
        assert isinstance(inner_section, type(outer_section))
        assert inner_section.directives.get("padding") == 10.0
        assert inner_section.children[0].text == "Inner"

    def test_deprecated_separators_are_ignored_for_layout(self, parser: Parser):
        """Test Case: PARSER-E-03"""
        markdown = ":::section\nTop\n---\nBottom\n***\nRight\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.root_section.children[0]
        assert len(section.children) > 1
        texts = [child.text for child in section.children if hasattr(child, "text")]
        assert "Top" in texts
        assert "Bottom" in texts
        assert "Right" in texts

    def test_table_with_row_directives(self, parser: Parser):
        """Test Case: PARSER-C-09"""
        markdown = """
:::section
| Header | Data | Directives          |
|--------|------|---------------------|
|        |      | [background=gray]   |
| R1     | D1   |                     |
| R2     | D2   | [color=red]         |
:::
"""
        deck = parser.parse(markdown)
        # Find the table element, as it might not be the first one if other text is parsed.
        table = next(
            e for e in deck.slides[0].elements if e.element_type == ElementType.TABLE
        )
        assert table is not None, "Table element not found in parsed slide."
        assert table.headers == ["Header", "Data"]
        assert table.rows == [["R1", "D1"], ["R2", "D2"]]
        assert len(table.row_directives) == 3
        assert table.row_directives[0] == {
            "background": {"type": "color", "value": {"type": "named", "value": "gray"}}
        }
        assert table.row_directives[1] == {}
        assert table.row_directives[2] == {
            "color": {"type": "color", "value": {"type": "named", "value": "red"}}
        }

    def test_image_with_required_dimensions_succeeds_in_paragraph(self, parser: Parser):
        """Validates that an image with width and height directives is parsed correctly."""
        markdown = "![alt](url.png) [width=100][height=50]"
        deck = parser.parse(markdown)
        element = deck.slides[0].elements[0]
        assert element.element_type == ElementType.IMAGE
        assert element.directives["width"] == 100.0
        assert element.directives["height"] == 50.0

    def test_image_missing_dimensions_raises_error(self, parser: Parser):
        """Test Case: Updated per PARSER_SPEC.md Rule #4.2 and [fill] directive exception"""
        markdown_no_height = "![alt](url.png) [width=100]"
        deck = parser.parse(markdown_no_height)
        slide = deck.slides[0]
        title_element = slide.get_title_element()
        assert "Error in Slide" in title_element.text
        text_element = next(
            e for e in slide.elements if e.element_type == ElementType.TEXT
        )
        assert "must have both [width] and [height]" in text_element.text

        markdown_with_fill = "![alt](url.png) [fill]"
        deck_with_fill = parser.parse(markdown_with_fill)
        slide_with_fill = deck_with_fill.slides[0]

        title_element_fill = slide_with_fill.get_title_element()
        if title_element_fill:
            assert "Error in Slide" not in title_element_fill.text

        image_elements = [
            e for e in slide_with_fill.elements if e.element_type == ElementType.IMAGE
        ]
        assert len(image_elements) == 1
        image_element = image_elements[0]
        assert image_element.directives.get("fill") is True

    def test_slide_with_base_directives(self, parser: Parser):
        """Test Case: Implied by PARSER_SPEC.md Rule #4.4"""
        markdown = "[color=blue][fontsize=12]\n# My Title"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.base_directives == {
            "color": {"type": "color", "value": {"type": "named", "value": "blue"}},
            "fontsize": 12.0,
        }
        assert slide.get_title_element().text == "My Title"

    def test_unclosed_fenced_block(self, parser: Parser, caplog):
        """Test Case: PARSER-E-01"""
        markdown = ":::section\nSome content"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert len(slide.root_section.children) == 1
        section = slide.root_section.children[0]
        assert section.children[0].text == "Some content"
        assert "Found 1 unclosed section(s). Auto-closing." in caplog.text

    def test_column_outside_row_warning(self, parser: Parser, caplog):
        """Test Case: PARSER-E-02"""
        markdown = ":::column\nContent\n:::"
        deck = parser.parse(markdown)
        assert len(deck.slides) == 1
        section = deck.slides[0].root_section.children[0]
        assert section.type == "section"
        assert section.children[0].text == "Content"

    def test_image_with_caption_creates_two_elements(self, parser: Parser):
        """Test new functionality for mixed image/text paragraphs."""
        markdown = "![alt text](url.png)[width=100][height=50] This is a caption."
        deck = parser.parse(markdown)
        elements = deck.slides[0].elements
        assert len(elements) == 2
        assert elements[0].element_type == ElementType.IMAGE
        assert elements[1].element_type == ElementType.TEXT
        assert elements[1].text == "This is a caption."

    def test_table_with_no_directive_column(self, parser: Parser):
        """Tests that a GFM table without the special directive column parses correctly."""
        markdown = "| Header1 | Header2 |\n|---|---|\n| Cell1 | Cell2 |"
        deck = parser.parse(markdown)
        table = next(
            e for e in deck.slides[0].elements if e.element_type == ElementType.TABLE
        )
        assert table is not None
        assert table.headers == ["Header1"]
        assert table.rows == [["Cell1"]]
        assert len(table.row_directives) == 2
        assert table.row_directives[0] == {}
        assert table.row_directives[1] == {}

    def test_fenced_block_with_content_and_nested_section(self, parser: Parser):
        """Tests a section with both its own content and a nested section."""
        markdown = ":::section\nOuter Content\n:::section\nInner Content\n:::\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        outer_section = slide.root_section.children[0]
        assert len(outer_section.children) == 2
        assert outer_section.children[0].element_type == ElementType.TEXT
        assert outer_section.children[0].text == "Outer Content"
        assert outer_section.children[1].type == "section"
        inner_section = outer_section.children[1]
        assert len(inner_section.children) == 1
        assert inner_section.children[0].element_type == ElementType.TEXT
        assert inner_section.children[0].text == "Inner Content"

    def test_paragraph_with_text_image_and_caption(self, parser: Parser):
        """NEW TEST: Validates a paragraph with leading text, an image, and a caption."""
        markdown = "Some leading text. ![alt text](url.png)[width=100][height=50] This is a caption."
        deck = parser.parse(markdown)
        elements = deck.slides[0].elements
        assert len(elements) == 3, "Expected three elements: Text, Image, Text"
        assert elements[0].element_type == ElementType.TEXT
        assert elements[0].text == "Some leading text."
        assert elements[1].element_type == ElementType.IMAGE
        assert elements[1].directives.get("width") == 100.0
        assert elements[2].element_type == ElementType.TEXT
        assert elements[2].text == "This is a caption."
