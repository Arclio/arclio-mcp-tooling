"""Text formatter for content parsing with improved directive handling."""

import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import (
    AlignmentType,
    Element,
    ElementType,
    TextElement,
    TextFormat,
)
from markdowndeck.models.constants import TextFormatType
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class TextFormatter(BaseFormatter):
    """
    Formatter for text elements with enhanced directive handling.

    CRITICAL FIXES:
    - P0: Properly removes directives from final text content
    - P4: Supports directives on same line as text content
    """

    def __init__(self, element_factory, directive_parser: DirectiveParser = None):
        """Initialize the TextFormatter with required dependencies."""
        super().__init__(element_factory)

        # Initialize MarkdownIt for formatting extraction
        opts = {
            "html": False,
            "typographer": True,
            "linkify": True,
            "breaks": True,
        }
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

        # ARCHITECTURAL IMPROVEMENT P5: Use injected DirectiveParser
        self.directive_parser = directive_parser or DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        if token.type in ["heading_open", "blockquote_open"]:
            return True

        if token.type == "paragraph_open":
            # Skip image-only paragraphs (let ImageFormatter handle them)
            if len(leading_tokens) > 1 and leading_tokens[1].type == "inline":
                inline_children = getattr(leading_tokens[1], "children", [])
                if inline_children:
                    image_children = [
                        child for child in inline_children if child.type == "image"
                    ]
                    other_content = [
                        child
                        for child in inline_children
                        if child.type != "image"
                        and (child.type != "text" or child.content.strip())
                    ]
                    if len(image_children) > 0 and not other_content:
                        return False
            return True

        return False

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[Element | None, int]:
        """Process tokens into text elements with improved directive handling."""
        if not tokens or start_index >= len(tokens):
            return None, start_index

        token = tokens[start_index]
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        if token.type == "heading_open":
            return self._process_heading(
                tokens, start_index, merged_directives, **kwargs
            )
        if token.type == "paragraph_open":
            return self._process_paragraph(tokens, start_index, merged_directives)
        if token.type == "blockquote_open":
            return self._process_quote(tokens, start_index, merged_directives)

        logger.warning(f"TextFormatter cannot process token type: {token.type}")
        return None, start_index

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

        inline_token_index = start_index + 1
        if (
            inline_token_index >= len(tokens)
            or tokens[inline_token_index].type != "inline"
        ):
            end_idx = self.find_closing_token(tokens, start_index, "heading_close")
            return None, end_idx

        inline_token = tokens[inline_token_index]

        # CRITICAL FIX P0: Use cleaned text content
        text_content, formatting = self._extract_clean_text_and_formatting(inline_token)

        end_idx = self.find_closing_token(tokens, start_index, "heading_close")

        # Determine element type based on heading analysis
        if level == 1:
            element_type = ElementType.TITLE
            default_alignment = AlignmentType.CENTER
        elif is_subtitle or (level == 2 and not is_section_heading):
            element_type = ElementType.SUBTITLE
            default_alignment = AlignmentType.CENTER
        else:
            element_type = ElementType.TEXT
            default_alignment = AlignmentType.LEFT
            # Add styling for section headings
            if level == 2:
                directives.setdefault("fontsize", 18)
                directives.setdefault("margin_bottom", 10)
            elif level == 3:
                directives.setdefault("fontsize", 16)
                directives.setdefault("margin_bottom", 8)

        # Get alignment from directives
        horizontal_alignment = AlignmentType(
            directives.get("align", default_alignment.value)
        )

        # Create appropriate element
        if element_type == ElementType.TITLE:
            element = self.element_factory.create_title_element(
                title=text_content, formatting=formatting, directives=directives.copy()
            )
        elif element_type == ElementType.SUBTITLE:
            element = self.element_factory.create_subtitle_element(
                text=text_content,
                formatting=formatting,
                alignment=horizontal_alignment,
                directives=directives.copy(),
            )
        else:
            element = self.element_factory.create_text_element(
                text=text_content,
                formatting=formatting,
                alignment=horizontal_alignment,
                directives=directives.copy(),
            )

        logger.debug(
            f"Created heading element: {element_type}, text: '{text_content[:30]}'"
        )
        return element, end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        """
        Process paragraph tokens with enhanced directive handling.

        CRITICAL FIXES:
        - P0: Ensures directives are removed from final text content
        - P4: Supports directives at beginning of paragraph text
        """
        inline_index = start_index + 1
        if inline_index >= len(tokens) or tokens[inline_index].type != "inline":
            return None, start_index + 1

        inline_token = tokens[inline_index]
        raw_content = inline_token.content or ""

        # CRITICAL FIX P0 & P4: Extract and remove directives from text
        element_directives, cleaned_content = (
            self._extract_element_directives_from_text(raw_content)
        )
        final_directives = self.merge_directives(directives, element_directives)

        # Skip image-only paragraphs
        if self._is_image_only_paragraph(inline_token):
            close_index = self._find_paragraph_close(tokens, inline_index)
            return None, close_index

        # CRITICAL FIX: Determine text extraction approach based on directive source
        # - If directives were found in the same paragraph text → preserve markdown syntax
        # - If directives came from preceding paragraphs (consumed by content parser) → extract plain text
        has_same_line_directives = bool(element_directives)
        bool(directives) and not has_same_line_directives

        if cleaned_content.strip():
            # Use cleaned content for text extraction when directives were found
            if has_same_line_directives:
                # Extract plain text from cleaned content
                text_content, formatting = (
                    self._extract_plain_text_from_cleaned_content(
                        cleaned_content, inline_token
                    )
                )
            else:
                # Use standard plain text extraction for consistency
                text_content, formatting = self._extract_clean_text_and_formatting(
                    inline_token
                )
        else:
            # CRITICAL FIX: If cleaned content is empty after directive extraction,
            # the paragraph contains only directives and should be ignored
            if has_same_line_directives:
                close_index = self._find_paragraph_close(tokens, inline_index)
                return None, close_index

            # Use original token processing if no directives were found within text
            # Use plain text extraction for standard cases
            text_content, formatting = self._extract_clean_text_and_formatting(
                inline_token
            )

        # Skip empty paragraphs
        if not text_content.strip():
            close_index = self._find_paragraph_close(tokens, inline_index)
            return None, close_index

        # Apply alignment from directives
        alignment = AlignmentType.LEFT
        if "align" in final_directives:
            align_value = final_directives["align"]
            if isinstance(align_value, str) and align_value.lower() in [
                "left",
                "center",
                "right",
                "justify",
            ]:
                alignment = AlignmentType(align_value.lower())

        element = self.element_factory.create_text_element(
            text=text_content,
            formatting=formatting,
            alignment=alignment,
            directives=final_directives,
        )

        close_index = self._find_paragraph_close(tokens, inline_index)
        logger.debug(
            f"Created text element with cleaned content: '{text_content[:30]}'"
        )
        return element, close_index

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[TextElement | None, int]:
        """Process blockquote tokens."""
        end_idx = self.find_closing_token(tokens, start_index, "blockquote_close")

        quote_text_parts = []
        all_formatting: list[TextFormat] = []
        current_text_len = 0

        i = start_index + 1
        while i < end_idx:
            token_i = tokens[i]
            if token_i.type == "paragraph_open":
                para_inline_idx = i + 1
                if (
                    para_inline_idx < end_idx
                    and tokens[para_inline_idx].type == "inline"
                ):
                    inline_token = tokens[para_inline_idx]

                    # Extract clean text and formatting
                    text_part, part_formatting = (
                        self._extract_clean_text_and_formatting(inline_token)
                    )

                    if quote_text_parts:
                        current_text_len += 1  # for newline
                    quote_text_parts.append(text_part)

                    # Adjust formatting positions
                    for fmt in part_formatting:
                        all_formatting.append(
                            TextFormat(
                                start=fmt.start + current_text_len,
                                end=fmt.end + current_text_len,
                                format_type=fmt.format_type,
                                value=fmt.value,
                            )
                        )
                    current_text_len += len(text_part)

                i = self.find_closing_token(tokens, i, "paragraph_close")
            i += 1

        final_text = "\n".join(quote_text_parts)
        if not final_text.strip():
            return None, end_idx

        alignment = AlignmentType(directives.get("align", AlignmentType.LEFT.value))

        element = self.element_factory.create_quote_element(
            text=final_text,
            formatting=all_formatting,
            alignment=alignment,
            directives=directives.copy(),
        )

        return element, end_idx

    def _extract_element_directives_from_text(
        self, text_content: str
    ) -> tuple[dict[str, Any], str]:
        """
        Extract element-specific directives from text content.

        CRITICAL FIX P4: Enhanced to support directives at start of text lines.
        """
        if not text_content.strip():
            return {}, text_content

        lines = text_content.split("\n")
        all_directives = {}
        content_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                content_lines.append(line)
                continue

            # CRITICAL FIX P4: Enhanced directive parsing
            # First try to parse as directive-only line
            line_directives, remaining_text = (
                self.directive_parser.parse_inline_directives(line_stripped)
            )

            if line_directives and not remaining_text.strip():
                # Pure directive line
                all_directives.update(line_directives)
                logger.debug(f"Extracted directives from line: {line_directives}")
            else:
                # Check if line starts with directives followed by text (P4 enhancement)
                start_directives, clean_line = self._extract_line_start_directives(
                    line_stripped
                )
                if start_directives:
                    all_directives.update(start_directives)
                    content_lines.append(clean_line if clean_line else "")
                    logger.debug(
                        f"Extracted start-of-line directives: {start_directives}"
                    )
                else:
                    content_lines.append(line)

        cleaned_text = "\n".join(content_lines)
        return all_directives, cleaned_text

    def _extract_line_start_directives(self, line: str) -> tuple[dict[str, Any], str]:
        """
        Extract directives from the start of a line, leaving remaining text.

        ENHANCEMENT P4: Support for '[directive=value]Text content' format.
        """
        import re

        # Pattern to match directives at the start of a line
        directive_pattern = r"^(\s*(?:\[[^\[\]]+=[^\[\]]*\]\s*)+)"
        match = re.match(directive_pattern, line)

        if not match:
            return {}, line

        directive_text = match.group(1)
        remaining_text = line[len(directive_text) :].strip()

        # Parse the directive text
        directives, _ = self.directive_parser.parse_inline_directives(
            directive_text.strip()
        )

        return directives, remaining_text

    def _extract_clean_text_and_formatting(
        self, inline_token: Token
    ) -> tuple[str, list[TextFormat]]:
        """
        Extract clean text content and formatting from an inline token.

        ARCHITECTURAL IMPROVEMENT: Centralized text extraction method.
        """
        text_content = self._get_plain_text_from_inline_token(inline_token)
        formatting = self.element_factory._extract_formatting_from_inline_token(
            inline_token
        )
        return text_content, formatting

    def _extract_text_from_cleaned_content(
        self, cleaned_content: str, original_token: Token
    ) -> tuple[str, list[TextFormat]]:
        """
        Extract text and formatting from cleaned content.

        CRITICAL FIX P0: Process cleaned content to preserve markdown syntax
        while extracting proper formatting information.
        """
        if not cleaned_content.strip():
            return "", []

        # Parse the cleaned content to get tokens for proper formatting extraction
        tokens = self.md.parse(cleaned_content.strip())

        # Find the inline token from the parsed content
        for token in tokens:
            if token.type == "inline":
                # CRITICAL FIX: Preserve the original markdown content instead of extracting plain text
                # The cleaned_content already has directives removed, so use it directly
                text_content = cleaned_content.strip()

                # Extract formatting information with positions relative to the original markdown text
                formatting = self._extract_formatting_with_markdown_positions(
                    token, text_content
                )
                return text_content, formatting

        # Fallback: if no inline token found, return the content as-is
        # This shouldn't happen for normal paragraph content, but provides safety
        formatting = self.element_factory.extract_formatting_from_text(
            cleaned_content, self.md
        )
        return cleaned_content, formatting

    def _extract_formatting_with_markdown_positions(
        self, token: Token, markdown_text: str
    ) -> list[TextFormat]:
        """
        Extract formatting with positions relative to plain text content.

        This method preserves markdown syntax in the text content but calculates
        formatting positions relative to the plain text (without markdown syntax).
        """
        if token.type != "inline" or not hasattr(token, "children"):
            return []

        formatting_data = []
        active_formats = []

        # Track position in plain text (for formatting positions)
        plain_text_pos = 0

        for child in token.children:
            child_type = getattr(child, "type", "")

            if child_type == "text":
                # Move position forward by the text content length
                plain_text_pos += len(child.content)

            elif child_type == "code_inline":
                # For code spans, formatting positions should cover the content without backticks
                code_start = plain_text_pos
                plain_text_pos += len(child.content)
                formatting_data.append(
                    TextFormat(
                        start=code_start,
                        end=plain_text_pos,
                        format_type=TextFormatType.CODE,
                        value=True,
                    )
                )

            elif child_type in ["softbreak", "hardbreak"]:
                plain_text_pos += 1  # For newlines

            elif child_type.endswith("_open"):
                base_type = child_type.split("_")[0]
                format_type_enum = None
                value = True

                if base_type == "strong":
                    format_type_enum = TextFormatType.BOLD
                elif base_type == "em":
                    format_type_enum = TextFormatType.ITALIC
                elif base_type == "s":
                    format_type_enum = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    format_type_enum = TextFormatType.LINK
                    value = (
                        child.attrs.get("href", "") if hasattr(child, "attrs") else ""
                    )

                if format_type_enum:
                    # Record the start position in plain text coordinates
                    active_formats.append((format_type_enum, plain_text_pos, value))

            elif child_type.endswith("_close"):
                base_type = child_type.split("_")[0]
                expected_format_type = None

                if base_type == "strong":
                    expected_format_type = TextFormatType.BOLD
                elif base_type == "em":
                    expected_format_type = TextFormatType.ITALIC
                elif base_type == "s":
                    expected_format_type = TextFormatType.STRIKETHROUGH
                elif base_type == "link":
                    expected_format_type = TextFormatType.LINK

                # Find and close matching format
                for i in range(len(active_formats) - 1, -1, -1):
                    fmt_type, start_pos, fmt_value = active_formats[i]
                    if fmt_type == expected_format_type:
                        formatting_data.append(
                            TextFormat(
                                start=start_pos,
                                end=plain_text_pos,
                                format_type=fmt_type,
                                value=fmt_value,
                            )
                        )
                        active_formats.pop(i)
                        break

        return formatting_data

    def _is_image_only_paragraph(self, inline_token: Token) -> bool:
        """Check if paragraph contains only images."""
        if not hasattr(inline_token, "children") or not inline_token.children:
            return False

        image_children = [
            child for child in inline_token.children if child.type == "image"
        ]
        non_image_content = [
            child
            for child in inline_token.children
            if child.type not in ["image", "softbreak"]
            and not (child.type == "text" and not child.content.strip())
        ]

        return len(image_children) > 0 and len(non_image_content) == 0

    def _find_paragraph_close(self, tokens: list[Token], inline_index: int) -> int:
        """Find the closing paragraph token."""
        close_index = inline_index + 1
        while (
            close_index < len(tokens) and tokens[close_index].type != "paragraph_close"
        ):
            close_index += 1
        return close_index

    def _extract_plain_text_from_cleaned_content(
        self, cleaned_content: str, original_token: Token
    ) -> tuple[str, list[TextFormat]]:
        """
        Extract plain text and formatting from cleaned content.

        This method extracts plain text (without markdown syntax) from cleaned content
        while preserving proper formatting information.
        """
        if not cleaned_content.strip():
            return "", []

        # Parse the cleaned content to get tokens for proper formatting extraction
        tokens = self.md.parse(cleaned_content.strip())

        # Find the inline token from the parsed content
        for token in tokens:
            if token.type == "inline":
                # Extract plain text from the cleaned content token
                text_content = self._get_plain_text_from_inline_token(token)

                # Extract formatting information from the cleaned content token
                formatting = self.element_factory._extract_formatting_from_inline_token(
                    token
                )
                return text_content, formatting

        # Fallback: if no inline token found, return the content as-is
        # This shouldn't happen for normal paragraph content, but provides safety
        return cleaned_content.strip(), []
