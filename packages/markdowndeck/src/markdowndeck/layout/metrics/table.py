"""Table element metrics for layout calculations."""

import logging
from typing import cast

from markdowndeck.layout.metrics.text import (
    calculate_text_element_height,
)  # Use the refined text height calculator
from markdowndeck.models import (
    ElementType,
    TableElement,
    TextElement,
)  # For cell height calculation

logger = logging.getLogger(__name__)


def calculate_table_element_height(element: TableElement | dict, available_width: float) -> float:
    """
    Calculate the height needed for a table element.

    Args:
        element: The table element or dict.
        available_width: Available width for the table.

    Returns:
        Calculated height in points.
    """
    table_element = (
        cast(TableElement, element)
        if isinstance(element, TableElement)
        else TableElement(**element)
    )

    if not table_element.rows and not table_element.headers:
        return 30  # Min height for an empty table shell

    num_cols = table_element.get_column_count()
    if num_cols == 0:
        return 30

    # OPTIMIZED: More efficient use of space for tables
    # Use more of the available width and reduce spacing
    effective_table_width = max(20.0, available_width - 8.0)  # Reduced from 10.0
    col_width_estimate = effective_table_width / num_cols
    # OPTIMIZED: Reduced minimum cell height
    min_cell_height = 18.0  # Reduced from 20.0
    # OPTIMIZED: Reduced cell padding
    cell_vertical_padding = 3.0  # Reduced from 5.0

    total_height = 0.0

    # Calculate header height
    if table_element.headers:
        max_header_cell_content_height = 0
        for header_text in table_element.headers:
            # Create a temporary TextElement for height calculation
            temp_text_el = TextElement(element_type=ElementType.TEXT, text=str(header_text))
            cell_content_height = calculate_text_element_height(temp_text_el, col_width_estimate)
            max_header_cell_content_height = max(
                max_header_cell_content_height, cell_content_height
            )
        total_height += max(min_cell_height, max_header_cell_content_height + cell_vertical_padding)

    # Calculate height for data rows
    for row_data in table_element.rows:
        max_row_cell_content_height = 0
        for cell_text in row_data:
            temp_text_el = TextElement(element_type=ElementType.TEXT, text=str(cell_text))
            cell_content_height = calculate_text_element_height(temp_text_el, col_width_estimate)
            max_row_cell_content_height = max(max_row_cell_content_height, cell_content_height)
        total_height += max(min_cell_height, max_row_cell_content_height + cell_vertical_padding)

    # OPTIMIZED: Reduced table padding/borders
    total_height += 8.0  # Reduced from 10.0

    # OPTIMIZED: Reduced minimum height for tables
    final_height = max(total_height, 35.0)  # Reduced from 40.0
    logger.debug(f"Table calculated height: {final_height:.2f} for width {available_width:.2f}")
    return final_height


# estimate_table_columns_width might be useful later for more sophisticated layout
# but for height calculation, a simple average is often used as a first pass.
def estimate_table_columns_width(
    col_count: int, available_width: float, has_header: bool = False
) -> list[float]:
    """
    Estimate the width for each column in a table. (Kept for potential future use)
    """
    if col_count <= 0:
        return []
    # OPTIMIZED: Reduce border allowance to gain more usable width
    col_width = (available_width - 8) / col_count  # Reduced from 10
    if has_header and col_count > 1:
        widths = [col_width] * col_count
        # OPTIMIZED: More balanced column proportions
        widths[0] = col_width * 1.15  # Reduced from 1.2
        reduction = (widths[0] - col_width) / max(
            1, (col_count - 1)
        )  # Avoid division by zero if col_count is 1
        for i in range(1, col_count):
            widths[i] -= reduction
        return [max(10.0, w) for w in widths]  # Ensure minimum width
    return [max(10.0, col_width)] * col_count
