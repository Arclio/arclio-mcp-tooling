import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import (
    AlignmentType,
    Element,
    TextElement,
    TextFormat,
)
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive.directive_parser import DirectiveParser

logger = logging.getLogger(__name__)


class TextFormatter(BaseFormatter):
    """
    Formatter for text elements with enhanced directive handling.
    """

    def __init__(self, element_factory, directive_parser: DirectiveParser = None):
        """Initialize the TextFormatter with required dependencies."""
        super().__init__(element_factory)
        opts = {"html": False, "typographer": True, "linkify": True, "breaks": True}
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")
        self.directive_parser = directive_parser or DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in ["heading_open", "blockquote_open", "paragraph_open"]

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[list[Element], int]:
        """Process tokens into text elements with improved directive handling."""
        if not tokens or start_index >= len(tokens):
            return [], start_index

        token = tokens[start_index]
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        if token.type == "heading_open":
            element, end_idx = self._process_heading(
                tokens, start_index, merged_directives, **kwargs
            )
            return [element] if element else [], end_idx
        if token.type == "paragraph_open":
            return self._process_paragraph(tokens, start_index, merged_directives)
        if token.type == "blockquote_open":
            element, end_idx = self._process_quote(
                tokens, start_index, merged_directives
            )
            return [element] if element else [], end_idx

        logger.warning(f"TextFormatter cannot process token type: {token.type}")
        return [], start_index

    def _process_heading(
        self,
        tokens: list[Token],
        start_index: int,
        directives: dict[str, Any],
        is_section_heading: bool = False,
        is_subtitle: bool = False,
    ) -> tuple[TextElement | None, int]:
        open_token = tokens[start_index]
        level = int(open_token.tag[1])
        end_idx = self.find_closing_token(tokens, start_index, "heading_close")
        inline_token_index = start_index + 1
        if (
            inline_token_index >= len(tokens)
            or tokens[inline_token_index].type != "inline"
        ):
            return None, end_idx
        inline_token = tokens[inline_token_index]
        raw_content = inline_token.content or ""
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            raw_content
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)
        if not text_content:
            return None, end_idx
        final_directives.setdefault("heading_level", level)
        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_text_element(
            text_content, formatting, alignment, final_directives
        )
        logger.debug(
            f"Created heading element: {element.element_type}, text: '{text_content[:30]}'"
        )
        return element, end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """Processes a paragraph, handling mixed content like images and text."""
        inline_index = start_index + 1
        if inline_index >= len(tokens) or tokens[inline_index].type != "inline":
            return [], start_index + 1

        inline_token = tokens[inline_index]
        close_index = self.find_closing_token(tokens, start_index, "paragraph_close")

        if not hasattr(inline_token, "children") or not inline_token.children:
            return [], close_index

        elements: list[Element] = []
        child_tokens = inline_token.children
        i = 0
        while i < len(child_tokens):
            child_token = child_tokens[i]

            if child_token.type == "image":
                # Extract alt text and its embedded directives
                alt_text_raw = "".join(c.content for c in child_token.children)
                alt_text, alt_directives = (
                    self.directive_parser.parse_and_strip_from_text(alt_text_raw)
                )

                # Look ahead for a trailing directive block
                trailing_directives = {}
                next_token_index = i + 1
                if next_token_index < len(child_tokens):
                    next_token = child_tokens[next_token_index]
                    if next_token.type == "text":
                        # Check if this text token contains ONLY directives
                        line_directives, remaining_text = (
                            self.directive_parser.parse_inline_directives(
                                next_token.content
                            )
                        )
                        if line_directives and not remaining_text.strip():
                            trailing_directives = line_directives
                            i += 1  # Consume the directive token

                final_image_directives = {
                    **directives,
                    **alt_directives,
                    **trailing_directives,
                }
                image_element = self.element_factory.create_image_element(
                    url=child_token.attrs.get("src", ""),
                    alt_text=alt_text,
                    directives=final_image_directives,
                )
                elements.append(image_element)

            else:
                # This is likely a block of text. Process until the next image or the end.
                text_chunk_tokens = []
                while i < len(child_tokens) and child_tokens[i].type != "image":
                    text_chunk_tokens.append(child_tokens[i])
                    i += 1
                i -= 1  # Decrement to account for outer loop's increment

                text_element = self._create_text_element_from_tokens(
                    text_chunk_tokens, directives
                )
                if text_element:
                    elements.append(text_element)
            i += 1

        return elements, close_index

    def _create_text_element_from_tokens(
        self, text_tokens: list[Token], directives: dict[str, Any]
    ) -> Element | None:
        """Create a text element from a list of inline tokens, preserving formatting."""
        if not text_tokens:
            return None

        # Create a temporary token to pass to the element factory's helpers
        temp_inline_token = Token("inline", "", 0)
        temp_inline_token.children = text_tokens
        temp_inline_token.content = "".join(
            t.content for t in text_tokens if hasattr(t, "content")
        )

        plain_text = self._get_plain_text_from_inline_token(temp_inline_token)

        if not plain_text.strip():
            return None

        formatting_data = self.element_factory._extract_formatting_from_inline_token(
            temp_inline_token
        )

        # Parse directives from the text content itself
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            plain_text
        )

        final_directives = {**directives, **line_directives}
        alignment = AlignmentType(final_directives.get("align", "left"))

        return self.element_factory.create_text_element(
            cleaned_text.strip(),
            formatting_data,
            alignment,
            final_directives,
        )

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[TextElement | None, int]:
        end_idx = self.find_closing_token(tokens, start_index, "blockquote_close")
        text_parts = []
        i = start_index + 1
        while i < end_idx:
            if tokens[i].type == "paragraph_open":
                para_inline_idx = i + 1
                if (
                    para_inline_idx < end_idx
                    and tokens[para_inline_idx].type == "inline"
                ):
                    text_parts.append(tokens[para_inline_idx].content)
                i = self.find_closing_token(tokens, i, "paragraph_close")
            i += 1
        full_text = "\n".join(text_parts)
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            full_text
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)
        if not text_content:
            return None, end_idx
        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_quote_element(
            text_content, formatting, alignment, final_directives
        )
        return element, end_idx

    def _extract_clean_text_and_formatting(
        self, cleaned_text: str
    ) -> tuple[str, list[TextFormat]]:
        if not cleaned_text.strip():
            return "", []

        tokens = self.md.parse(cleaned_text.strip())

        for token in tokens:
            if token.type == "inline":
                plain_text = self._get_plain_text_from_inline_token(token)
                formatting = self.element_factory._extract_formatting_from_inline_token(
                    token
                )
                return plain_text, formatting

        return cleaned_text.strip(), []
