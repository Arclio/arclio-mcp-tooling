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

        # FIXED: Parse the entire line content first to extract trailing directives
        # that should apply to image elements per task requirements
        full_content = inline_token.content or ""
        line_cleaned, line_directives = self.directive_parser.parse_and_strip_from_text(
            full_content
        )

        elements: list[Element] = []
        text_tokens = []  # Collect text-related tokens for processing together

        for child_token in inline_token.children:
            if child_token.type == "image":
                # Process any accumulated text tokens first
                if text_tokens:
                    text_element = self._create_text_element_from_tokens(
                        text_tokens, directives
                    )
                    if text_element:
                        elements.append(text_element)
                    text_tokens = []

                # Extract alt text and any directives within it
                alt_text_raw = "".join(c.content for c in child_token.children)
                alt_text, alt_directives = (
                    self.directive_parser.parse_and_strip_from_text(alt_text_raw)
                )

                # FIXED: Merge section directives, line directives, and alt text directives
                # Line directives (trailing directives) take precedence per task specification
                final_image_directives = {
                    **directives,
                    **alt_directives,
                    **line_directives,
                }

                image_element = self.element_factory.create_image_element(
                    url=child_token.attrs.get("src", ""),
                    alt_text=alt_text,
                    directives=final_image_directives,
                )
                elements.append(image_element)
            else:
                # Collect all text-related tokens (text, formatting, etc.)
                text_tokens.append(child_token)

        # Process remaining text tokens
        if text_tokens:
            text_element = self._create_text_element_from_tokens(
                text_tokens, directives
            )
            if text_element:
                elements.append(text_element)

        return elements, close_index

    def _create_text_element_from_tokens(
        self, text_tokens: list[Token], directives: dict[str, Any]
    ) -> Element | None:
        """Create a text element from a list of inline tokens, preserving formatting."""
        if not text_tokens:
            return None

        # Extract plain text and formatting from the tokens
        plain_text = ""
        formatting_data = []
        active_formats = []

        for token in text_tokens:
            token_type = getattr(token, "type", "")

            if token_type == "text":
                plain_text += token.content
            elif token_type == "code_inline":
                start_pos = len(plain_text)
                code_content = token.content
                plain_text += code_content
                if code_content.strip():
                    from markdowndeck.models import TextFormat, TextFormatType

                    formatting_data.append(
                        TextFormat(
                            start=start_pos,
                            end=start_pos + len(code_content),
                            format_type=TextFormatType.CODE,
                        )
                    )
            elif token_type in ["softbreak", "hardbreak"]:
                plain_text += "\n"
            elif token_type.endswith("_open"):
                base_type = token_type.split("_")[0]
                format_type_enum = None
                value: Any = True
                if base_type == "strong":
                    from markdowndeck.models import TextFormatType

                    format_type_enum = TextFormatType.BOLD
                elif base_type == "em":
                    from markdowndeck.models import TextFormatType

                    format_type_enum = TextFormatType.ITALIC
                elif base_type == "s":
                    from markdowndeck.models import TextFormatType

                    format_type_enum = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    from markdowndeck.models import TextFormatType

                    format_type_enum = TextFormatType.LINK
                    value = (
                        token.attrs.get("href", "") if hasattr(token, "attrs") else ""
                    )
                if format_type_enum:
                    active_formats.append((format_type_enum, len(plain_text), value))
            elif token_type.endswith("_close"):
                base_type = token_type.split("_")[0]
                expected_format_type = None
                if base_type == "strong":
                    from markdowndeck.models import TextFormatType

                    expected_format_type = TextFormatType.BOLD
                elif base_type == "em":
                    from markdowndeck.models import TextFormatType

                    expected_format_type = TextFormatType.ITALIC
                elif base_type == "s":
                    from markdowndeck.models import TextFormatType

                    expected_format_type = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    from markdowndeck.models import TextFormatType

                    expected_format_type = TextFormatType.LINK
                for i in range(len(active_formats) - 1, -1, -1):
                    fmt_type, start_pos, fmt_value = active_formats[i]
                    if fmt_type == expected_format_type:
                        if start_pos < len(plain_text):
                            from markdowndeck.models import TextFormat

                            formatting_data.append(
                                TextFormat(
                                    start=start_pos,
                                    end=len(plain_text),
                                    format_type=fmt_type,
                                    value=fmt_value,
                                )
                            )
                        active_formats.pop(i)
                        break

        if not plain_text.strip():
            return None

        # FIXED: Parse directives from the text content to support element-scoped directives
        cleaned_text, line_directives = self.directive_parser.parse_and_strip_from_text(
            plain_text
        )

        # Merge section directives with any element-specific directives found in the text
        final_directives = {**directives, **line_directives}

        # Use the cleaned text (with directives removed) but keep the extracted formatting
        alignment = AlignmentType(final_directives.get("align", "left"))
        return self.element_factory.create_text_element(
            cleaned_text if cleaned_text.strip() else plain_text,
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
