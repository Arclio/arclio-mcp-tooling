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
        """Create a list element from tokens.

        TASK 3.1: Updated to return list[Element] instead of Element | None.
        """
        # Merge section and element-specific directives
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

        # Merge any directives found within list items
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
        return [element], end_index

    def _extract_list_items(
        self, tokens: list[Token], current_token_idx: int, list_end_idx: int, level: int
    ) -> tuple[list[ListItem], dict[str, Any]]:
        """
        Recursively extracts list items, handling nesting.

        Returns:
            Tuple of (list_items, found_directives)
        """
        items: list[ListItem] = []
        found_directives: dict[str, Any] = {}
        i = current_token_idx

        # TASK_003 FIX: Track pending directives for next list item
        pending_directives_for_next_item: dict[str, Any] = {}

        while i < list_end_idx:
            token = tokens[i]

            if token.type == "list_item_open":
                # TASK_003 FIX: Look backwards for standalone directive paragraphs before this list item
                preceding_directives = self._extract_preceding_list_item_directives(
                    tokens, i
                )

                # TASK_003 FIX: Apply any pending directives from previous item
                if pending_directives_for_next_item:
                    preceding_directives.update(pending_directives_for_next_item)
                    pending_directives_for_next_item = {}

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
                    tokens[j].type == "list_item_close"
                    and tokens[j].level == token.level
                ):
                    item_token = tokens[j]
                    if (
                        item_token.type == "paragraph_open"
                    ):  # Text content of list item is usually in a paragraph
                        inline_idx = j + 1
                        if (
                            inline_idx < list_end_idx
                            and tokens[inline_idx].type == "inline"
                        ):
                            # Append text, if multiple paragraphs, join with newline
                            if item_text:
                                item_text += "\n"
                            current_text_offset = len(item_text)

                            # TASK 1.2 FIX: Check for and extract directives from list item content
                            inline_token = tokens[inline_idx]
                            raw_content = inline_token.content or ""

                            # TASK_003 FIX: Check for trailing directives that should apply to next item
                            item_directives, cleaned_content, trailing_directives = (
                                self._extract_list_item_directives_with_trailing(
                                    raw_content
                                )
                            )

                            # Store trailing directives for next item
                            if trailing_directives:
                                pending_directives_for_next_item.update(
                                    trailing_directives
                                )

                            # If directives were found, store them for later merging
                            if item_directives:
                                found_directives.update(item_directives)
                                logger.debug(
                                    f"Found directives in list item: {item_directives}"
                                )

                            # Use cleaned content for text extraction
                            if cleaned_content != raw_content:
                                # Directives were found and removed, use cleaned content directly
                                plain_text = cleaned_content

                                # For formatting extraction, we still need to use the original token
                                # since formatting is based on the original markdown structure
                                extracted_fmts = self.element_factory._extract_formatting_from_inline_token(
                                    inline_token
                                )
                                # But we need to adjust the formatting positions since our text is shorter
                                # For now, we'll skip formatting adjustment and just use empty formatting
                                # TODO: Implement proper formatting adjustment for cleaned content
                                extracted_fmts = []
                            else:
                                # No directives found, use original content
                                plain_text = self._get_plain_text_from_inline_token(
                                    inline_token
                                )

                                # Use original token for formatting extraction
                                extracted_fmts = self.element_factory._extract_formatting_from_inline_token(
                                    tokens[inline_idx]
                                )

                            item_text += plain_text
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
                        nested_items, nested_directives = self._extract_list_items(
                            tokens, j + 1, nested_list_end_idx, level + 1
                        )
                        children.extend(nested_items)
                        if nested_directives:
                            found_directives.update(nested_directives)
                        j = nested_list_end_idx

                    item_content_processed_up_to = (
                        j  # update how far we've processed for this item
                    )
                    j += 1

                # TASK_003 FIX: Create ListItem with preceding directives applied
                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                    directives=preceding_directives,  # Apply the preceding directives
                )
                items.append(list_item_obj)
                i = (
                    item_content_processed_up_to + 1
                )  # Continue after the list_item_close or processed content

            else:  # Not a list_item_open, means we are past the items at current_level or malformed
                i += 1

        return items, found_directives

    def _extract_directives_from_list_content(
        self, content: str
    ) -> tuple[dict[str, Any], str]:
        """
        Extract directives from list item content.

        TASK 1.2 FIX: Parse directives that appear within list item text.

        Args:
            content: Raw content from the list item

        Returns:
            Tuple of (extracted_directives, cleaned_content)
        """
        if not content.strip():
            return {}, content

        lines = content.split("\n")
        all_directives = {}
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                cleaned_lines.append(line)
                continue

            # TASK 1.2 FIX: Enhanced directive extraction that handles directives followed by text
            # Pattern to match directives at the beginning of a line, followed by optional text
            directive_pattern = r"^(\s*(?:\[[^\[\]]+=[^\[\]]*\]\s*)+)(.*)"
            import re

            match = re.match(directive_pattern, line_stripped)

            if match:
                directive_text = match.group(1)
                remaining_text = match.group(2).strip()

                # Parse the directive text
                directives = self.directive_parser._parse_directive_text(directive_text)

                if directives:
                    all_directives.update(directives)
                    logger.debug(f"Extracted directives from list line: {directives}")

                    # If there's remaining text, keep it; otherwise remove the line
                    if remaining_text:
                        cleaned_lines.append(remaining_text)
                    # If no remaining text, don't add anything (removes the directive line)
                else:
                    # No valid directives found, keep the original line
                    cleaned_lines.append(line)
            else:
                # No directives found, keep the original line
                cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)
        return all_directives, cleaned_content

    def _extract_preceding_list_item_directives(
        self, tokens: list[Token], list_item_idx: int
    ) -> dict[str, Any]:
        """
        Extract directives from standalone directive paragraphs immediately preceding a list item.

        TASK_003 FIX: Implements DIRECTIVES.md Rule 2.3 (The List Item Rule).

        This handles two patterns:
        1. Directive within a list item (less common, handled by existing code)
        2. Directive between lists (when a blank line separates items, creating separate lists)

        Args:
            tokens: All tokens
            list_item_idx: Index of the list_item_open token

        Returns:
            Dictionary of directives that apply to this list item
        """
        # Pattern 1: Look backwards for a directive-only paragraph immediately before this list item
        # within the same list: paragraph_open -> inline (with directives only) -> paragraph_close -> list_item_open
        if list_item_idx >= 3:
            paragraph_close_idx = list_item_idx - 1
            inline_idx = list_item_idx - 2
            paragraph_open_idx = list_item_idx - 3

            if (
                tokens[paragraph_close_idx].type == "paragraph_close"
                and tokens[inline_idx].type == "inline"
                and tokens[paragraph_open_idx].type == "paragraph_open"
            ):

                inline_token = tokens[inline_idx]
                content = inline_token.content or ""

                if content.strip():
                    directives = self.directive_parser._parse_directive_text(
                        content.strip()
                    )

                    if directives:
                        # Verify that the content is ONLY directives (no other text)
                        import re

                        directive_pattern = r"\[[^\[\]]+=[^\[\]]*\]"
                        text_without_directives = re.sub(
                            directive_pattern, "", content
                        ).strip()

                        if not text_without_directives:
                            logger.debug(
                                f"Found preceding directives within list for list item: {directives}"
                            )
                            return directives

        # Pattern 2: Look for directive paragraphs between separate lists
        # This happens when markdown has blank lines that separate lists
        # Pattern: bullet_list_open -> list_item_open (we are here)
        # Look backwards for: bullet_list_close -> paragraph_open -> inline -> paragraph_close -> bullet_list_open
        if list_item_idx >= 5:  # Need space for the pattern
            current_list_open_idx = (
                list_item_idx - 1
            )  # Should be bullet_list_open or ordered_list_open
            if current_list_open_idx >= 0 and tokens[current_list_open_idx].type in [
                "bullet_list_open",
                "ordered_list_open",
            ]:

                # Look backwards from the current list's open token
                paragraph_close_idx = current_list_open_idx - 1
                inline_idx = current_list_open_idx - 2
                paragraph_open_idx = current_list_open_idx - 3
                prev_list_close_idx = current_list_open_idx - 4

                if (
                    paragraph_close_idx >= 0
                    and tokens[paragraph_close_idx].type == "paragraph_close"
                    and inline_idx >= 0
                    and tokens[inline_idx].type == "inline"
                    and paragraph_open_idx >= 0
                    and tokens[paragraph_open_idx].type == "paragraph_open"
                    and prev_list_close_idx >= 0
                    and tokens[prev_list_close_idx].type
                    in ["bullet_list_close", "ordered_list_close"]
                ):

                    inline_token = tokens[inline_idx]
                    content = inline_token.content or ""

                    if content.strip():
                        directives = self.directive_parser._parse_directive_text(
                            content.strip()
                        )

                        if directives:
                            # Verify that the content is ONLY directives (no other text)
                            import re

                            directive_pattern = r"\[[^\[\]]+=[^\[\]]*\]"
                            text_without_directives = re.sub(
                                directive_pattern, "", content
                            ).strip()

                            if not text_without_directives:
                                logger.debug(
                                    f"Found preceding directives between lists for list item: {directives}"
                                )
                                return directives

        return {}

    def _extract_list_item_directives_with_trailing(
        self, content: str
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """
        Extract directives from list item content and identify trailing directives.

        TASK_003 FIX: Parse directives that appear within list item text and identify trailing directives
        that should apply to the next list item according to the List Item Rule.

        Args:
            content: Raw content from the list item

        Returns:
            Tuple of (extracted_directives, cleaned_content, trailing_directives)
        """
        if not content.strip():
            return {}, content, {}

        lines = content.split("\n")
        all_directives = {}
        cleaned_lines = []
        trailing_directives = {}

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                cleaned_lines.append(line)
                continue

            # TASK_003 FIX: Check if this line contains only directives (directive-only line)
            import re

            directive_pattern = r"^\s*(\[([^\[\]]+=[^\[\]]*)\]\s*)+$"

            if re.match(directive_pattern, line_stripped):
                # This line contains only directives
                directives = self.directive_parser._parse_directive_text(line_stripped)

                if directives:
                    # Check if this is a trailing directive line (last non-empty line)
                    is_trailing = True
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip():  # Found non-empty line after this
                            is_trailing = False
                            break

                    if is_trailing:
                        # This is a trailing directive - should apply to next list item
                        trailing_directives.update(directives)
                        logger.debug(
                            f"Found trailing directives for next list item: {directives}"
                        )
                        # Don't add this line to cleaned content
                    else:
                        # This is an inline directive - applies to current item
                        all_directives.update(directives)
                        logger.debug(
                            f"Found inline directives for current list item: {directives}"
                        )
                        # Don't add this line to cleaned content
                else:
                    # No valid directives found, keep the original line
                    cleaned_lines.append(line)
            else:
                # Not a directive-only line, check for mixed content (directives + text)
                directive_prefix_pattern = r"^(\s*(?:\[[^\[\]]+=[^\[\]]*\]\s*)+)(.*)"
                match = re.match(directive_prefix_pattern, line_stripped)

                if match:
                    directive_text = match.group(1)
                    remaining_text = match.group(2).strip()

                    # Parse the directive text
                    directives = self.directive_parser._parse_directive_text(
                        directive_text
                    )

                    if directives:
                        all_directives.update(directives)
                        logger.debug(
                            f"Extracted directives from mixed content line: {directives}"
                        )

                        # Keep the remaining text
                        if remaining_text:
                            cleaned_lines.append(remaining_text)
                        # If no remaining text, don't add anything
                    else:
                        # No valid directives found, keep the original line
                        cleaned_lines.append(line)
                else:
                    # No directives found, keep the original line
                    cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)
        return all_directives, cleaned_content, trailing_directives
