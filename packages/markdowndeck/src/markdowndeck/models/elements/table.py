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

        # Calculate current element width to determine row heights
        element_width = self.size[0] if self.size else 400.0  # fallback width

        # Create temporary table with just headers to measure header height
        header_height = 0.0
        if self.headers:
            temp_header_table = deepcopy(self)
            temp_header_table.rows = []
            # Local import to avoid circular dependency
            from markdowndeck.layout.metrics import calculate_element_height

            header_height = calculate_element_height(temp_header_table, element_width)

        # Check if even headers don't fit
        if header_height > available_height:
            return None, deepcopy(self)

        # Find how many rows fit within available height (after accounting for headers)
        available_for_rows = available_height - header_height
        fitted_rows = []

        for _i, row in enumerate(self.rows):
            # Create temporary element with current rows to measure height
            temp_element = deepcopy(self)
            temp_element.rows = fitted_rows + [row]

            # Calculate height this would require (minus header height since we already accounted for it)
            # Local import to avoid circular dependency
            from markdowndeck.layout.metrics import calculate_element_height

            full_height = calculate_element_height(temp_element, element_width)
            rows_height = full_height - header_height

            if rows_height <= available_for_rows:
                fitted_rows.append(row)
            else:
                # This row doesn't fit
                break

        # Determine split results
        if not fitted_rows and not self.headers:
            # Nothing fits and no headers
            return None, deepcopy(self)

        if len(fitted_rows) == len(self.rows):
            # Everything fits
            return deepcopy(self), None

        # Create fitted part
        fitted_part = deepcopy(self)
        fitted_part.rows = fitted_rows

        # Calculate actual size for fitted part
        if fitted_rows or self.headers:
            # Local import to avoid circular dependency
            from markdowndeck.layout.metrics import calculate_element_height

            fitted_height = calculate_element_height(fitted_part, element_width)
            fitted_part.size = (element_width, fitted_height)
        else:
            return None, deepcopy(self)

        # Create overflowing part with header duplication
        if len(fitted_rows) < len(self.rows):
            overflowing_rows = self.rows[len(fitted_rows) :]
            overflowing_part = deepcopy(self)
            overflowing_part.rows = overflowing_rows

            # CRITICAL: Always duplicate headers in overflowing part
            if self.headers:
                overflowing_part.headers = deepcopy(self.headers)

            return fitted_part, overflowing_part

        return fitted_part, None

    def requires_header_duplication(self) -> bool:
        """
        Check if this table would require header duplication when split.

        Returns:
            True if the table has headers that should be duplicated
        """
        return bool(self.headers)
