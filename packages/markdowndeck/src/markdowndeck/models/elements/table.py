"""Table element models."""

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
