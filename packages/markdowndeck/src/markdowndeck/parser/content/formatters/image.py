"""
Image formatter for content parsing.
Handles standalone images and images that might be the sole content of a paragraph.
TASK 1.3 ENHANCEMENT: Also handles images followed by directives.
"""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive.directive_parser import DirectiveParser

logger = logging.getLogger(__name__)


class ImageFormatter(BaseFormatter):
    """Formatter for image elements.

    TASK 1.3 ENHANCEMENT: Now handles images followed by directives.
    """

    def __init__(self, element_factory):
        """Initialize the image formatter with directive parser for Task 1.3."""
        super().__init__(element_factory)
        self.directive_parser = DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """
        Check if this formatter can handle the given token, specifically looking for
        paragraphs that solely contain an image.
        """
        if token.type == "paragraph_open":
            # We need to be more conservative here. Only claim we can handle
            # paragraph_open if we can reasonably expect it to be image-only.
            # For now, we'll still return True but ensure process() properly
            # defers to other formatters when it's not an image.
            # A better approach would be to check the inline content here,
            # but that requires more context about the token sequence.
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
    ) -> tuple[list[Element], int]:
        """
        Create an image element if the current token sequence represents an image.
        This primarily targets paragraphs that solely contain an image.

        TASK 3.1: Updated to return list[Element] instead of Element | None.
        """
        # Merge section and element-specific directives
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

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

            if (
                inline_token_index < len(tokens)
                and tokens[inline_token_index].type == "inline"
            ):
                inline_token = tokens[inline_token_index]
                if hasattr(inline_token, "children") and inline_token.children:
                    # Check if this paragraph only contains images and whitespace
                    image_children = [
                        child
                        for child in inline_token.children
                        if child.type == "image"
                    ]
                    non_image_content = [
                        child
                        for child in inline_token.children
                        if child.type not in ["image", "softbreak"]
                        and not (child.type == "text" and not child.content.strip())
                    ]

                    if len(image_children) == 1 and len(non_image_content) == 0:
                        # This is an image-only paragraph
                        image_child = image_children[0]
                        src = (
                            image_child.attrs.get("src", "")
                            if hasattr(image_child, "attrs")
                            else ""
                        )
                        alt_text = image_child.content or ""

                        if src:
                            image_element = self.element_factory.create_image_element(
                                url=src,
                                alt_text=alt_text,
                                directives=merged_directives.copy(),
                            )
                            logger.debug(
                                f"Created image element from paragraph at index {start_index}: {src}"
                            )
                            return [image_element], paragraph_close_index

                    # TASK 1.3 FIX: Check if this paragraph contains an image followed by directives
                    elif len(image_children) == 1 and len(non_image_content) == 1:
                        # Check if the non-image content is directive text
                        non_image_child = non_image_content[0]
                        if non_image_child.type == "text":
                            directive_text = non_image_child.content.strip()

                            # Try to parse as directives
                            post_image_directives, remaining_text = (
                                self.directive_parser.parse_inline_directives(
                                    directive_text
                                )
                            )

                            if post_image_directives and not remaining_text:
                                # This is an image followed by directives
                                image_child = image_children[0]
                                src = (
                                    image_child.attrs.get("src", "")
                                    if hasattr(image_child, "attrs")
                                    else ""
                                )
                                alt_text = image_child.content or ""

                                # Merge the post-image directives with the existing directives
                                final_directives = merged_directives.copy()
                                final_directives.update(post_image_directives)

                                if src:
                                    image_element = (
                                        self.element_factory.create_image_element(
                                            url=src,
                                            alt_text=alt_text,
                                            directives=final_directives,
                                        )
                                    )
                                    logger.debug(
                                        f"TASK 1.3: Created image element with post-image directives at index {start_index}: {src}, directives: {post_image_directives}"
                                    )
                                    return [image_element], paragraph_close_index

                # If we reach here, it's not an image-only paragraph
                # Return None and indicate we didn't consume any tokens so other formatters can try
                # CRITICAL FIX: Return start_index instead of start_index - 1 to avoid negative indices
                logger.debug(
                    f"Paragraph at index {start_index} is not image-only, deferring to other formatters"
                )
                return (
                    [],
                    start_index,
                )  # Don't consume any tokens, let other formatters try

            # If no inline token found, it's an empty paragraph - don't handle it
            return [], start_index

        if (
            current_token.type == "image"
        ):  # Handles cases where 'image' token might be directly processable
            src = current_token.attrs.get("src", "")
            alt_text = current_token.content
            if not alt_text and current_token.children:
                alt_text = "".join(
                    c.content for c in current_token.children if c.type == "text"
                )

            if src:
                image_element = self.element_factory.create_image_element(
                    url=src, alt_text=alt_text, directives=merged_directives.copy()
                )
                logger.debug(f"Created image element from direct image token: {src}")
                return [image_element], start_index

        # If we reach here, we couldn't create an image element
        return [], start_index
