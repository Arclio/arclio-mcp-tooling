import pytest
from markdowndeck.models import AlignmentType, ElementType, TextFormatType
from markdowndeck.parser.content_parser import ContentParser


class TestContentParser:
    """Tests for the ContentParser component."""

    @pytest.fixture
    def parser(self):
        """Create a content parser for testing."""
        return ContentParser()

    def test_parse_content_with_title(self, parser):
        """Test parsing content with a title."""
        title = "Slide Title"
        sections = [{"type": "section", "content": "Simple content", "directives": {}}]
        footer = None

        elements = parser.parse_content(title, sections, footer)

        assert len(elements) > 0

        # Verify title element
        title_element = elements[0]
        assert title_element.element_type == ElementType.TITLE
        assert title_element.text == "Slide Title"

    def test_parse_content_with_footer(self, parser):
        """Test parsing content with a footer."""
        title = None
        sections = [{"type": "section", "content": "Simple content", "directives": {}}]
        footer = "Slide Footer"

        elements = parser.parse_content(title, sections, footer)

        # Find the footer element
        footer_element = None
        for element in elements:
            if element.element_type == ElementType.FOOTER:
                footer_element = element
                break

        assert footer_element is not None
        assert footer_element.text == "Slide Footer"

    def test_parse_simple_section(self, parser):
        """Test parsing a simple section with text content."""
        section = {
            "type": "section",
            "content": "This is simple text",
            "directives": {},
        }

        elements = parser._parse_simple_section(section)

        assert len(elements) > 0
        assert elements[0].text == "This is simple text"

    def test_parse_section_with_list(self, parser):
        """Test parsing a section with a bullet list."""
        section = {
            "type": "section",
            "content": "* Item 1\n* Item 2\n* Item 3",
            "directives": {},
        }

        elements = parser._parse_simple_section(section)

        # Find the list element
        list_element = None
        for element in elements:
            if element.element_type == ElementType.BULLET_LIST:
                list_element = element
                break

        # Verify bullet list parsing - exact format depends on markdown-it implementation
        assert list_element is not None

    def test_parse_section_with_code(self, parser):
        """Test parsing a section with code block."""
        section = {
            "type": "section",
            "content": "```python\ndef hello():\n    print('Hello world')\n```",
            "directives": {},
        }

        elements = parser._parse_simple_section(section)

        # Find the code element
        code_element = None
        for element in elements:
            if element.element_type == ElementType.CODE:
                code_element = element
                break

        # Verify code parsing
        assert code_element is not None
        assert code_element.language == "python"
        assert "def hello()" in code_element.code

    def test_parse_section_with_image(self, parser):
        """Test parsing a section with an image."""
        section = {
            "type": "section",
            "content": "![Alt text](https://example.com/image.jpg)",
            "directives": {},
        }

        elements = parser._parse_simple_section(section)

        # Find the image element
        image_element = None
        for element in elements:
            if element.element_type == ElementType.IMAGE:
                image_element = element
                break

        # Verify image parsing
        assert image_element is not None
        assert image_element.url == "https://example.com/image.jpg"
        assert image_element.alt_text == "Alt text"

    def test_parse_section_with_heading(self, parser):
        """Test parsing a section with headings."""
        section = {
            "type": "section",
            "content": "## Section Heading\nContent under heading",
            "directives": {},
        }

        elements = parser._parse_simple_section(section)

        # Find the subtitle element (h2)
        subtitle_element = None
        for element in elements:
            if element.element_type == ElementType.SUBTITLE:
                subtitle_element = element
                break

        # Verify heading parsing
        assert subtitle_element is not None
        assert subtitle_element.text == "Section Heading"

    def test_parse_row_section(self, parser):
        """Test parsing a row section with subsections."""
        section = {
            "type": "row",
            "subsections": [
                {"type": "section", "content": "Left column", "directives": {}},
                {"type": "section", "content": "Right column", "directives": {}},
            ],
            "directives": {},
        }

        elements = parser._parse_row_section(section)

        # Verify elements from all subsections are included
        assert len(elements) > 0

        # Check that left and right column text is present in elements
        found_left = False
        found_right = False

        for element in elements:
            if hasattr(element, "text"):
                if "Left column" in element.text:
                    found_left = True
                if "Right column" in element.text:
                    found_right = True

        assert found_left
        assert found_right

    def test_extract_formatting(self, parser):
        """Test extracting formatting from markdown text."""
        # Create a token with formatting (this is a bit hacky for testing)
        from markdown_it import MarkdownIt

        md = MarkdownIt()
        tokens = md.parse("This is **bold** and *italic* text with `code`.")
        inline_token = None

        for token in tokens:
            if token.type == "inline":
                inline_token = token
                break

        assert inline_token is not None

        # Extract formatting
        formatting = parser._extract_formatting(inline_token)

        # Check that bold, italic, and code formatting were extracted
        has_bold = False
        has_italic = False
        has_code = False

        for text_format in formatting:
            if text_format.format_type == TextFormatType.BOLD:
                has_bold = True
            elif text_format.format_type == TextFormatType.ITALIC:
                has_italic = True
            elif text_format.format_type == TextFormatType.CODE:
                has_code = True

        assert has_bold
        assert has_italic
        assert has_code

    def test_apply_alignment_directive(self, parser):
        """Test that alignment directives are applied to elements."""
        section = {
            "type": "section",
            "content": "Text content",
            "directives": {"align": "center"},
        }

        elements = parser._parse_simple_section(section)

        # Verify alignment was applied
        for element in elements:
            if hasattr(element, "horizontal_alignment"):
                assert element.horizontal_alignment == AlignmentType.CENTER
