"""List formatter for content parsing."""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element, ListItem, TextFormat
from markdowndeck.parser.content.formatters.base import BaseFormatter

logger = logging.getLogger(__name__)


class ListFormatter(BaseFormatter):
    """Formatter for list elements (ordered and unordered)."""

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in ["bullet_list_open", "ordered_list_open"]

    def process(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        """Create a list element from tokens."""
        open_token = tokens[start_index]
        ordered = open_token.type == "ordered_list_open"
        close_tag_type = "ordered_list_close" if ordered else "bullet_list_close"

        end_index = self.find_closing_token(tokens, start_index, close_tag_type)

        items = self._extract_list_items(tokens, start_index + 1, end_index, 0)

        if not items:
            logger.debug(f"No list items found for list at index {start_index}, skipping element.")
            return None, end_index

        element = self.element_factory.create_list_element(
            items=items, ordered=ordered, directives=directives.copy()
        )
        logger.debug(
            f"Created {'ordered' if ordered else 'bullet'} list with {len(items)} top-level items from token index {start_index} to {end_index}"
        )
        return element, end_index

    def _extract_list_items(
        self, tokens: list[Token], current_token_idx: int, list_end_idx: int, level: int
    ) -> list[ListItem]:
        """
        Recursively extracts list items, handling nesting.
        """
        items: list[ListItem] = []
        i = current_token_idx

        while i < list_end_idx:
            token = tokens[i]

            if token.type == "list_item_open":
                # Find the content of this list item
                item_content_start_idx = i + 1
                item_text = ""
                item_formatting: list[TextFormat] = []
                children: list[ListItem] = []

                # Iterate within the list_item_open and list_item_close
                # A list item can contain paragraphs, nested lists, etc.
                j = item_content_start_idx
                item_content_processed_up_to = j

                while j < list_end_idx and not (
                    tokens[j].type == "list_item_close" and tokens[j].level == token.level
                ):
                    item_token = tokens[j]
                    if (
                        item_token.type == "paragraph_open"
                    ):  # Text content of list item is usually in a paragraph
                        inline_idx = j + 1
                        if inline_idx < list_end_idx and tokens[inline_idx].type == "inline":
                            # Append text, if multiple paragraphs, join with newline
                            if item_text:
                                item_text += "\n"
                            current_text_offset = len(item_text)

                            # Use helper method to extract plain text instead of raw markdown
                            plain_text = self._get_plain_text_from_inline_token(tokens[inline_idx])
                            item_text += plain_text

                            extracted_fmts = (
                                self.element_factory._extract_formatting_from_inline_token(
                                    tokens[inline_idx]
                                )
                            )
                            for fmt in extracted_fmts:
                                item_formatting.append(
                                    TextFormat(
                                        start=fmt.start + current_text_offset,
                                        end=fmt.end + current_text_offset,
                                        format_type=fmt.format_type,
                                        value=fmt.value,
                                    )
                                )
                        # Move j past the paragraph
                        j = self.find_closing_token(tokens, j, "paragraph_close")
                    elif item_token.type in ["bullet_list_open", "ordered_list_open"]:
                        # This is a nested list
                        nested_list_close_tag = (
                            "bullet_list_close"
                            if item_token.type == "bullet_list_open"
                            else "ordered_list_close"
                        )
                        nested_list_end_idx = self.find_closing_token(
                            tokens, j, nested_list_close_tag
                        )
                        children.extend(
                            self._extract_list_items(tokens, j + 1, nested_list_end_idx, level + 1)
                        )
                        j = nested_list_end_idx

                    item_content_processed_up_to = j  # update how far we've processed for this item
                    j += 1

                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                )
                items.append(list_item_obj)
                i = (
                    item_content_processed_up_to + 1
                )  # Continue after the list_item_close or processed content

            else:  # Not a list_item_open, means we are past the items at current_level or malformed
                i += 1

        return items
