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
        """Process heading tokens with proper classification."""
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

        # REFACTORED: Use centralized parser to strip directives from anywhere in the line.
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            raw_content
        )
        final_directives = {**directives, **line_directives}

        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)

        if not text_content:
            return None, end_idx

        if level == 1:
            element = self.element_factory.create_title_element(
                text_content, formatting, final_directives
            )
        elif is_subtitle or (level == 2 and not is_section_heading):
            alignment = AlignmentType(final_directives.get("align", "center"))
            element = self.element_factory.create_subtitle_element(
                text_content, formatting, alignment, final_directives
            )
        else:
            final_directives.setdefault("fontsize", {2: 18, 3: 16}.get(level, 14))
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
        text_buffer = ""

        for child_token in inline_token.children:
            if child_token.type == "image":
                # If there's pending text, process it first
                if text_buffer.strip():
                    elements.extend(
                        self._create_text_elements_from_buffer(text_buffer, directives)
                    )
                    text_buffer = ""

                # Process the image
                image_element = self.element_factory.create_image_element(
                    url=child_token.attrs.get("src", ""),
                    alt_text="".join(c.content for c in child_token.children),
                    directives=directives,  # Directives from section apply
                )
                elements.append(image_element)
            else:
                text_buffer += child_token.content

        # Process any remaining text in the buffer
        if text_buffer.strip():
            elements.extend(
                self._create_text_elements_from_buffer(text_buffer, directives)
            )

        return elements, close_index

    def _create_text_elements_from_buffer(
        self, text_buffer: str, directives: dict[str, Any]
    ) -> list[Element]:
        """Creates a text element from a buffer, stripping directives."""
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            text_buffer
        )

        if not cleaned_text.strip():
            # If only directives were in the buffer, apply them to the last element if possible
            # This handles `![img](...)\n[width=100]`
            # For simplicity, this is not implemented here to avoid statefulness.
            # The recommended pattern is `![img](...) [width=100]` on the same line.
            return []

        final_directives = {**directives, **line_directives}
        text_content, formatting = self._extract_clean_text_and_formatting(cleaned_text)

        if not text_content:
            return []

        alignment = AlignmentType(final_directives.get("align", "left"))
        element = self.element_factory.create_text_element(
            text_content, formatting, alignment, final_directives
        )
        return [element]

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[TextElement | None, int]:
        """Process blockquote tokens."""
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
        """Extracts formatting from a pre-cleaned text string."""
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
