"""Updated unit tests for the TextFormatter with enhanced directive handling."""

from unittest.mock import Mock

import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    TextElement,
    TextFormatType,
)
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters.text import TextFormatter
from markdowndeck.parser.directive import DirectiveParser


class TestTextFormatter:
    """Updated unit tests for the TextFormatter."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def directive_parser(self) -> DirectiveParser:
        return DirectiveParser()

    @pytest.fixture
    def formatter(self, factory: ElementFactory, directive_parser: DirectiveParser) -> TextFormatter:
        return TextFormatter(factory, directive_parser)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        md = MarkdownIt()
        md.enable("strikethrough")
        return md

    # ========================================================================
    # Basic Functionality Tests (Updated)
    # ========================================================================

    @pytest.mark.parametrize("token_type", ["heading_open", "paragraph_open", "blockquote_open"])
    def test_can_handle_valid_tokens(self, formatter: TextFormatter, token_type: str, md_parser: MarkdownIt):
        """Test can_handle for valid token types."""
        if token_type == "paragraph_open":
            tokens = md_parser.parse("Just some text.")
            assert formatter.can_handle(tokens[0], tokens)
        elif token_type == "heading_open":
            tokens = md_parser.parse("## A heading")
            assert formatter.can_handle(tokens[0], tokens)
        elif token_type == "blockquote_open":
            tokens = md_parser.parse("> A quote")
            assert formatter.can_handle(tokens[0], tokens)

    def test_cannot_handle_other_tokens(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test that non-text tokens are not handled."""
        tokens = md_parser.parse("* List item")
        assert not formatter.can_handle(tokens[0], tokens)

    def test_cannot_handle_image_only_paragraphs(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test that image-only paragraphs are not handled by TextFormatter."""
        tokens = md_parser.parse("![alt text](image.png)")
        # Should not handle image-only paragraphs
        assert not formatter.can_handle(tokens[0], tokens)

    # ========================================================================
    # Enhanced Heading Processing Tests
    # ========================================================================

    @pytest.mark.parametrize(
        (
            "level",
            "is_section_heading",
            "is_subtitle",
            "expected_type",
            "expected_align",
        ),
        [
            (1, False, False, ElementType.TITLE, AlignmentType.CENTER),
            (2, False, True, ElementType.SUBTITLE, AlignmentType.CENTER),
            (2, True, False, ElementType.TEXT, AlignmentType.LEFT),
            (3, True, False, ElementType.TEXT, AlignmentType.LEFT),
        ],
    )
    def test_process_heading_with_context(
        self,
        formatter: TextFormatter,
        md_parser: MarkdownIt,
        level: int,
        is_section_heading: bool,
        is_subtitle: bool,
        expected_type: ElementType,
        expected_align: AlignmentType,
    ):
        """Test heading processing with proper context flags."""
        markdown = f"{'#' * level} Test Heading"
        tokens = md_parser.parse(markdown)

        element, end_index = formatter.process(
            tokens,
            0,
            {},
            None,
            is_section_heading=is_section_heading,
            is_subtitle=is_subtitle,
        )

        assert isinstance(element, TextElement)
        assert element.element_type == expected_type
        assert element.text == "Test Heading"
        assert element.horizontal_alignment == expected_align
        assert end_index == 2

    def test_process_heading_with_section_styling(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test that section headings get appropriate styling."""
        markdown = "## Section Heading"
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, None, is_section_heading=True)

        assert element.element_type == ElementType.TEXT
        assert element.directives.get("fontsize") == 18
        assert element.directives.get("margin_bottom") == 10

    def test_process_heading_with_directives(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test heading processing with directives."""
        markdown = "# Test Heading"
        tokens = md_parser.parse(markdown)
        directives = {"align": "right", "color": {"type": "named", "value": "blue"}}

        element, _ = formatter.process(tokens, 0, directives, None)

        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Heading"
        # Title elements don't use directives for alignment (they have their own logic)
        # But directives should still be stored
        assert element.directives.get("align") == "right"

    # ========================================================================
    # Enhanced Paragraph Processing Tests (P0, P4 Fixes)
    # ========================================================================

    def test_process_paragraph_with_inline_directives_P4(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test processing paragraphs with inline directives (P4 fix)."""
        # Simulate a paragraph with directives at the start
        tokens = md_parser.parse("[color=red][fontsize=14]This is styled text.")

        element, end_index = formatter.process(tokens, 0, {}, None)

        assert isinstance(element, TextElement)
        assert element.element_type == ElementType.TEXT
        # CRITICAL: Text should NOT contain the directive strings (P0 fix)
        assert element.text == "This is styled text."
        assert "[color=red]" not in element.text
        assert "[fontsize=14]" not in element.text

        # Directives should be properly parsed
        assert element.directives["color"]["value"] == "red"
        assert element.directives["fontsize"] == 14

    def test_process_paragraph_directive_separate_line_P0(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test paragraph with directives on separate line (P0 fix)."""
        markdown = """[align=center][font-family=Arial]
This text should be centered and Arial."""
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, None)

        assert element.text == "This text should be centered and Arial."
        # Ensure NO directive text remains in the content
        assert "[align=center]" not in element.text
        assert "[font-family=Arial]" not in element.text

        # Check directives are applied
        assert element.directives["align"] == "center"
        assert element.directives["font-family"] == "Arial"
        assert element.horizontal_alignment == AlignmentType.CENTER

    def test_process_paragraph_mixed_directive_content(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test paragraph processing with mixed directive and content patterns."""
        # Test case where some lines have directives, others don't
        markdown = """[color=blue]
First paragraph with color.

[fontsize=16]
Second paragraph with size."""
        tokens = md_parser.parse(markdown)

        # This would be processed as one paragraph token in markdown-it
        # We expect clean text extraction
        element, _ = formatter.process(tokens, 0, {}, None)

        # Verify directive removal and proper text content
        assert "[color=blue]" not in element.text
        assert "[fontsize=16]" not in element.text
        assert "First paragraph with color." in element.text or "Second paragraph with size." in element.text

    def test_process_paragraph_with_formatting_and_directives(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test paragraph with both formatting and directives."""
        markdown = "[align=justify]This has **bold** and *italic* text."
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, None)

        # Text should be clean of directives but preserve content
        assert element.text == "This has bold and italic text."
        assert element.directives["align"] == "justify"
        assert element.horizontal_alignment == AlignmentType.JUSTIFY

        # Should have formatting for bold and italic
        bold_formats = [f for f in element.formatting if f.format_type == TextFormatType.BOLD]
        italic_formats = [f for f in element.formatting if f.format_type == TextFormatType.ITALIC]
        assert len(bold_formats) == 1
        assert len(italic_formats) == 1

    def test_process_paragraph_empty_after_directive_removal(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test paragraph that becomes empty after directive removal."""
        markdown = "[width=100%][height=50%]"  # Only directives, no text
        tokens = md_parser.parse(markdown)

        element, end_index = formatter.process(tokens, 0, {}, None)

        # Should return None for empty paragraphs
        assert element is None

    # ========================================================================
    # Directive Extraction Tests
    # ========================================================================

    def test_extract_element_directives_from_text_multiline(self, formatter: TextFormatter):
        """Test directive extraction from multi-line text."""
        text = """[color=red][fontsize=12]
First line of content.
[align=center]
Second line with different alignment."""

        directives, cleaned_text = formatter._extract_element_directives_from_text(text)

        # Should extract directives from directive-only lines
        assert directives["color"]["value"] == "red"
        assert directives["fontsize"] == 12
        assert directives["align"] == "center"

        # Cleaned text should not contain directive lines
        assert "[color=red]" not in cleaned_text
        assert "[fontsize=12]" not in cleaned_text
        assert "[align=center]" not in cleaned_text
        assert "First line of content." in cleaned_text
        assert "Second line with different alignment." in cleaned_text

    def test_extract_line_start_directives_P4(self, formatter: TextFormatter):
        """Test extraction of directives from start of content lines (P4 enhancement)."""
        # Test same-line directive extraction
        directives, cleaned = formatter._extract_line_start_directives("[color=blue][margin=5px] Content here")

        assert directives["color"]["value"] == "blue"
        assert directives["margin"] == 5
        assert cleaned == "Content here"

        # Test line without directives
        directives2, cleaned2 = formatter._extract_line_start_directives("Just normal content")
        assert directives2 == {}
        assert cleaned2 == "Just normal content"

    def test_extract_element_directives_complex_scenarios(self, formatter: TextFormatter):
        """Test complex directive extraction scenarios."""
        # Mixed directive-only and directive+content lines
        text = """[background=yellow]
[border=solid]
This is content with background and border.
[fontsize=16] This line starts with directive but has content.
Regular content line.
[color=green]
Final content line."""

        directives, cleaned_text = formatter._extract_element_directives_from_text(text)

        # Should extract from directive-only lines and start-of-line directives
        assert directives["background"]["value"] == "yellow"
        assert directives["border"]["style"] == "solid"
        assert directives["fontsize"] == 16
        assert directives["color"]["value"] == "green"

        # Cleaned text should have directives removed
        lines = cleaned_text.split("\n")
        content_lines = [line for line in lines if line.strip()]

        assert "This is content with background and border." in content_lines
        assert "This line starts with directive but has content." in content_lines
        assert "Regular content line." in content_lines
        assert "Final content line." in content_lines

    # ========================================================================
    # Blockquote Processing Tests
    # ========================================================================

    def test_process_simple_blockquote(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test simple blockquote processing."""
        markdown = "> This is a quote."
        tokens = md_parser.parse(markdown)

        element, end_index = formatter.process(tokens, 0, {}, None)

        assert isinstance(element, TextElement)
        assert element.element_type == ElementType.QUOTE
        assert element.text == "This is a quote."
        assert end_index == 4

    def test_process_multiline_blockquote(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test multiline blockquote processing."""
        markdown = "> First line.\n> Second line."
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, None)

        assert element.element_type == ElementType.QUOTE
        assert "First line." in element.text
        assert "Second line." in element.text

    def test_process_blockquote_with_formatting(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test blockquote with text formatting."""
        markdown = "> Quote with **bold** text."
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, None)

        assert element.text == "Quote with bold text."
        bold_formats = [f for f in element.formatting if f.format_type == TextFormatType.BOLD]
        assert len(bold_formats) == 1

    def test_process_blockquote_with_directives(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test blockquote with directives."""
        markdown = "> Important quote."
        tokens = md_parser.parse(markdown)
        directives = {"align": "center", "fontweight": "bold"}

        element, _ = formatter.process(tokens, 0, directives, None)

        assert element.element_type == ElementType.QUOTE
        assert element.horizontal_alignment == AlignmentType.CENTER
        assert element.directives["fontweight"] == "bold"

    # ========================================================================
    # Helper Method Tests
    # ========================================================================

    def test_extract_clean_text_and_formatting(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test clean text and formatting extraction."""
        tokens = md_parser.parse("**Bold** and *italic* text.")
        inline_token = tokens[1]  # The inline token

        text, formatting = formatter._extract_clean_text_and_formatting(inline_token)

        assert text == "Bold and italic text."
        assert len(formatting) == 2

        bold_format = next(f for f in formatting if f.format_type == TextFormatType.BOLD)
        italic_format = next(f for f in formatting if f.format_type == TextFormatType.ITALIC)

        assert bold_format.start == 0
        assert bold_format.end == 4
        assert italic_format.start == 9
        assert italic_format.end == 15

    def test_extract_text_from_cleaned_content(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test text extraction from pre-cleaned content."""
        original_tokens = md_parser.parse("[color=red] **Bold** text")
        cleaned_content = "**Bold** text"  # Directives removed

        text, formatting = formatter._extract_text_from_cleaned_content(cleaned_content, original_tokens[1])

        assert text == "**Bold** text"  # Should preserve markdown for formatting extraction
        # Note: This method processes the cleaned markdown, so formatting extraction happens properly

    def test_is_image_only_paragraph(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test image-only paragraph detection."""
        # Image-only paragraph
        tokens1 = md_parser.parse("![alt text](image.png)")
        inline_token1 = tokens1[1]
        assert formatter._is_image_only_paragraph(inline_token1)

        # Paragraph with image and text
        tokens2 = md_parser.parse("![alt text](image.png) Some text")
        inline_token2 = tokens2[1]
        assert not formatter._is_image_only_paragraph(inline_token2)

        # Text-only paragraph
        tokens3 = md_parser.parse("Just text")
        inline_token3 = tokens3[1]
        assert not formatter._is_image_only_paragraph(inline_token3)

    def test_find_paragraph_close(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test finding paragraph close token."""
        tokens = md_parser.parse("Some paragraph text.")
        # tokens: [paragraph_open, inline, paragraph_close]

        close_index = formatter._find_paragraph_close(tokens, 1)  # Start from inline token
        assert close_index == 2  # Should find paragraph_close at index 2

    # ========================================================================
    # Integration Tests with Section Directives
    # ========================================================================

    def test_directive_inheritance_and_override(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test section directive inheritance and element override."""
        markdown = "[fontweight=bold] Text with mixed directives."
        tokens = md_parser.parse(markdown)

        section_directives = {
            "color": {"type": "named", "value": "blue"},
            "fontsize": 12,
        }

        element, _ = formatter.process(tokens, 0, section_directives, None)

        # Should inherit section directives and add element-specific ones
        assert element.directives["color"]["value"] == "blue"  # Inherited
        assert element.directives["fontsize"] == 12  # Inherited
        assert element.directives["fontweight"] == "bold"  # Element-specific
        assert element.text == "Text with mixed directives."

    def test_element_directive_override_section(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test element directives overriding section directives."""
        markdown = "[color=red][fontsize=16] Override text."
        tokens = md_parser.parse(markdown)

        section_directives = {
            "color": {"type": "named", "value": "blue"},
            "fontsize": 12,
            "margin": 5,
        }

        element, _ = formatter.process(tokens, 0, section_directives, None)

        # Element directives should override section directives
        assert element.directives["color"]["value"] == "red"  # Overridden
        assert element.directives["fontsize"] == 16  # Overridden
        assert element.directives["margin"] == 5  # Inherited (not overridden)

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_process_with_invalid_tokens(self, formatter: TextFormatter):
        """Test processing with invalid or malformed tokens."""
        # Empty token list
        element, index = formatter.process([], 0, {}, None)
        assert element is None
        assert index == 0

        # Index out of bounds
        tokens = [Mock()]
        element, index = formatter.process(tokens, 5, {}, None)
        assert element is None
        assert index == 5

    def test_process_unsupported_token_type(self, formatter: TextFormatter, md_parser: MarkdownIt):
        """Test processing unsupported token types."""
        # Create a mock token that TextFormatter shouldn't handle
        from unittest.mock import Mock

        tokens = [Mock()]
        tokens[0].type = "unsupported_type"

        element, index = formatter.process(tokens, 0, {}, None)
        assert element is None
        assert index == 0
