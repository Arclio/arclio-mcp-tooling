import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.elements.base import Element

logger = logging.getLogger(__name__)


@dataclass
class TableElement(Element):
    """Table element with simple splitting logic."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    # ADDED: `column_widths` attribute per DATA_MODELS.md
    column_widths: list[float] | None = None
    # ADDED: `row_directives` attribute per DATA_MODELS.md
    row_directives: list[dict[str, Any]] = field(default_factory=list)

    def get_column_count(self) -> int:
        """Get the number of columns in the table."""
        if self.headers:
            return len(self.headers)
        if self.rows:
            return max(len(row) for row in self.rows) if self.rows else 0
        return 0

    def get_row_count(self) -> int:
        """Get the number of rows in the table, including header."""
        count = len(self.rows)
        if self.headers:
            count += 1
        return count

    def validate(self) -> bool:
        """Validate the table structure."""
        if not self.headers and not self.rows:
            return False

        column_count = self.get_column_count()
        if column_count == 0:
            return False

        return all(len(row) <= column_count for row in self.rows)

    def split(
        self, available_height: float
    ) -> tuple["TableElement | None", "TableElement | None"]:
        """
        Split this TableElement using minimum requirements.

        Rule: Must fit header + at least 1 data row to split.
        If minimum met, splits what fits. If not, promotes entire table.
        """
        if not self.rows and not self.headers:
            return None, None

        from markdowndeck.layout.metrics.table import calculate_row_height

        element_width = self.size[0] if self.size else 400.0
        num_cols = self.get_column_count()
        if num_cols == 0:
            return deepcopy(self), None
        col_width = element_width / num_cols

        header_height = 0.0
        if self.headers:
            header_height = calculate_row_height(
                self.headers, col_width, is_header=True
            )

        available_for_rows = available_height - header_height
        if available_for_rows <= 0 and self.headers:
            logger.debug("No space available for data rows after header")
            return None, deepcopy(self)

        fitted_rows_count = 0
        current_rows_height = 0.0
        for _i, row in enumerate(self.rows):
            next_row_height = calculate_row_height(row, col_width, is_header=False)
            if current_rows_height + next_row_height <= available_for_rows:
                current_rows_height += next_row_height
                fitted_rows_count += 1
            else:
                break

        if fitted_rows_count == len(self.rows):
            return deepcopy(self), None

        minimum_rows_required = 1
        if self.headers and fitted_rows_count < minimum_rows_required:
            logger.info(
                f"Table split rejected: Only {fitted_rows_count} rows fit, need minimum {minimum_rows_required} with header."
            )
            return None, deepcopy(self)
        if fitted_rows_count == 0 and not self.headers:
            return None, deepcopy(self)

        fitted_part = deepcopy(self)
        fitted_part.rows = self.rows[:fitted_rows_count]
        fitted_part.size = (element_width, header_height + current_rows_height)

        header_offset = 1 if self.headers else 0
        fitted_part.row_directives = self.row_directives[
            : header_offset + fitted_rows_count
        ]

        overflowing_rows = self.rows[fitted_rows_count:]
        if not overflowing_rows:
            return fitted_part, None

        overflowing_part = deepcopy(self)
        overflowing_part.rows = overflowing_rows
        overflowing_part.position = None
        # REFACTORED: `split` contract requires deep-copy of `column_widths`.
        overflowing_part.column_widths = deepcopy(self.column_widths)
        # REFACTORED: Correctly partition row_directives per `split` contract.
        overflowing_part.row_directives = self.row_directives[
            header_offset + fitted_rows_count :
        ]
        if self.headers:
            overflowing_part.headers = deepcopy(self.headers)
            # Prepend the header directive to the overflowing part's directives
            if self.row_directives:
                overflowing_part.row_directives.insert(0, self.row_directives[0])

        overflow_header_height = (
            calculate_row_height(overflowing_part.headers, col_width, is_header=True)
            if overflowing_part.headers
            else 0
        )
        overflow_rows_height = sum(
            calculate_row_height(row, col_width, is_header=False)
            for row in overflowing_rows
        )
        overflowing_part.size = (
            element_width,
            overflow_header_height + overflow_rows_height,
        )

        logger.info(
            f"Table split successful: {fitted_rows_count} rows fitted, {len(overflowing_rows)} rows overflowing"
        )
        return fitted_part, overflowing_part
