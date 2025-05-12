"""Table formatter for content parsing."""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element

# ElementFactory will be injected via __init__ from BaseFormatter
from markdowndeck.parser.content.formatters.base import BaseFormatter

logger = logging.getLogger(__name__)


class TableFormatter(BaseFormatter):
    """Formatter for table elements."""

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type == "table_open"

    def process(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        """Create a table element from tokens."""
        table_open_token = tokens[start_index]
        if table_open_token.type != "table_open":
            logger.warning(
                f"TableFormatter received non-table_open token: {table_open_token.type} at index {start_index}"
            )
            return None, start_index

        end_index = self.find_closing_token(tokens, start_index, "table_close")

        headers: list[str] = []
        rows: list[list[str]] = []
        current_row_cells: list[str] = []
        in_header_row = False

        i = start_index + 1
        while i < end_index:
            token = tokens[i]
            if token.type == "thead_open":
                in_header_row = True
            elif token.type == "thead_close":
                in_header_row = False
            elif token.type == "tr_open":
                current_row_cells = []
            elif token.type == "tr_close":
                if current_row_cells:
                    if in_header_row:  # This should ideally only happen once for the table
                        headers = list(current_row_cells)
                    else:
                        rows.append(list(current_row_cells))
                current_row_cells = []  # Reset for next row
            elif token.type in ("th_open", "td_open"):
                # Content of a cell is in the next inline token
                cell_content_idx = i + 1
                cell_text = ""
                if cell_content_idx < end_index and tokens[cell_content_idx].type == "inline":
                    # Extract plain text from the inline token using the helper method
                    cell_text = self._get_plain_text_from_inline_token(
                        tokens[cell_content_idx]
                    ).strip()
                    i = cell_content_idx  # Advance past the inline token
                current_row_cells.append(cell_text)
                # Need to advance i past td_close/th_close as well
                cell_end_tag = "th_close" if token.type == "th_open" else "td_close"
                while i < end_index and tokens[i].type != cell_end_tag:
                    i += 1
            i += 1

        if not headers and not rows:
            logger.debug(
                f"No headers or rows found for table at index {start_index}, skipping element."
            )
            return None, end_index

        element = self.element_factory.create_table_element(
            headers=headers, rows=rows, directives=directives.copy()
        )
        logger.debug(
            f"Created table element with {len(headers)} headers and {len(rows)} rows from token index {start_index} to {end_index}"
        )
        return element, end_index
