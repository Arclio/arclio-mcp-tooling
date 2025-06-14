import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import Element, ListItem, TextFormat
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class ListFormatter(BaseFormatter):
    """Formatter for list elements (ordered and unordered)."""

    def __init__(self, element_factory):
        """Initialize the ListFormatter with directive parsing capability."""
        super().__init__(element_factory)
        self.directive_parser = DirectiveParser()
        # REFACTORED: Added a local markdown-it instance to fix a dependency bug.
        # This instance is used to re-parse list item content after directives are stripped.
        opts = {"html": False, "typographer": True, "linkify": True, "breaks": True}
        self.md = MarkdownIt("commonmark", opts)
        self.md.enable("table")
        self.md.enable("strikethrough")

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in ["bullet_list_open", "ordered_list_open"]

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[list[Element], int]:
        """Create a list element from tokens."""
        merged_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        open_token = tokens[start_index]
        ordered = open_token.type == "ordered_list_open"
        close_tag_type = "ordered_list_close" if ordered else "bullet_list_close"

        end_index = self.find_closing_token(tokens, start_index, close_tag_type)

        items = self._extract_list_items(
            tokens, start_index + 1, end_index, 0, merged_directives
        )

        if not items:
            logger.debug(
                f"No list items found for list at index {start_index}, skipping element."
            )
            return [], end_index

        # CRITICAL FIX: Promote layout directives from last item to element level
        # Per PRINCIPLES.md Section 8.1, element-level directives should take precedence
        element_level_directives = {
            "align",
            "valign",
            "width",
            "height",
            "margin",
            "padding",
        }

        if items:
            last_item = items[-1]
            directives_to_promote = {}
            remaining_item_directives = {}

            # Check if last item has directives that should be promoted to element level
            for key, value in last_item.directives.items():
                if key in element_level_directives:
                    directives_to_promote[key] = value
                    logger.debug(
                        f"Promoting directive '{key}={value}' from last item to list element"
                    )
                else:
                    remaining_item_directives[key] = value

            # Update the last item to remove promoted directives
            if directives_to_promote:
                last_item.directives = remaining_item_directives
                # Update element directives with promoted directives (they override inherited ones)
                merged_directives.update(directives_to_promote)

        element = self.element_factory.create_list_element(
            items=items, ordered=ordered, directives=merged_directives.copy()
        )
        logger.debug(
            f"Created {'ordered' if ordered else 'bullet'} list with {len(items)} top-level items from token index {start_index} to {end_index}"
        )
        # REFACTORED: Return a list containing the element to match the base class signature.
        return [element], end_index

    def _extract_list_items(
        self,
        tokens: list[Token],
        current_token_idx: int,
        list_end_idx: int,
        level: int,
        section_directives: dict[str, Any] = None,
    ) -> list[ListItem]:
        """
        Recursively extracts list items, handling nesting and directives.

        Args:
            tokens: List of markdown tokens
            current_token_idx: Current position in tokens
            list_end_idx: End position for this list
            level: Nesting level of items
            section_directives: Directives inherited from parent sections
        """
        if section_directives is None:
            section_directives = {}

        items: list[ListItem] = []
        i = current_token_idx

        while i < list_end_idx:
            token = tokens[i]
            if token.type == "list_item_open":
                item_directives: dict[str, Any] = {}
                item_text = ""
                item_formatting: list[TextFormat] = []
                children: list[ListItem] = []

                # Find the end of the current list item
                item_end_idx = i
                while item_end_idx < list_end_idx and not (
                    tokens[item_end_idx].type == "list_item_close"
                    and tokens[item_end_idx].level == token.level
                ):
                    item_end_idx += 1

                # Process tokens within this list item
                j = i + 1
                while j < item_end_idx:
                    item_token = tokens[j]
                    if item_token.type == "paragraph_open":
                        inline_idx = j + 1
                        if (
                            inline_idx < item_end_idx
                            and tokens[inline_idx].type == "inline"
                        ):
                            inline_token = tokens[inline_idx]
                            # FIXED: Parse directives from the item's raw text content
                            cleaned_content, directives = (
                                self.directive_parser.parse_and_strip_from_text(
                                    inline_token.content
                                )
                            )
                            item_directives.update(directives)

                            # CRITICAL FIX: Use cleaned content directly instead of re-parsing
                            # The re-parsing through markdown-it was causing the content to be lost
                            if cleaned_content.strip():
                                if item_text:
                                    item_text += "\n"
                                item_text += cleaned_content.strip()
                            else:
                                logger.debug(
                                    "DEBUG: No content after directive cleaning"
                                )

                            # TODO: For now, we're not extracting formatting from cleaned content
                            # This means directives like [bold] won't work in list items, but the basic
                            # functionality will work. This can be improved later if needed.
                        j = self.find_closing_token(tokens, j, "paragraph_close")
                    elif item_token.type in ["bullet_list_open", "ordered_list_open"]:
                        nested_list_close_tag = (
                            "bullet_list_close"
                            if item_token.type == "bullet_list_open"
                            else "ordered_list_close"
                        )
                        nested_list_end_idx = self.find_closing_token(
                            tokens, j, nested_list_close_tag
                        )
                        children.extend(
                            self._extract_list_items(
                                tokens,
                                j + 1,
                                nested_list_end_idx,
                                level + 1,
                                section_directives,
                            )
                        )
                        j = nested_list_end_idx
                    j += 1

                # CRITICAL FIX: Merge section directives with item directives per PRINCIPLES.md Section 8.1
                # Item-specific directives (Level 1) take precedence over section directives (Level 2)
                merged_item_directives = self.merge_directives(
                    section_directives, item_directives
                )

                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                    directives=merged_item_directives,
                )
                items.append(list_item_obj)
                i = item_end_idx + 1
            else:
                i += 1
        return items

    def _extract_preceding_list_item_directives(
        self, tokens: list[Token], list_item_idx: int
    ) -> dict[str, Any]:
        return {}

    def _extract_list_item_directives_with_trailing(
        self, content: str
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """Extract directives from list item content, including trailing directives."""
        cleaned_content, directives = self.directive_parser.parse_and_strip_from_text(
            content
        )
        return directives, cleaned_content, {}
