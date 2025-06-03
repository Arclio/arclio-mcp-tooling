"""
Image formatter for content parsing.
Handles standalone images and images that might be the sole content of a paragraph.
"""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element
from markdowndeck.parser.content.formatters.base import BaseFormatter

logger = logging.getLogger(__name__)


class ImageFormatter(BaseFormatter):
    """Formatter for image elements."""

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """
        Check if this formatter can handle the given token, specifically looking for
        paragraphs that solely contain an image.
        """
        if token.type == "paragraph_open":
            # Look ahead to see if the paragraph is image-only
            # This requires peeking at the tokens that ContentParser would pass to process()
            # For simplicity in can_handle, we assume ContentParser's dispatch logic
            # will call process(), and process() will determine if it's truly an image.
            # A more robust can_handle would need the index of `token` in the main list.
            # For now, let process make the final call.
            # However, if we can reliably check here, it's better.
            # This check is tricky without the main token list and current index.
            # Let's assume ContentParser might try this formatter for paragraphs.
            # The `process` method will return None if it's not an image-only paragraph.
            #
            # A more direct check for an inline token containing only an image:
            # This requires `leading_tokens` to be the main token list and `token` is the current one.
            # This is hard to do in `can_handle` without the main token list and current index.
            # Let's make process() robust enough to return None if it's not an image.
            #
            # Simplified: If it's a paragraph_open, it *could* be an image.
            # If it's an image token directly (less common from markdown-it for block images).
            return True  # Tentatively, process will verify.

        # For directly embedded image tokens, if any
        return token.type == "image"

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[Element | None, int]:
        """
        Create an image element if the current token sequence represents an image.
        This primarily targets paragraphs that solely contain an image.
        """
        # Merge section and element-specific directives
        merged_directives = self.merge_directives(section_directives, element_specific_directives)

        current_token = tokens[start_index]
        image_element: Element | None = None

        if current_token.type == "paragraph_open":
            inline_token_index = start_index + 1

            # Simple scan for paragraph_close
            paragraph_close_index = start_index + 2  # Default: next token after inline
            for i in range(start_index + 1, len(tokens)):
                if tokens[i].type == "paragraph_close":
                    paragraph_close_index = i
                    break

            if inline_token_index < len(tokens) and tokens[inline_token_index].type == "inline":
                inline_token = tokens[inline_token_index]
                if hasattr(inline_token, "children") and inline_token.children:
                    # Check if this paragraph only contains images and whitespace
                    image_children = [child for child in inline_token.children if child.type == "image"]
                    non_image_content = [
                        child
                        for child in inline_token.children
                        if child.type not in ["image", "softbreak"]
                        and not (child.type == "text" and not child.content.strip())
                    ]

                    if len(image_children) == 1 and len(non_image_content) == 0:
                        # This is an image-only paragraph
                        image_child = image_children[0]
                        src = image_child.attrs.get("src", "") if hasattr(image_child, "attrs") else ""
                        alt_text = image_child.content or ""

                        if src:
                            image_element = self.element_factory.create_image_element(
                                url=src,
                                alt_text=alt_text,
                                directives=merged_directives.copy(),
                            )
                            logger.debug(f"Created image element from paragraph at index {start_index}: {src}")
                            return image_element, paragraph_close_index

                # If we reach here, it's not an image-only paragraph
                # Return None and indicate we didn't consume any tokens so other formatters can try
                logger.debug(f"Paragraph at index {start_index} is not image-only, deferring to other formatters")
                return None, start_index - 1  # Don't consume any tokens

            # If no inline token found, it's an empty paragraph - don't handle it
            return None, start_index - 1

        if current_token.type == "image":  # Handles cases where 'image' token might be directly processable
            src = current_token.attrs.get("src", "")
            alt_text = current_token.content
            if not alt_text and current_token.children:
                alt_text = "".join(c.content for c in current_token.children if c.type == "text")

            if src:
                image_element = self.element_factory.create_image_element(
                    url=src, alt_text=alt_text, directives=merged_directives.copy()
                )
                logger.debug(f"Created image element from direct image token: {src}")
                return image_element, start_index

        # If we reach here, we couldn't create an image element
        return None, start_index - 1
