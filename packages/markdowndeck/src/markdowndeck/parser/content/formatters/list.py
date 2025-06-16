import logging
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdowndeck.models import Element, ListItem
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class ListFormatter(BaseFormatter):
    """Formatter for list elements (ordered and unordered)."""

    def __init__(self, element_factory):
        """Initialize the ListFormatter with directive parsing capability."""
        super().__init__(element_factory)
        self.directive_parser = DirectiveParser()
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
        # Create a copy of directives for this list element.
        list_level_directives = self.merge_directives(
            section_directives, element_specific_directives
        )

        open_token = tokens[start_index]
        ordered = open_token.type == "ordered_list_open"
        close_tag_type = "ordered_list_close" if ordered else "bullet_list_close"

        end_index = self.find_closing_token(tokens, start_index, close_tag_type)

        # FIXED: Pass the original section_directives down so item-level directives have correct precedence.
        items = self._extract_list_items(
            tokens, start_index + 1, end_index, 0, section_directives
        )

        # FIXED: Elevate certain directives from list items to the list element itself.
        # Only layout-related directives should be elevated; visual directives stay with items.
        if items:
            # Define which directives should be elevated from item to list
            list_level_directive_keys = {
                "align",
                "valign",
                "width",
                "height",
                "margin",
                "padding",
            }

            # If there's only one item with list-level directives, elevate them
            if len(items) == 1 and items[0].directives:
                item_directives = items[0].directives
                list_specific_directives = {}
                remaining_item_directives = {}

                for key, value in item_directives.items():
                    if key in list_level_directive_keys:
                        list_specific_directives[key] = value
                    else:
                        remaining_item_directives[key] = value

                if list_specific_directives:
                    list_level_directives.update(list_specific_directives)
                    items[0].directives = remaining_item_directives
            elif not items[0].text.strip() and items[0].directives:
                # Handle empty first item with directives (original logic)
                list_specific_directives = items.pop(0).directives
                list_level_directives.update(list_specific_directives)

        if not items:
            logger.debug(
                f"No list items found for list at index {start_index}, skipping element."
            )
            return [], end_index

        element = self.element_factory.create_list_element(
            items=items, ordered=ordered, directives=list_level_directives
        )
        logger.debug(
            f"Created {'ordered' if ordered else 'bullet'} list with {len(items)} top-level items from token index {start_index} to {end_index}"
        )
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
        """
        if section_directives is None:
            section_directives = {}

        items: list[ListItem] = []
        i = current_token_idx

        while i < list_end_idx:
            token = tokens[i]
            if token.type == "list_item_open":
                item_directives: dict[str, Any] = {}
                raw_content_for_reparse = ""
                children: list[ListItem] = []

                item_end_idx = self.find_closing_token(tokens, i, "list_item_close")

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
                            cleaned_content, directives = (
                                self.directive_parser.parse_and_strip_from_text(
                                    inline_token.content
                                )
                            )
                            item_directives.update(directives)

                            if raw_content_for_reparse:
                                raw_content_for_reparse += "\n"
                            raw_content_for_reparse += cleaned_content.strip()

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

                if raw_content_for_reparse:
                    parsed_inline_tokens = self.md.parse(raw_content_for_reparse)

                    # Find the inline token in the parsed tokens
                    inline_token = None
                    for token in parsed_inline_tokens:
                        if token.type == "inline":
                            inline_token = token
                            break

                    if inline_token:
                        item_text = self._get_plain_text_from_inline_token(inline_token)
                        item_formatting = (
                            self.element_factory._extract_formatting_from_inline_token(
                                inline_token
                            )
                        )
                    else:
                        # Fallback: treat as plain text if no inline token found
                        item_text = raw_content_for_reparse
                        item_formatting = []
                else:
                    item_text = ""
                    item_formatting = []

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
