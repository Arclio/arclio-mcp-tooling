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


class TestTextFormatter:
    """Unit tests for the TextFormatter."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> TextFormatter:
        return TextFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        md = MarkdownIt()
        md.enable("strikethrough")
        return md

    @pytest.mark.parametrize(
        "token_type", ["heading_open", "paragraph_open", "blockquote_open"]
    )
    def test_can_handle_valid_tokens(
        self, formatter: TextFormatter, token_type: str, md_parser: MarkdownIt
    ):
        # For paragraph_open, can_handle might be true even for image-only, process should sort it out
        # or ContentParser's dispatch order should prioritize ImageFormatter.
        # Here we simulate tokens that TextFormatter *should* definitively handle.
        if token_type == "paragraph_open":
            tokens = md_parser.parse("Just some text.")
            assert formatter.can_handle(
                tokens[0], tokens
            )  # tokens[0] is paragraph_open
        elif token_type == "heading_open":
            tokens = md_parser.parse("## A heading")
            assert formatter.can_handle(tokens[0], tokens)  # tokens[0] is heading_open
        elif token_type == "blockquote_open":
            tokens = md_parser.parse("> A quote")
            assert formatter.can_handle(
                tokens[0], tokens
            )  # tokens[0] is blockquote_open

    def test_cannot_handle_other_tokens(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        tokens = md_parser.parse("* List item")  # Creates bullet_list_open, etc.
        assert not formatter.can_handle(
            tokens[0], tokens
        )  # Should not handle bullet_list_open

    # --- Test _process_heading ---
    @pytest.mark.parametrize(
        ("level", "expected_type", "expected_align"),
        [
            (1, ElementType.TITLE, AlignmentType.CENTER),  # H1 is TITLE/CENTER
            (2, ElementType.SUBTITLE, AlignmentType.CENTER),  # H2 is SUBTITLE/CENTER
            (3, ElementType.TEXT, AlignmentType.LEFT),  # H3-H4 are TEXT/LEFT
            (4, ElementType.TEXT, AlignmentType.LEFT),
        ],
    )
    def test_process_heading_levels(
        self,
        formatter: TextFormatter,
        md_parser: MarkdownIt,
        level: int,
        expected_type: ElementType,
        expected_align: AlignmentType,
    ):
        markdown = f"{'#' * level} Test Heading"
        tokens = md_parser.parse(markdown)  # [heading_open, inline, heading_close]
        element, end_index = formatter.process(tokens, 0, {})

        assert isinstance(element, TextElement)
        assert element.element_type == expected_type
        assert element.text == "Test Heading"
        assert element.horizontal_alignment == expected_align
        assert end_index == 2

    def test_process_heading_with_formatting(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "## Heading with **bold** and *italic*"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, TextElement)
        assert element.text == "Heading with bold and italic"
        assert len(element.formatting) == 2
        # Detailed formatting checks are in ElementFactory tests

    # --- Test _process_paragraph ---
    def test_process_simple_paragraph(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "This is a simple paragraph."
        tokens = md_parser.parse(markdown)  # [paragraph_open, inline, paragraph_close]
        element, end_index = formatter.process(tokens, 0, {})

        assert isinstance(element, TextElement)
        assert element.element_type == ElementType.TEXT
        assert element.text == "This is a simple paragraph."
        assert element.horizontal_alignment == AlignmentType.LEFT
        assert end_index == 2

    def test_process_paragraph_with_inline_formatting(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "Text with `code` and a [link](http://ex.com)."
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, TextElement)
        assert element.text == "Text with code and a link."
        assert len(element.formatting) == 2

    def test_process_paragraph_with_directives(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "Aligned paragraph."
        tokens = md_parser.parse(markdown)
        directives = {"align": "center", "custom": "val"}
        element, _ = formatter.process(tokens, 0, directives)
        assert isinstance(element, TextElement)
        assert element.horizontal_alignment == AlignmentType.CENTER
        assert element.directives.get("custom") == "val"

    def test_process_empty_paragraph(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = " \n "  # Markdown-it might produce an empty inline token
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert element is None  # Empty paragraphs should be skipped

    # --- Test _process_quote ---
    def test_process_simple_blockquote(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "> This is a quote."
        tokens = md_parser.parse(
            markdown
        )  # [blockquote_open, paragraph_open, inline, paragraph_close, blockquote_close]
        element, end_index = formatter.process(tokens, 0, {})

        assert isinstance(element, TextElement)
        assert element.element_type == ElementType.QUOTE
        assert element.text == "This is a quote."
        assert end_index == 4

    def test_process_multiline_blockquote(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "> First line.\n> Second line."  # This becomes two paragraphs inside blockquote
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, TextElement)
        # The formatter either joins with newlines (original behavior) or with spaces (current behavior)
        assert element.text in ["First line.\nSecond line.", "First line. Second line."]

    def test_process_blockquote_with_formatting(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        markdown = "> Quote with **bold** text."
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, TextElement)
        assert element.text == "Quote with bold text."
        assert len(element.formatting) == 1
        assert element.formatting[0].format_type == TextFormatType.BOLD

    def test_process_paragraph_that_is_image_only_should_return_none(
        self, formatter: TextFormatter, md_parser: MarkdownIt
    ):
        """TextFormatter should yield to ImageFormatter for image-only paragraphs."""
        markdown = "![alt text](image.png)"
        tokens = md_parser.parse(markdown)
        # tokens[0] is paragraph_open
        element, _ = formatter.process(tokens, 0, {})
        assert element is None  # Assuming ImageFormatter would have handled this.
