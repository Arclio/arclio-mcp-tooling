import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import AlignmentType, Element, TextFormat
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

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
                tokens, start_index, merged_directives
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
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        # FIXED: This method is now more robust to prevent content loss.
        # A heading block is guaranteed by markdown-it to be three tokens:
        # heading_open, inline, heading_close. We explicitly use this structure
        # to determine the end index, preventing the formatter from consuming
        # subsequent content blocks.
        open_token = tokens[start_index]
        level = int(open_token.tag[1:])
        end_idx = start_index + 2

        # Defensive check in case of a malformed token stream.
        if (
            end_idx >= len(tokens)
            or tokens[end_idx].type != "heading_close"
            or tokens[start_index + 1].type != "inline"
        ):
            logger.warning(
                f"Unexpected token structure for heading at index {start_index}. Using generic token finder as fallback."
            )
            end_idx = self.find_closing_token(tokens, start_index, "heading_close")

        inline_token = tokens[start_index + 1]
        raw_content = inline_token.content or ""
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            raw_content
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)

        if not text_content:
            return None, end_idx

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_text_element(
            text_content,
            formatting,
            alignment,
            final_directives,
            heading_level=level,
        )
        return element, end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """
        Processes a paragraph, correctly handling mixed content like images and captions.
        """
        inline_token = tokens[start_index + 1]
        close_index = self.find_closing_token(tokens, start_index, "paragraph_close")

        if not hasattr(inline_token, "children") or not inline_token.children:
            return [], close_index

        elements: list[Element] = []
        child_tokens = inline_token.children

        i = 0
        while i < len(child_tokens):
            buffer = []
            while i < len(child_tokens) and child_tokens[i].type != "image":
                buffer.append(child_tokens[i])
                i += 1

            if buffer:
                text_element = self._create_text_element_from_tokens(buffer, directives)
                if text_element:
                    elements.append(text_element)

            if i < len(child_tokens):
                image_token = child_tokens[i]
                i += 1

                img_alt, img_src = image_token.content, image_token.attrs.get("src", "")
                alt_text, img_directives = (
                    self.directive_parser.parse_and_strip_from_text(img_alt)
                )

                if i < len(child_tokens) and child_tokens[i].type == "text":
                    next_child = child_tokens[i]
                    cleaned_text, next_directives = (
                        self.directive_parser.parse_and_strip_from_text(
                            next_child.content
                        )
                    )
                    if next_directives:
                        img_directives.update(next_directives)
                    next_child.content = cleaned_text

                final_directives = {**directives, **img_directives}
                image_element = self.element_factory.create_image_element(
                    url=img_src, alt_text=alt_text, directives=final_directives
                )
                elements.append(image_element)

        return elements, close_index

    def _create_text_element_from_tokens(
        self, text_tokens: list[Token], directives: dict[str, Any]
    ) -> Element | None:
        """
        Create a text element from a list of inline tokens.
        """
        final_text_parts = []
        final_directives = directives.copy()

        for child in text_tokens:
            if child.type in ["softbreak", "hardbreak"]:
                final_text_parts.append("\n")
            elif child.type == "code_inline":
                final_text_parts.append(f"`{child.content}`")
            elif hasattr(child, "content"):
                cleaned_content, line_directives = (
                    self.directive_parser.parse_and_strip_from_text(child.content)
                )
                final_text_parts.append(cleaned_content)
                final_directives.update(line_directives)

        full_cleaned_text = "".join(final_text_parts)
        text_content, formatting_data = self._extract_clean_text_and_formatting(
            full_cleaned_text
        )

        if not text_content:
            return None

        alignment = AlignmentType(final_directives.get("align", "left"))
        return self.element_factory.create_text_element(
            text_content, formatting_data, alignment, final_directives
        )

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
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
