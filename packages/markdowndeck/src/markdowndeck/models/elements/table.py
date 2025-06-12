import logging
from copy import deepcopy
from dataclasses import dataclass, field

from markdowndeck.models.elements.base import Element

logger = logging.getLogger(__name__)


@dataclass
class TableElement(Element):
    """Table element with simple splitting logic."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def get_column_count(self) -> int:
        """Get the number of columns in the table."""
        if self.headers:
            return len(self.headers)
        if self.rows:
            return max(len(row) for row in self.rows)
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
        Split this TableElement using simple minimum requirements.

        Rule: Must fit header + at least 2 data rows to split.
        If minimum not met, promote entire table to next slide.
        If minimum met, split off what fits.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
        """
        if not self.rows and not self.headers:
            return None, None

        # REFACTORED: Use public `calculate_row_height` function for testability.
        from markdowndeck.layout.metrics.table import calculate_row_height

        element_width = self.size[0] if self.size else 400.0
        num_cols = self.get_column_count()
        if num_cols == 0:
            return deepcopy(self), None
        col_width = element_width / num_cols

        # Calculate header height
        header_height = 0.0
        if self.headers:
            header_height = calculate_row_height(
                self.headers, col_width, is_header=True
            )

        # Calculate available space for data rows
        available_for_rows = available_height - header_height
        if available_for_rows <= 0:
            logger.debug("No space available for data rows after header")
            return None, deepcopy(self)

        # Calculate how many rows can fit
        fitted_rows = []
        current_rows_height = 0.0

        for row in self.rows:
            next_row_height = calculate_row_height(row, col_width, is_header=False)
            if current_rows_height + next_row_height <= available_for_rows:
                fitted_rows.append(row)
                current_rows_height += next_row_height
            else:
                break

        # If all rows fit, no split needed
        if len(fitted_rows) == len(self.rows):
            return deepcopy(self), None

        # SIMPLE CHECK: Do we meet minimum requirement?
        minimum_rows_required = 2
        fitted_row_count = len(fitted_rows)

        if self.headers and fitted_row_count < minimum_rows_required:
            logger.info(
                f"Table split rejected: Only {fitted_row_count} rows fit, need minimum {minimum_rows_required} with header."
            )
            return None, deepcopy(self)

        # Minimum met - proceed with split
        fitted_part = deepcopy(self)
        fitted_part.rows = fitted_rows
        fitted_part.size = (element_width, header_height + current_rows_height)

        # Create the overflowing part
        overflowing_rows = self.rows[len(fitted_rows) :]
        if not overflowing_rows:
            return fitted_part, None

        overflowing_part = deepcopy(self)
        overflowing_part.rows = overflowing_rows
        overflowing_part.position = None  # Reset position for continuation slide

        # FIXED: Ensure headers are duplicated on the overflow part for consistency.
        if self.headers:
            overflowing_part.headers = deepcopy(self.headers)

        # Recalculate size for the overflowing part
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
            f"Table split successful: {fitted_row_count} rows fitted, {len(overflowing_rows)} rows overflowing"
        )
        return fitted_part, overflowing_part

    def requires_header_duplication(self) -> bool:
        """Check if this table would require header duplication when split."""
        return bool(self.headers)
