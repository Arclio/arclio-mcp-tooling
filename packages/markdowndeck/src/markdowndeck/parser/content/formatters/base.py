"""Base formatter for content parsing."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import (
    Element,
)  # Keep if shared utilities are needed, otherwise remove
from markdowndeck.parser.content.element_factory import (
    ElementFactory,
)  # Formatters will use this

logger = logging.getLogger(__name__)


class BaseFormatter(ABC):
    """Base class for content formatters."""

    def __init__(self, element_factory: ElementFactory):
        """
        Initialize the formatter.

        Args:
            element_factory: An instance of ElementFactory to create elements.
        """
        self.element_factory = element_factory

    @abstractmethod
    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """
        Check if this formatter can handle the current token,
        potentially based on a sequence of leading tokens if ambiguous.

        Args:
            token: The current token to check.
            leading_tokens: A list of tokens immediately preceding the current
                          (or current block's opening) token. This can help
                          differentiate contexts, e.g., an image inside a paragraph.

        Returns:
            True if this formatter can handle the token, False otherwise.
        """
        pass

    @abstractmethod
    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[list[Element], int]:
        """
        Create elements from a sequence of tokens.

        TASK 3.1: Updated to support multiple elements from a single token block.
        This enables mixed-content paragraphs like `![img](url) caption` to produce
        multiple elements (ImageElement and TextElement).

        Args:
            tokens: The full list of tokens for the current parsing scope.
            start_index: The index of the token that this formatter should start processing.
            section_directives: Directives from the current section to apply to elements.
            element_specific_directives: Directives specific to these elements that override section directives.
            **kwargs: Additional keyword arguments for specific formatters.

        Returns:
            A tuple containing:
                - A list of created Element objects (empty list if no elements were created).
                - The index of the last token consumed by this formatter.
        """
        raise NotImplementedError("Subclasses must implement process()")

    def merge_directives(
        self,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Merge section-level and element-specific directives.

        Element-specific directives take precedence over section-level directives.

        Args:
            section_directives: Directives from the section
            element_specific_directives: Element-specific directives (optional)

        Returns:
            Merged directives dictionary
        """
        merged = section_directives.copy()
        if element_specific_directives:
            merged.update(element_specific_directives)
            logger.debug(
                f"Merged directives: section={section_directives}, element={element_specific_directives}, result={merged}"
            )
        return merged

    def find_closing_token(
        self,
        tokens: list[Token],
        open_token_index: int,
        close_tag_type: str,
    ) -> int:
        """
        Find the index of the matching closing token for a given opening token.
        Considers nesting levels.

        Args:
            tokens: The list of all tokens.
            open_token_index: The index of the opening token.
            close_tag_type: The type of the closing token to find (e.g., "paragraph_close").

        Returns:
            The index of the closing token, or the last index if not found (should not happen).
        """
        open_token = tokens[open_token_index]
        open_tag_type = open_token.type
        nesting_level = open_token.level
        depth = 1

        for i in range(open_token_index + 1, len(tokens)):
            current_token = tokens[i]
            if current_token.level == nesting_level:
                if current_token.type == open_tag_type:
                    depth += 1
                elif current_token.type == close_tag_type:
                    depth -= 1
                    if depth == 0:
                        return i
            # Also consider tokens that might affect depth at higher levels
            elif (
                current_token.level < nesting_level
            ):  # Exited the current nesting context
                logger.warning(
                    f"Exited nesting level {nesting_level} looking for {close_tag_type} after {open_tag_type} at index {open_token_index}. Found {current_token.type} at level {current_token.level}."
                )
                return i - 1  # Should have closed before this

        logger.warning(
            f"Could not find matching closing token '{close_tag_type}' for '{open_tag_type}' "
            f"starting at index {open_token_index}. Defaulting to end of token list."
        )
        return len(tokens) - 1

    def _get_plain_text_from_inline_token(self, inline_token: Token) -> str:
        """
        Extract plain text content from an inline token, removing markdown formatting syntax.

        Args:
            inline_token: A markdown-it inline token with children

        Returns:
            Plain text content with formatting syntax removed
        """
        if not hasattr(inline_token, "children"):
            return getattr(inline_token, "content", "")

        plain_text = ""
        for child in inline_token.children:
            if child.type == "text" or child.type == "code_inline":
                plain_text += child.content
            elif child.type == "softbreak" or child.type == "hardbreak":
                plain_text += "\n"
            elif child.type == "image":
                plain_text += (
                    child.attrs.get("alt", "") if hasattr(child, "attrs") else ""
                )
            elif child.type.endswith("_open") or child.type.endswith("_close"):
                # Skip formatting markers
                pass

        return plain_text
