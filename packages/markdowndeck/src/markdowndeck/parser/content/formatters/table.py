import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element
from markdowndeck.parser.content.formatters.base import BaseFormatter
from markdowndeck.parser.directive import DirectiveParser

logger = logging.getLogger(__name__)


class TableFormatter(BaseFormatter):
    """Formatter for table elements."""

    def __init__(self, element_factory):
        super().__init__(element_factory)
        self.directive_parser = DirectiveParser()

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type == "table_open"

    def process(
        self,
        tokens: list[Token],
        start_index: int,
        section_directives: dict[str, Any],
        element_specific_directives: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[list[Element], int]:
        """Create a table element from tokens, handling row directives."""
        merged_directives = self.merge_directives(section_directives, element_specific_directives)

        end_index = self.find_closing_token(tokens, start_index, "table_close")

        headers: list[str] = []
        rows: list[list[str]] = []
        row_directives: list[dict[str, Any]] = []

        i = start_index + 1
        in_header = False
        while i < end_index:
            token = tokens[i]
            if token.type == "thead_open":
                in_header = True
            elif token.type == "thead_close":
                in_header = False
            elif token.type == "tr_open":
                cells, directives = self._process_row(tokens, i + 1, end_index)

                # REFACTORED: Handle directive-only rows for header styling
                is_directive_row = all(not cell for cell in cells) and directives
                if is_directive_row and row_directives:
                    # Merge these directives with the previous row's
                    row_directives[-1].update(directives)
                else:
                    if in_header:
                        headers = cells
                    else:
                        rows.append(cells)
                    row_directives.append(directives)

                i = self.find_closing_token(tokens, i, "tr_close")
            i += 1

        if not headers and not rows:
            return [], end_index

        element = self.element_factory.create_table_element(
            headers=headers,
            rows=rows,
            row_directives=row_directives,
            directives=merged_directives.copy(),
        )
        return [element], end_index

    def _process_row(self, tokens: list[Token], start_index: int, table_end_index: int) -> tuple[list[str], dict[str, Any]]:
        """Process a single table row (tr) to extract cells and directives."""
        cells: list[str] = []
        row_directives: dict[str, Any] = {}
        i = start_index
        row_end_index = self.find_closing_token(tokens, start_index - 1, "tr_close")

        while i < row_end_index:
            token = tokens[i]
            if token.type in ["th_open", "td_open"]:
                cell_content_idx = i + 1
                cell_text = ""
                if cell_content_idx < row_end_index and tokens[cell_content_idx].type == "inline":
                    cell_text = self._get_plain_text_from_inline_token(tokens[cell_content_idx]).strip()
                cells.append(cell_text)
            i += 1

        # The last cell is reserved for directives
        if cells:
            last_cell_content = cells.pop()
            if last_cell_content:
                _, directives = self.directive_parser.parse_and_strip_from_text(last_cell_content)
                row_directives.update(directives)

        return cells, row_directives
