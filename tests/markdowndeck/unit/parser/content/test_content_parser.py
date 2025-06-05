"""Updated unit tests for the ContentParser with enhanced directive handling."""

from unittest.mock import Mock

import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import ElementType
from markdowndeck.models.slide import Section
from markdowndeck.parser.content.content_parser import ContentParser
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.directive import DirectiveParser


class TestContentParser:
    """Updated unit tests for the ContentParser."""

    @pytest.fixture
    def parser(self) -> ContentParser:
        """Return a real ContentParser instance."""
        return ContentParser()

    def test_initialization(self):
        """Test that ContentParser initializes with correct components."""
        parser = ContentParser()
        assert isinstance(parser.md, MarkdownIt)
        assert isinstance(parser.element_factory, ElementFactory)
        assert isinstance(parser.directive_parser, DirectiveParser)
        assert len(parser.formatters) == 5

        # Verify formatter types and order
        formatter_types = [type(f).__name__ for f in parser.formatters]
        expected_types = [
            "ImageFormatter",
            "ListFormatter",
            "CodeFormatter",
            "TableFormatter",
            "TextFormatter",
        ]
        assert formatter_types == expected_types

    def test_parse_content_with_title_and_footer(self, parser: ContentParser):
        """Test parsing with title and footer."""
        slide_title = "Test Title"
        slide_footer = "Test Footer"
        sections = []
        title_directives = {
            "align": "center",
            "color": {"type": "named", "value": "blue"},
        }

        elements = parser.parse_content(slide_title, sections, slide_footer, title_directives)

        assert len(elements) == 2  # Title and footer

        # Check title element
        title_elem = elements[0]
        assert title_elem.element_type == ElementType.TITLE
        assert title_elem.text == slide_title
        assert title_elem.directives["align"] == "center"
        assert title_elem.directives["color"]["value"] == "blue"

        # Check footer element
        footer_elem = elements[1]
        assert footer_elem.element_type == ElementType.FOOTER
        assert footer_elem.text == slide_footer

    def test_parse_content_with_sections(self, parser: ContentParser):
        """Test parsing content with sections."""
        sections = [
            Section(
                type="section",
                id="test_section",
                content="This is **bold** text.",
                directives={"align": "center"},
                elements=[],
            )
        ]

        elements = parser.parse_content("Title", sections, None)

        # Should have title + section content
        assert len(elements) >= 2

        # Check that section has elements populated
        assert len(sections[0].elements) == 1
        section_elem = sections[0].elements[0]
        assert section_elem.element_type == ElementType.TEXT
        assert section_elem.text == "This is bold text."
        assert section_elem.directives["align"] == "center"

    def test_parse_content_with_row_and_subsections(self, parser: ContentParser):
        """Test parsing content with row sections and subsections."""
        subsection1 = Section(
            type="section",
            id="sub1",
            content="Left content",
            directives={"width": 0.5},
            elements=[],
        )
        subsection2 = Section(
            type="section",
            id="sub2",
            content="Right content",
            directives={"width": 0.5},
            elements=[],
        )
        row_section = Section(
            type="row",
            id="row1",
            content="",
            directives={},
            subsections=[subsection1, subsection2],
            elements=[],
        )

        elements = parser.parse_content("Title", [row_section], None)

        # Should have title + 2 subsection elements
        assert len(elements) == 3

        # Check subsections have elements
        assert len(subsection1.elements) == 1
        assert len(subsection2.elements) == 1

        assert subsection1.elements[0].text == "Left content"
        assert subsection2.elements[0].text == "Right content"

    def test_extract_preceding_directives_with_directive_paragraph(self, parser: ContentParser):
        """Test extraction of preceding directives from directive-only paragraphs."""
        # Create tokens for: [align=center]\n- List item
        tokens = parser.md.parse("[align=center]\n- List item")

        # Should find directive paragraph at start
        directives, consumed = parser._extract_preceding_directives(tokens, 0)

        assert directives == {"align": "center"}
        assert consumed > 0  # Should consume the directive paragraph tokens

    def test_extract_preceding_directives_no_directives(self, parser: ContentParser):
        """Test that non-directive paragraphs are not consumed."""
        tokens = parser.md.parse("Regular paragraph\n- List item")

        directives, consumed = parser._extract_preceding_directives(tokens, 0)

        assert directives == {}
        assert consumed == 0

    def test_analyze_headings(self, parser: ContentParser):
        """Test heading analysis for proper classification."""
        markdown = "# Title\n## Subtitle\n### Section Heading\n## Another Section"
        tokens = parser.md.parse(markdown)

        heading_info = parser._analyze_headings(tokens)

        # Find heading token indices
        heading_indices = [i for i, token in enumerate(tokens) if token.type == "heading_open"]
        assert len(heading_indices) == 4

        # Check classifications
        assert heading_info[heading_indices[0]]["type"] == "title"  # First H1
        assert heading_info[heading_indices[1]]["type"] == "subtitle"  # H2 after H1
        assert heading_info[heading_indices[2]]["type"] == "section"  # H3
        assert heading_info[heading_indices[3]]["type"] == "section"  # Second H2

    def test_dispatch_to_formatter_with_heading_context(self, parser: ContentParser):
        """Test formatter dispatch with heading context information."""
        tokens = parser.md.parse("## Section Heading")
        heading_info = {0: {"type": "section", "level": 2}}

        element, end_index = parser._dispatch_to_formatter(tokens, 0, {}, heading_info)

        assert element is not None
        assert element.element_type == ElementType.TEXT  # Section headings become TEXT
        assert element.text == "Section Heading"

    def test_merge_directives(self, parser: ContentParser):
        """Test directive merging with precedence."""
        section_directives = {"color": "blue", "align": "left", "fontsize": 12}
        element_directives = {"align": "center", "fontweight": "bold"}

        merged = parser._merge_directives(section_directives, element_directives)

        expected = {
            "color": "blue",  # From section
            "align": "center",  # Element overrides section
            "fontsize": 12,  # From section
            "fontweight": "bold",  # From element
        }
        assert merged == expected

    def test_process_tokens_with_directive_detection_table(self, parser: ContentParser):
        """Test processing tokens with directive detection for tables."""
        markdown = "[border=solid]\n| A | B |\n|---|---|\n| 1 | 2 |"
        tokens = parser.md.parse(markdown)

        elements = parser._process_tokens_with_directive_detection(tokens, {})

        # Should have only a table element, no text element for directives
        table_elements = [e for e in elements if e.element_type == ElementType.TABLE]
        text_elements = [e for e in elements if e.element_type == ElementType.TEXT]

        assert len(table_elements) == 1
        assert len(text_elements) == 0  # No spurious text element

        # Table should have the directive
        table_elem = table_elements[0]
        assert "border" in table_elem.directives

    def test_process_tokens_with_directive_detection_list(self, parser: ContentParser):
        """Test processing tokens with directive detection for lists."""
        markdown = "[color=red]\n- Item 1\n- Item 2"
        tokens = parser.md.parse(markdown)

        elements = parser._process_tokens_with_directive_detection(tokens, {})

        # Should have only a list element
        list_elements = [e for e in elements if e.element_type == ElementType.BULLET_LIST]
        text_elements = [e for e in elements if e.element_type == ElementType.TEXT]

        assert len(list_elements) == 1
        assert len(text_elements) == 0

        # List should have the directive
        list_elem = list_elements[0]
        assert list_elem.directives["color"]["value"] == "red"

    def test_process_tokens_with_directive_detection_code(self, parser: ContentParser):
        """Test processing tokens with directive detection for code blocks."""
        markdown = "[background=black]\n```python\nprint('hello')\n```"
        tokens = parser.md.parse(markdown)

        elements = parser._process_tokens_with_directive_detection(tokens, {})

        # Should have only a code element
        code_elements = [e for e in elements if e.element_type == ElementType.CODE]
        text_elements = [e for e in elements if e.element_type == ElementType.TEXT]

        assert len(code_elements) == 1
        assert len(text_elements) == 0

        # Code should have the directive
        code_elem = code_elements[0]
        assert code_elem.directives["background"]["value"] == "black"

    def test_process_tokens_error_handling(self, parser: ContentParser):
        """Test error handling in token processing."""
        tokens = parser.md.parse("Normal text")

        # Mock a formatter to raise an exception
        original_formatters = parser.formatters[:]
        mock_formatter = Mock()
        mock_formatter.can_handle.return_value = True
        mock_formatter.process.side_effect = ValueError("Test error")
        parser.formatters = [mock_formatter]

        try:
            # Should not raise exception, should handle gracefully
            elements = parser._process_tokens_with_directive_detection(tokens, {})
            assert elements == []  # No elements due to error
        finally:
            # Restore original formatters
            parser.formatters = original_formatters

    def test_complex_directive_and_content_mixing(self, parser: ContentParser):
        """Test complex mixing of directives and content."""
        sections = [
            Section(
                type="section",
                id="complex",
                content="""[color=blue][fontsize=14]
This is blue text.

[align=center]
## Centered Heading

[fontweight=bold]
**Bold paragraph** with formatting.

[border=solid]
- List item 1
- List item 2""",
                directives={"margin": 10},
                elements=[],
            )
        ]

        parser.parse_content("Title", sections, None)

        # Check that section elements were populated
        section_elements = sections[0].elements
        assert len(section_elements) >= 4  # Text, heading, text, list

        # Check element types and directives
        text_elements = [e for e in section_elements if e.element_type == ElementType.TEXT]
        list_elements = [e for e in section_elements if e.element_type == ElementType.BULLET_LIST]

        # First text element should have section + element directives
        first_text = next(e for e in text_elements if "blue text" in e.text)
        assert first_text.directives["color"]["value"] == "blue"
        assert first_text.directives["fontsize"] == 14
        assert first_text.directives["margin"] == 10  # Inherited from section

        # List should have border directive + section margin
        assert len(list_elements) == 1
        list_elem = list_elements[0]
        assert "border" in list_elem.directives
        assert list_elem.directives["margin"] == 10

    def test_empty_content_handling(self, parser: ContentParser):
        """Test handling of empty or whitespace-only content."""
        sections = [
            Section(
                type="section",
                id="empty",
                content="   \n   \n   ",  # Only whitespace
                directives={},
                elements=[],
            ),
            Section(
                type="section",
                id="directives_only",
                content="[width=100%][height=50%]",  # Only directives
                directives={},
                elements=[],
            ),
        ]

        # CRITICAL FIX: Manually parse directives on the directive-only section
        # to simulate the normal flow where DirectiveParser runs before ContentParser
        directive_parser = DirectiveParser()
        directive_parser.parse_directives(sections[1])

        elements = parser.parse_content("Title", sections, None)

        # Should only have title element
        assert len(elements) == 1
        assert elements[0].element_type == ElementType.TITLE

        # First section should have no elements
        assert len(sections[0].elements) == 0

        # Second section should have parsed directives but no elements
        assert sections[1].directives["width"] == 1.0  # 100%
        assert sections[1].directives["height"] == 0.5  # 50%
        assert len(sections[1].elements) == 0
