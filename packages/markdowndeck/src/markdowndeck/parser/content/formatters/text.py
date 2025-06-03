"""Text formatter for content parsing (paragraphs, headings, blockquotes)."""

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

# ElementFactory injected via BaseFormatter
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class TextFormatter(BaseFormatter):
    """Formatter for text elements (headings, paragraphs, quotes)."""

    def __init__(self, element_factory):
        """Initialize the TextFormatter with a MarkdownIt instance."""
        super().__init__(element_factory)
        # Create a local MarkdownIt instance for formatting extraction
        opts = {
            "html": False,
            "typographer": True,
            "linkify": True,
            "breaks": True,
        }
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        if token.type in ["heading_open", "blockquote_open"]:
            return True
        if token.type == "paragraph_open":
            # Check if it's NOT an image-only paragraph.
            # This relies on ImageFormatter running first and "consuming" image-only paragraphs.
            if len(leading_tokens) > 1 and leading_tokens[1].type == "inline":  # leading_tokens[0] is current token
                inline_children = getattr(leading_tokens[1], "children", [])
                if inline_children:
                    image_children = [child for child in inline_children if child.type == "image"]
                    other_content = [
                        child
                        for child in inline_children
                        if child.type != "image" and (child.type != "text" or child.content.strip())
                    ]
                    if len(image_children) > 0 and not other_content:
                        return False  # This is an image-only paragraph, ImageFormatter should take it.
            return True  # It's a paragraph, and not clearly image-only from this limited peek.
        return False

    def _extract_element_directives_from_text(self, text_content: str) -> tuple[dict[str, Any], str]:
        """
        Extract element-specific directives from the beginning of text content.

        Args:
            text_content: The raw text content that may start with directive lines

        Returns:
            Tuple of (element_directives, cleaned_text) where:
            - element_directives: Dictionary of parsed directives found at the start
            - cleaned_text: The text content with directive lines removed
        """
        if not text_content.strip():
            return {}, text_content

        lines = text_content.split("\n")
        directive_lines = []
        content_start_index = 0

        # Check each line from the beginning to see if it contains only directives
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                # Empty line - continue checking
                content_start_index = i + 1
                continue

            parser = DirectiveParser()

            # Try to parse this line as directives
            line_directives, remaining_text = parser.parse_inline_directives(line_stripped)

            if line_directives and not remaining_text:
                # This line contains only directives
                directive_lines.append(line_stripped)
                content_start_index = i + 1
            else:
                # This line contains non-directive content, stop looking
                break

        if not directive_lines:
            # No directive lines found
            return {}, text_content

        # Parse all directive lines to extract directives
        combined_directives = {}
        for directive_line in directive_lines:
            parser = DirectiveParser()
            line_directives, _ = parser.parse_inline_directives(directive_line)
            combined_directives.update(line_directives)

        # Reconstruct the text content without the directive lines
        remaining_lines = lines[content_start_index:]
        cleaned_text = "\n".join(remaining_lines)

        logger.debug(f"Extracted element directives: {combined_directives}")
        logger.debug(f"Cleaned text content: {repr(cleaned_text[:100])}")

        return combined_directives, cleaned_text

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[Element | None, int]:
        # Add guard clause for empty tokens
        if not tokens or start_index >= len(tokens):
            logger.debug(f"TextFormatter received empty tokens or invalid start_index {start_index}.")
            return None, start_index

        token = tokens[start_index]

        # Merge section and element-specific directives
        merged_directives = self.merge_directives(section_directives, element_specific_directives)

        if token.type == "heading_open":
            # Pass any additional kwargs to _process_heading
            return self._process_heading(tokens, start_index, merged_directives, **kwargs)
        if token.type == "paragraph_open":
            return self._process_paragraph(tokens, start_index, merged_directives)
        if token.type == "blockquote_open":
            return self._process_quote(tokens, start_index, merged_directives)

        logger.warning(f"TextFormatter cannot process token type: {token.type} at index {start_index}")
        return None, start_index

    def _process_heading(
        self,
        tokens: list[Token],
        start_index: int,
        directives: dict[str, Any],
        is_section_heading: bool = False,
        is_subtitle: bool = False,  # Added parameter
    ) -> tuple[TextElement | None, int]:
        """
        Process a heading token into an appropriate element.

        Args:
            tokens: The list of tokens
            start_index: Starting token index
            directives: Directives to apply
            is_section_heading: Whether this heading is a section-level heading
            is_subtitle: Whether this heading should be a subtitle
        """
        open_token = tokens[start_index]
        level = int(open_token.tag[1])

        inline_token_index = start_index + 1
        if not (inline_token_index < len(tokens) and tokens[inline_token_index].type == "inline"):
            logger.warning(f"No inline content found for heading at index {start_index}")
            end_idx = self.find_closing_token(tokens, start_index, "heading_close")
            return None, end_idx

        inline_token = tokens[inline_token_index]
        # Use helper method to get plain text instead of raw markdown
        text_content = self._get_plain_text_from_inline_token(inline_token)
        formatting = self.element_factory._extract_formatting_from_inline_token(inline_token)

        end_idx = self.find_closing_token(tokens, start_index, "heading_close")

        # CRITICAL FIX: Improved heading classification to handle all cases correctly
        if level == 1:
            # H1 headers are always treated as titles
            element_type = ElementType.TITLE
            default_alignment = AlignmentType.CENTER
        elif is_subtitle or (level == 2 and not is_section_heading):
            # Explicit subtitle flag or first H2 that's not a section heading
            element_type = ElementType.SUBTITLE
            default_alignment = AlignmentType.CENTER
        else:
            # All other headings (section H2s and all H3+) become text elements with styling
            element_type = ElementType.TEXT
            default_alignment = AlignmentType.LEFT

            # Add styling for section headings based on level
            if level == 2:  # It's a section H2, make it prominent
                directives["fontsize"] = 18
                directives["margin_bottom"] = 10
            elif level == 3:
                directives["fontsize"] = 16
                directives["margin_bottom"] = 8

        # Get alignment from directives or use default
        horizontal_alignment = AlignmentType(directives.get("align", default_alignment.value))

        # Create the appropriate element based on element_type
        element: TextElement | None = None
        if element_type == ElementType.TITLE:
            element = self.element_factory.create_title_element(
                title=text_content,
                formatting=formatting,
            )
        elif element_type == ElementType.SUBTITLE:
            element = self.element_factory.create_subtitle_element(
                text=text_content,
                formatting=formatting,
                alignment=horizontal_alignment,
                directives=directives.copy(),
            )
        else:  # ElementType.TEXT for section headers
            element = self.element_factory.create_text_element(
                text=text_content,
                formatting=formatting,
                alignment=horizontal_alignment,
                directives=directives.copy(),
            )

        logger.debug(
            f"Created heading element (type: {element_type}, level: {level}, "
            f"is_section_heading: {is_section_heading}, is_subtitle: {is_subtitle}, "
            f"text: '{text_content[:30]}') from token index {start_index} to {end_idx}"
        )
        return element, end_idx

    def _process_paragraph(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        """Process a paragraph token sequence."""
        # Find the inline token that contains the actual text
        inline_index = start_index + 1
        if inline_index >= len(tokens) or tokens[inline_index].type != "inline":
            logger.warning("Expected inline token after paragraph_open")
            return None, start_index + 1

        inline_token = tokens[inline_index]
        raw_text_content = inline_token.content or ""

        # Extract element-specific directives from the beginning of the text
        element_directives, cleaned_text_content = self._extract_element_directives_from_text(raw_text_content)

        # Merge element-specific directives with existing directives (element-specific take precedence)
        final_directives = self.merge_directives(directives, element_directives)

        # Extract formatting and create the text element
        formatting = self.element_factory.extract_formatting_from_text(cleaned_text_content, self.md)

        # Skip empty paragraphs (after directive extraction)
        if not cleaned_text_content.strip():
            logger.debug("Skipping empty paragraph after directive extraction")
            # Find the paragraph_close token
            close_index = inline_index + 1
            while close_index < len(tokens) and tokens[close_index].type != "paragraph_close":
                close_index += 1
            return None, close_index

        element = self.element_factory.create_text_element(
            text=cleaned_text_content,
            formatting=formatting,
            directives=final_directives,
        )

        # Find the paragraph_close token to determine the end of this token sequence
        close_index = inline_index + 1
        while close_index < len(tokens) and tokens[close_index].type != "paragraph_close":
            close_index += 1

        logger.debug(f"Created text element with directives: {final_directives}")
        return element, close_index

    def _process_quote(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[TextElement | None, int]:
        end_idx = self.find_closing_token(tokens, start_index, "blockquote_close")

        quote_text_parts = []
        all_formatting: list[TextFormat] = []
        current_text_len = 0

        i = start_index + 1
        while i < end_idx:
            token_i = tokens[i]
            if token_i.type == "paragraph_open":
                para_inline_idx = i + 1
                if para_inline_idx < end_idx and tokens[para_inline_idx].type == "inline":
                    inline_token = tokens[para_inline_idx]
                    # Use helper method to get plain text instead of raw markdown
                    text_part = self._get_plain_text_from_inline_token(inline_token)
                    part_formatting = self.element_factory._extract_formatting_from_inline_token(inline_token)

                    if quote_text_parts:  # Add newline if not the first paragraph
                        current_text_len += 1  # for the \n
                    quote_text_parts.append(text_part)

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

        final_quote_text = "\n".join(quote_text_parts)
        if not final_quote_text.strip():
            return None, end_idx

        horizontal_alignment = AlignmentType(directives.get("align", AlignmentType.LEFT.value))

        element = self.element_factory.create_quote_element(
            text=final_quote_text,
            formatting=all_formatting,
            alignment=horizontal_alignment,
            directives=directives.copy(),
        )
        logger.debug(f"Created blockquote element from token index {start_index} to {end_idx}")
        return element, end_idx
