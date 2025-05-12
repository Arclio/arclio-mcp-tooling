"""Text formatter for content parsing (paragraphs, headings, blockquotes)."""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import (
    AlignmentType,
    Element,
    ElementType,
    TextElement,
    TextFormat,
    TextFormatType,
)

# ElementFactory injected via BaseFormatter
from markdowndeck.parser.content.formatters.base import BaseFormatter

logger = logging.getLogger(__name__)


class TextFormatter(BaseFormatter):
    """Formatter for text elements (headings, paragraphs, quotes)."""

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        if token.type in ["heading_open", "blockquote_open"]:
            return True
        if token.type == "paragraph_open":
            # Check if it's NOT an image-only paragraph.
            # This relies on ImageFormatter running first and "consuming" image-only paragraphs.
            if (
                len(leading_tokens) > 1 and leading_tokens[1].type == "inline"
            ):  # leading_tokens[0] is current token
                inline_children = getattr(leading_tokens[1], "children", [])
                if inline_children:
                    image_children = [child for child in inline_children if child.type == "image"]
                    other_content = [
                        child
                        for child in inline_children
                        if child.type != "image" and (child.type != "text" or child.content.strip())
                    ]
                    if len(image_children) > 0 and not other_content:
                        return (
                            False  # This is an image-only paragraph, ImageFormatter should take it.
                        )
            return True  # It's a paragraph, and not clearly image-only from this limited peek.
        return False

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        directives: dict[str, Any],
        **kwargs,
    ) -> tuple[Element | None, int]:
        # Add guard clause for empty tokens
        if not tokens or start_index >= len(tokens):
            logger.debug(
                f"TextFormatter received empty tokens or invalid start_index {start_index}."
            )
            return None, start_index

        token = tokens[start_index]

        if token.type == "heading_open":
            # Pass any additional kwargs to _process_heading
            return self._process_heading(tokens, start_index, directives, **kwargs)
        if token.type == "paragraph_open":
            return self._process_paragraph(tokens, start_index, directives)
        if token.type == "blockquote_open":
            return self._process_quote(tokens, start_index, directives)

        logger.warning(
            f"TextFormatter cannot process token type: {token.type} at index {start_index}"
        )
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
    ) -> tuple[TextElement | None, int]:
        inline_token_index = start_index + 1
        if not (inline_token_index < len(tokens) and tokens[inline_token_index].type == "inline"):
            logger.debug(
                f"No inline content found for paragraph at index {start_index}, could be empty or just structural."
            )
            end_idx = self.find_closing_token(tokens, start_index, "paragraph_close")
            return None, end_idx

        inline_token = tokens[inline_token_index]
        # Use helper method to get plain text instead of raw markdown
        text_content = self._get_plain_text_from_inline_token(inline_token)
        formatting = self.element_factory._extract_formatting_from_inline_token(inline_token)

        end_idx = self.find_closing_token(tokens, start_index, "paragraph_close")

        # Double check if it's an image-only paragraph, ImageFormatter should have caught this if ordered correctly.
        if hasattr(inline_token, "children") and inline_token.children:
            image_children = [child for child in inline_token.children if child.type == "image"]
            other_content_present = any(
                child
                for child in inline_token.children
                if child.type != "image" and (child.type != "text" or child.content.strip())
            )
            if len(image_children) > 0 and not other_content_present:
                logger.debug(
                    f"TextFormatter encountered image-only paragraph at {start_index}, but ImageFormatter should handle it. Skipping."
                )
                return None, end_idx

        if not text_content.strip() and not any(
            f for f in formatting if f.format_type == TextFormatType.LINK
        ):
            logger.debug(f"Skipping empty paragraph at index {start_index}")
            return None, end_idx

        horizontal_alignment = AlignmentType(directives.get("align", AlignmentType.LEFT.value))

        element = self.element_factory.create_text_element(
            text=text_content,
            formatting=formatting,
            alignment=horizontal_alignment,
            directives=directives.copy(),
        )
        logger.debug(f"Created paragraph element from token index {start_index} to {end_idx}")
        return element, end_idx

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
                    part_formatting = self.element_factory._extract_formatting_from_inline_token(
                        inline_token
                    )

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
