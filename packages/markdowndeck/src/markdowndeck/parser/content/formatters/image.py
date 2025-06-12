import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive.directive_parser import DirectiveParser

logger = logging.getLogger(__name__)


class ImageFormatter(BaseFormatter):
    """Formatter for image elements."""

    def __init__(self, element_factory):
        """Initialize the image formatter."""
        super().__init__(element_factory)
        self.directive_parser = DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """
        Check if this formatter can handle the given token.
        This formatter now only handles explicit 'image' tokens.
        Paragraphs containing images are handled by the TextFormatter.
        """
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
        Create an image element from an image token.
        Paragraphs containing images are now handled by the TextFormatter
        to correctly process mixed content (e.g., image + caption).
        """
        current_token = tokens[start_index]
        if current_token.type != "image":
            return [], start_index

        # Merge section and element-specific directives
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        src = (
            current_token.attrs.get("src", "")
            if hasattr(current_token, "attrs")
            else ""
        )
        # The 'alt text' is stored in the children of the image token
        alt_text = (
            "".join(c.content for c in current_token.children if c.type == "text")
            if current_token.children
            else ""
        )

        # Directives may follow the image on the same line, which markdown-it
        # parses as a text token. We need to check the next token.
        if start_index + 1 < len(tokens):
            next_token = tokens[start_index + 1]
            if next_token.type == "text":
                line_directives, remaining_text = (
                    self.directive_parser.parse_and_strip_from_text(next_token.content)
                )
                if line_directives and not remaining_text.strip():
                    merged_directives.update(line_directives)
                    # Since we consumed the directive text token, we should advance the index
                    # However, the main loop advances by 1, so we return start_index + 1
                    # to signal we consumed the image and the text token.
                    if src:
                        image_element = self.element_factory.create_image_element(
                            url=src, alt_text=alt_text, directives=merged_directives
                        )
                        logger.debug(
                            f"Created image element and consumed directive text: {src}"
                        )
                        return [image_element], start_index + 1  # Consumed two tokens

        if src:
            image_element = self.element_factory.create_image_element(
                url=src, alt_text=alt_text, directives=merged_directives
            )
            logger.debug(f"Created image element from direct image token: {src}")
            return [image_element], start_index

        return [], start_index
