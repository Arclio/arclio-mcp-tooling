"""Table element models."""

from copy import deepcopy
from dataclasses import dataclass, field

from markdowndeck.models.elements.base import Element


@dataclass
class TableElement(Element):
    """Table element."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def get_column_count(self) -> int:
        """
        Get the number of columns in the table.

        Returns:
            Number of columns
        """
        if self.headers:
            return len(self.headers)
        if self.rows:
            return max(len(row) for row in self.rows)
        return 0

    def get_row_count(self) -> int:
        """
        Get the number of rows in the table, including header.

        Returns:
            Number of rows including header
        """
        count = len(self.rows)
        if self.headers:
            count += 1
        return count

    def validate(self) -> bool:
        """
        Validate the table structure.

        Returns:
            True if the table is valid, False otherwise
        """
        if not self.headers and not self.rows:
            return False

        column_count = self.get_column_count()
        if column_count == 0:
            return False

        # Check if all rows have the same number of columns
        return all(len(row) <= column_count for row in self.rows)

    def split(
        self, available_height: float
    ) -> tuple["TableElement | None", "TableElement | None"]:
        """
        Split this TableElement to fit within available_height.

        Args:
            available_height: The vertical space available for this element

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
            fitted_part: Contains rows that fit within available_height
            overflowing_part: Contains rows that don't fit, with duplicated headers
        """
        if not self.rows and not self.headers:
            return None, None

        from markdowndeck.layout.metrics.table import _calculate_row_height

        element_width = self.size[0] if self.size else 400.0
        num_cols = self.get_column_count()
        if num_cols == 0:
            return deepcopy(self), None
        col_width = element_width / num_cols

        header_height = 0.0
        if self.headers:
            header_height = _calculate_row_height(
                self.headers, col_width, is_header=True
            )

        if available_height < header_height:
            return None, deepcopy(self)

        available_for_rows = available_height - header_height
        fitted_rows = []
        current_rows_height = 0.0

        for row in self.rows:
            next_row_height = _calculate_row_height(row, col_width, is_header=False)
            if current_rows_height + next_row_height <= available_for_rows:
                fitted_rows.append(row)
                current_rows_height += next_row_height
            else:
                break

        if len(fitted_rows) == len(self.rows):
            return deepcopy(self), None

        if not fitted_rows and not self.headers:
            return None, deepcopy(self)

        # If no rows fit but there's a header that fits, the fitted part is just the header.
        if not fitted_rows and self.headers and header_height <= available_height:
            fitted_part = deepcopy(self)
            fitted_part.rows = []
            fitted_part.size = (element_width, header_height)

            overflowing_part = deepcopy(self)  # The whole table overflows
            overflowing_part.headers = deepcopy(self.headers)
            # ✅ FIX: Calculate proper size for overflowing part
            overflow_rows_height = sum(
                _calculate_row_height(row, col_width, is_header=False)
                for row in self.rows
            )
            overflowing_part.size = (
                element_width,
                header_height + overflow_rows_height,
            )
            return fitted_part, overflowing_part

        if not fitted_rows:
            return None, deepcopy(self)

        fitted_part = deepcopy(self)
        fitted_part.rows = fitted_rows
        fitted_part.size = (element_width, header_height + current_rows_height)

        overflowing_rows = self.rows[len(fitted_rows) :]
        overflowing_part = deepcopy(self)
        overflowing_part.rows = overflowing_rows
        if self.headers:
            overflowing_part.headers = deepcopy(self.headers)

        # ✅ FIX: Calculate proper size for overflowing part
        overflow_rows_height = sum(
            _calculate_row_height(row, col_width, is_header=False)
            for row in overflowing_rows
        )
        overflowing_part.size = (element_width, header_height + overflow_rows_height)

        return fitted_part, overflowing_part

    def requires_header_duplication(self) -> bool:
        """
        Check if this table would require header duplication when split.

        Returns:
            True if the table has headers that should be duplicated
        """
        return bool(self.headers)
