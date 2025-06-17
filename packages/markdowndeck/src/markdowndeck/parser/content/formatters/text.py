import logging
import re
import textwrap
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

        # REFACTORED: Disabled 'lheading' and 'hr' rules to ensure separators are treated as plain text.
        self.md.disable(["lheading", "hr"])

        self.directive_parser = directive_parser or DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in [
            "heading_open",
            "blockquote_open",
            "paragraph_open",
            "hr",
            "code_block",
        ]

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
            elements, end_index = self._process_heading(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "paragraph_open":
            elements, end_index = self._process_paragraph(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "blockquote_open":
            elements, end_index = self._process_quote(
                tokens, start_index, merged_directives
            )
            return elements, end_index
        if token.type == "hr":
            hr_text = getattr(token, "markup", "---")
            element = self.element_factory.create_text_element(
                hr_text, [], AlignmentType.LEFT, merged_directives
            )
            return [element], start_index
        if token.type == "code_block":
            raw_content = token.content
            dedented_content = textwrap.dedent(raw_content).strip()

            text_content, formatting = self._extract_clean_text_and_formatting(
                dedented_content
            )

            if not text_content:
                return [], start_index

            element = self.element_factory.create_text_element(
                text_content, formatting, AlignmentType.LEFT, merged_directives
            )
            return [element], start_index

        logger.warning(f"TextFormatter cannot process token type: {token.type}")
        return [], start_index

    def _process_heading(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        open_token = tokens[start_index]
        level = int(open_token.tag[1:])
        end_idx = self.find_closing_token(tokens, start_index, "heading_close")
        inline_token = tokens[start_index + 1]
        raw_content = inline_token.content or ""

        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            raw_content
        )
        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)

        if not text_content:
            return [], end_idx

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_text_element(
            text_content,
            formatting,
            alignment,
            final_directives,
            heading_level=level,
        )
        return [element] if element else [], end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
        """
        REFACTORED: Processes a paragraph by iterating through its inline children,
        correctly handling mixed content (text/images/headings) and splitting by newlines.
        """
        inline_token = tokens[start_index + 1]
        close_index = self.find_closing_token(tokens, start_index, "paragraph_close")

        child_tokens = inline_token.children or []
        if not child_tokens:
            return [], close_index

        elements: list[Element] = []
        chunk_buffer: list[Token] = []

        def process_buffer():
            if chunk_buffer:
                element = self._create_text_element_from_tokens(
                    chunk_buffer, directives
                )
                if element:
                    elements.append(element)
                chunk_buffer.clear()

        i = 0
        while i < len(child_tokens):
            child = child_tokens[i]
            if child.type == "image":
                process_buffer()
                img_alt, img_src = child.content, child.attrs.get("src", "")
                final_img_directives = directives.copy()
                if i + 1 < len(child_tokens) and child_tokens[i + 1].type == "text":
                    next_token = child_tokens[i + 1]
                    remaining_text, parsed_directives = (
                        self.directive_parser.parse_and_strip_from_text(
                            next_token.content
                        )
                    )
                    if parsed_directives:
                        final_img_directives.update(parsed_directives)
                        next_token.content = remaining_text.lstrip()
                cleaned_alt, alt_directives = (
                    self.directive_parser.parse_and_strip_from_text(img_alt)
                )
                final_img_directives.update(alt_directives)
                image_element = self.element_factory.create_image_element(
                    url=img_src, alt_text=cleaned_alt, directives=final_img_directives
                )
                elements.append(image_element)
            elif child.type in ["softbreak", "hardbreak"]:
                process_buffer()
            else:
                chunk_buffer.append(child)
            i += 1
        process_buffer()
        return elements, close_index

    def _create_text_element_from_tokens(
        self,
        text_tokens: list[Token],
        directives: dict[str, Any],
    ) -> Element | None:
        """
        Creates a single TextElement from a buffer of inline child tokens.
        """
        temp_inline_token = Token("inline", "", 0, children=text_tokens)
        full_raw_text = self._get_plain_text_from_inline_token(temp_inline_token)

        if not full_raw_text.strip():
            return None

        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            full_raw_text
        )
        final_directives = {**directives, **line_directives}

        heading_level = None
        heading_match = re.match(r"^(#+)\s", cleaned_text)
        if heading_match:
            heading_level = len(heading_match.group(1))
            cleaned_text = cleaned_text[len(heading_match.group(0)) :]

        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)
        if not text_content:
            return None

        alignment = AlignmentType(final_directives.get("align", "left"))
        return self.element_factory.create_text_element(
            text_content, formatting, alignment, final_directives, heading_level
        )

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[list[Element], int]:
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
            return [], end_idx

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_quote_element(
            text_content, formatting, alignment, final_directives
        )
        return [element] if element else [], end_idx

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
