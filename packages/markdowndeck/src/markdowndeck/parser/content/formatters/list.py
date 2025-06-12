"""List formatter for content parsing."""

import logging
from typing import Any

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

        items, item_directives = self._extract_list_items(
            tokens, start_index + 1, end_index, 0
        )

        if item_directives:
            merged_directives.update(item_directives)

        if not items:
            logger.debug(
                f"No list items found for list at index {start_index}, skipping element."
            )
            return [], end_index

        element = self.element_factory.create_list_element(
            items=items, ordered=ordered, directives=merged_directives.copy()
        )
        logger.debug(
            f"Created {'ordered' if ordered else 'bullet'} list with {len(items)} top-level items from token index {start_index} to {end_index}"
        )
        # REFACTORED: Return a list containing the element to match the base class signature.
        return [element], end_index

    def _extract_list_items(
        self, tokens: list[Token], current_token_idx: int, list_end_idx: int, level: int
    ) -> tuple[list[ListItem], dict[str, Any]]:
        """
        Recursively extracts list items, handling nesting.
        """
        items: list[ListItem] = []
        found_directives: dict[str, Any] = {}
        i = current_token_idx
        pending_directives_for_next_item: dict[str, Any] = {}

        while i < list_end_idx:
            token = tokens[i]
            if token.type == "list_item_open":
                preceding_directives = self._extract_preceding_list_item_directives(
                    tokens, i
                )
                if pending_directives_for_next_item:
                    preceding_directives.update(pending_directives_for_next_item)
                    pending_directives_for_next_item = {}

                item_content_start_idx = i + 1
                item_text = ""
                item_formatting: list[TextFormat] = []
                children: list[ListItem] = []
                j = item_content_start_idx
                item_content_processed_up_to = j

                while j < list_end_idx and not (
                    tokens[j].type == "list_item_close"
                    and tokens[j].level == token.level
                ):
                    item_token = tokens[j]
                    if item_token.type == "paragraph_open":
                        inline_idx = j + 1
                        if (
                            inline_idx < list_end_idx
                            and tokens[inline_idx].type == "inline"
                        ):
                            if item_text:
                                item_text += "\n"
                            current_text_offset = len(item_text)
                            inline_token = tokens[inline_idx]
                            raw_content = inline_token.content or ""
                            (
                                item_directives,
                                cleaned_content,
                                trailing_directives,
                            ) = self._extract_list_item_directives_with_trailing(
                                raw_content
                            )
                            if trailing_directives:
                                pending_directives_for_next_item.update(
                                    trailing_directives
                                )
                            if item_directives:
                                found_directives.update(item_directives)
                            plain_text = self._get_plain_text_from_inline_token(
                                inline_token
                            )
                            item_text += plain_text
                            extracted_fmts = self.element_factory._extract_formatting_from_inline_token(
                                tokens[inline_idx]
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
                        nested_items, nested_directives = self._extract_list_items(
                            tokens, j + 1, nested_list_end_idx, level + 1
                        )
                        children.extend(nested_items)
                        if nested_directives:
                            found_directives.update(nested_directives)
                        j = nested_list_end_idx
                    item_content_processed_up_to = j
                    j += 1

                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                    directives=preceding_directives,
                )
                items.append(list_item_obj)
                i = item_content_processed_up_to + 1
            else:
                i += 1
        return items, found_directives

    def _extract_preceding_list_item_directives(
        self, tokens: list[Token], list_item_idx: int
    ) -> dict[str, Any]:
        return {}

    def _extract_list_item_directives_with_trailing(
        self, content: str
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        return {}, content, {}
