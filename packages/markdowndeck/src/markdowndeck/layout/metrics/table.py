"""Pure table element metrics for layout calculations - Content-aware height calculation."""

import logging
from typing import cast

from markdowndeck.layout.constants import (
    # Minimum dimensions
    MIN_TABLE_HEIGHT,
    TABLE_CELL_PADDING,
    TABLE_HEADER_HEIGHT,
    TABLE_PADDING,
    # Table specific constants
    TABLE_ROW_HEIGHT,
)
from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import ElementType, TableElement, TextElement

logger = logging.getLogger(__name__)


def calculate_table_element_height(
    element: TableElement | dict, available_width: float
) -> float:
    """
    Calculate the pure intrinsic height needed for a table element based on its content.

    This is a pure measurement function that returns the actual height required
    to render the complete table with all rows and columns at the given width.

    Args:
        element: The table element to measure
        available_width: Available width for the table

    Returns:
        The intrinsic height in points required to render the complete table
    """
    table_element = (
        cast(TableElement, element)
        if isinstance(element, TableElement)
        else TableElement(**element)
    )

    if not table_element.rows and not table_element.headers:
        return MIN_TABLE_HEIGHT

    # Determine number of columns
    num_cols = table_element.get_column_count()
    if num_cols == 0:
        return MIN_TABLE_HEIGHT

    # Calculate column widths (equal distribution)
    table_border_space = 4.0  # Space for table borders
    effective_table_width = max(20.0, available_width - table_border_space)
    col_width = effective_table_width / num_cols

    total_height = 0.0

    # Calculate header height if headers exist
    if table_element.headers:
        header_height = calculate_row_height(
            table_element.headers, col_width, is_header=True
        )
        total_height += header_height
        logger.debug(f"Header row height: {header_height:.1f}")

    # Calculate data rows height
    for i, row_data in enumerate(table_element.rows):
        row_height = calculate_row_height(row_data, col_width, is_header=False)
        total_height += row_height
        logger.debug(f"Data row {i} height: {row_height:.1f}")

    # Add table padding
    total_height += TABLE_PADDING * 2  # Top and bottom padding

    # Apply minimum height
    final_height = max(total_height, MIN_TABLE_HEIGHT)

    logger.debug(
        f"Table height calculation: cols={num_cols}, "
        f"header_rows={1 if table_element.headers else 0}, "
        f"data_rows={len(table_element.rows)}, "
        f"width={available_width:.1f}, final_height={final_height:.1f}"
    )

    return final_height


def calculate_row_height(
    row_data: list, col_width: float, is_header: bool = False
) -> float:
    """
    Calculate the height required for a single table row.

    Args:
        row_data: List of cell contents for this row
        col_width: Width available for each column
        is_header: Whether this is a header row

    Returns:
        Height needed for this row
    """
    if not row_data:
        return TABLE_HEADER_HEIGHT if is_header else TABLE_ROW_HEIGHT

    # Calculate cell content width (subtract cell padding)
    cell_content_width = max(10.0, col_width - (TABLE_CELL_PADDING * 2))

    # Find the tallest cell in this row
    max_cell_height = 0.0

    for cell_content in row_data:
        cell_text = str(cell_content) if cell_content is not None else ""

        if cell_text.strip():
            # Use text metrics to calculate cell content height
            temp_text_element = TextElement(
                element_type=ElementType.TEXT, text=cell_text
            )
            cell_content_height = calculate_text_element_height(
                temp_text_element, cell_content_width
            )
        else:
            # Empty cell still needs minimum height
            cell_content_height = 16.0

        # Add cell padding to content height
        total_cell_height = cell_content_height + (TABLE_CELL_PADDING * 2)
        max_cell_height = max(max_cell_height, total_cell_height)

    # Apply minimum row height
    min_row_height = TABLE_HEADER_HEIGHT if is_header else TABLE_ROW_HEIGHT
    return max(max_cell_height, min_row_height)


def calculate_table_column_widths(
    available_width: float, num_columns: int
) -> list[float]:
    """
    Calculate equal-width columns for a table.

    Args:
        available_width: Total available width for the table
        num_columns: Number of columns in the table

    Returns:
        List of column widths
    """
    if num_columns <= 0:
        return []

    # Reserve space for table borders and spacing
    table_border_space = 4.0
    effective_width = max(20.0, available_width - table_border_space)

    # Equal distribution
    col_width = effective_width / num_columns
    min_col_width = 20.0  # Minimum readable column width

    actual_col_width = max(col_width, min_col_width)

    return [actual_col_width] * num_columns


def estimate_table_content_density(table_element: TableElement | dict) -> str:
    """
    Estimate the content density of a table (light, medium, heavy).

    Args:
        table_element: The table element to analyze

    Returns:
        Content density classification
    """
    if isinstance(table_element, dict):
        headers = table_element.get("headers", [])
        rows = table_element.get("rows", [])
    else:
        headers = getattr(table_element, "headers", [])
        rows = getattr(table_element, "rows", [])

    total_cells = len(headers) + sum(len(row) for row in rows)
    if total_cells == 0:
        return "light"

    # Calculate average cell content length
    total_content_length = 0
    cell_count = 0

    for header in headers:
        total_content_length += len(str(header))
        cell_count += 1

    for row in rows:
        for cell in row:
            total_content_length += len(str(cell) if cell is not None else "")
            cell_count += 1

    if cell_count == 0:
        return "light"

    avg_content_length = total_content_length / cell_count

    if avg_content_length < 10:
        return "light"
    if avg_content_length < 30:
        return "medium"
    return "heavy"


def get_table_dimensions(table_element: TableElement | dict) -> tuple[int, int]:
    """
    Get the dimensions (rows, columns) of a table.

    Args:
        table_element: The table element to analyze

    Returns:
        (number_of_rows, number_of_columns)
    """
    if isinstance(table_element, dict):
        headers = table_element.get("headers", [])
        rows = table_element.get("rows", [])
    else:
        headers = getattr(table_element, "headers", [])
        rows = getattr(table_element, "rows", [])

    # Count columns
    num_cols = len(headers) if headers else 0
    if rows:
        max_row_cols = max(len(row) for row in rows)
        num_cols = max(num_cols, max_row_cols)

    # Count rows (headers count as one row if present)
    num_rows = len(rows)
    if headers:
        num_rows += 1

    return (num_rows, num_cols)
