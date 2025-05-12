"""Element sizing metrics for layout calculations."""

import logging

from markdowndeck.models import (
    CodeElement,
    Element,
    ElementType,
    ListElement,
    TableElement,
    TextElement,
)

logger = logging.getLogger(__name__)


def calculate_element_height(element: Element, available_width: float) -> float:
    """
    Calculate the height needed for an element based on its content and type.

    Args:
        element: The element to calculate height for
        available_width: The available width for the element

    Returns:
        The calculated height in points
    """
    # Dispatch to specific handler based on element type
    if element.element_type in (
        ElementType.TEXT,
        ElementType.QUOTE,
        ElementType.TITLE,
        ElementType.SUBTITLE,
        ElementType.FOOTER,
    ):
        return calculate_text_element_height(element, available_width)
    if element.element_type in (ElementType.BULLET_LIST, ElementType.ORDERED_LIST):
        return calculate_list_element_height(element, available_width)
    if element.element_type == ElementType.TABLE:
        return calculate_table_element_height(element, available_width)
    if element.element_type == ElementType.CODE:
        return calculate_code_element_height(element, available_width)
    if element.element_type == ElementType.IMAGE:
        # Image elements typically have fixed size
        return element.size[1] if hasattr(element, "size") and element.size else 200
    # Default minimum height for unknown element types
    return 80


def calculate_text_element_height(
    element: TextElement | Element, available_width: float
) -> float:
    """
    Calculate height needed for a text element.

    Args:
        element: The text element
        available_width: Available width in points

    Returns:
        Calculated height in points
    """
    # Safety check for empty text
    if not hasattr(element, "text") or not element.text:
        return 20  # Minimum height for empty text

    text = element.text

    # For footers, strip HTML comments (speaker notes)
    if element.element_type == ElementType.FOOTER:
        import re

        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        # Use a fixed height for footers regardless of content
        return 30.0  # Fixed footer height

    # FIXED: Reduced padding and more efficient sizing parameters
    if element.element_type == ElementType.TITLE:
        avg_char_width_pt = 5.5  # More realistic character width (reduced from 6.0)
        line_height_pt = 20.0  # Reduced from 24pt
        padding_pt = 5.0  # Reduced from 8pt
        min_height = 30.0  # Reduced from 40pt
    elif element.element_type == ElementType.SUBTITLE:
        avg_char_width_pt = 5.0  # Reduced from 5.5pt
        line_height_pt = 18.0  # Reduced from 20pt
        padding_pt = 4.0  # Reduced from 6pt
        min_height = 25.0  # Reduced from 35pt
    elif element.element_type == ElementType.QUOTE:
        avg_char_width_pt = 5.0  # Unchanged
        line_height_pt = 16.0  # Reduced from 18pt
        padding_pt = 8.0  # Reduced from 10pt
        min_height = 25.0  # Reduced from 30pt
    else:  # Default for all other text elements
        avg_char_width_pt = 5.0  # Unchanged
        line_height_pt = 14.0  # Reduced from 16pt
        padding_pt = 3.0  # Reduced from 4pt
        min_height = 18.0  # Reduced from 20pt

    # FIXED: Calculate effective width with minimal internal padding
    effective_width = max(1.0, available_width - 4.0)  # Reduced from 6pt

    # FIXED: More efficient line counting algorithm
    lines = text.split("\n")
    line_count = 0

    for line in lines:
        if not line.strip():  # Empty line
            line_count += 1
        else:
            # Calculate characters per line based on available width
            chars_per_line = max(1, int(effective_width / avg_char_width_pt))

            # Simple line wrapping calculation
            text_length = len(line)
            lines_needed = (
                text_length + chars_per_line - 1
            ) // chars_per_line  # Ceiling division
            line_count += lines_needed

    # FIXED: Minimal adjustments for formatting
    if hasattr(element, "formatting") and element.formatting:
        line_count *= 1.02  # Very minor increase (reduced from 1.05)

    # Calculate final height with minimal padding
    calculated_height = (line_count * line_height_pt) + padding_pt

    # Apply reasonable min/max constraints based on element type
    if element.element_type == ElementType.TITLE:
        max_height = 60.0
    elif element.element_type == ElementType.SUBTITLE:
        max_height = 50.0
    elif element.element_type == ElementType.QUOTE:
        max_height = 120.0
    else:
        max_height = 250.0  # Reduced from 300pt for normal text

    final_height = max(min_height, min(calculated_height, max_height))

    return final_height


def calculate_list_element_height(
    element: ListElement | Element, available_width: float
) -> float:
    """
    Calculate height needed for a list element.

    Args:
        element: The list element
        available_width: Available width in points

    Returns:
        Calculated height in points
    """
    # Safety check
    if not hasattr(element, "items") or not element.items:
        return 20  # Minimum height for empty list

    items = getattr(element, "items", [])

    # FIXED: More efficient list height calculation
    total_height = 0
    base_item_height = 24  # Reduced from 30
    item_spacing = 4  # Reduced from 5
    child_indent = 16  # Reduced from 20

    # Calculate height based on number of items and nesting
    for item in items:
        # Calculate height for this item
        item_height = base_item_height

        # Add height for text based on potential wrapping
        text_length = len(item.text)
        chars_per_line = max(
            1, int(available_width / 5.0)
        )  # Assuming 5pt per character
        lines_needed = (text_length + chars_per_line - 1) // chars_per_line
        item_height += (lines_needed - 1) * 14  # Add height for wrapped lines

        # Add height of children (with reduced spacing)
        if item.children:
            for child in item.children:
                # Simpler calculation for children
                child_text_length = len(child.text)
                child_width = available_width - child_indent
                child_chars_per_line = max(1, int(child_width / 5.0))
                child_lines = (
                    child_text_length + child_chars_per_line - 1
                ) // child_chars_per_line
                child_height = 22 + (
                    (child_lines - 1) * 14
                )  # Base height + wrapped lines

                item_height += child_height + (item_spacing / 2)

        total_height += item_height + item_spacing

    # Remove spacing after the last item
    if total_height > 0:
        total_height -= item_spacing

    # Add minimal padding
    total_height += 10  # Reduced from 20

    # Ensure minimum height
    return max(total_height, 30.0)


def calculate_table_element_height(
    element: TableElement | Element, available_width: float
) -> float:
    """
    Calculate height needed for a table element.

    Args:
        element: The table element
        available_width: Available width in points

    Returns:
        Calculated height in points
    """
    # Safety check
    if not hasattr(element, "rows") or not element.rows:
        return 40  # Minimum height for empty table (reduced from 60)

    headers = getattr(element, "headers", [])
    rows = getattr(element, "rows", [])

    # Calculate table dimensions
    row_count = len(rows)
    col_count = max(
        len(headers) if headers else 0, max(len(row) for row in rows) if rows else 0
    )

    if col_count == 0:
        return 40  # Minimum height (reduced from 60)

    # FIXED: More efficient table height calculation
    # Calculate cell width
    cell_width = (
        available_width - 8
    ) / col_count  # Reduced border allowance from 10pt to 8pt

    # Base height calculation with reduced padding
    header_height = headers and 25 or 0  # Reduced from 30pt
    row_height = 0

    # Calculate row heights with reduced space per row
    for row in rows:
        max_cell_height = 22  # Reduced minimum cell height from 30pt

        for cell_idx, cell in enumerate(row):
            if cell_idx >= col_count:
                break

            # Calculate cell text height more efficiently
            cell_text = str(cell)
            chars_per_line = max(1, int(cell_width / 5.0))  # Assuming 5pt per character
            lines_needed = (len(cell_text) + chars_per_line - 1) // chars_per_line
            cell_height = 18 + (
                (lines_needed - 1) * 14
            )  # Base + wrapped lines (reduced from 20pt)

            max_cell_height = max(max_cell_height, cell_height)

        row_height += max_cell_height

    # Total height with minimal padding
    total_height = header_height + row_height + 20  # Reduced padding from 40pt to 20pt

    return max(total_height, 40)  # Minimum table height (reduced from 60pt)


def calculate_code_element_height(
    element: CodeElement | Element, available_width: float
) -> float:
    """
    Calculate height needed for a code element.

    Args:
        element: The code element
        available_width: Available width in points

    Returns:
        Calculated height in points
    """
    # Safety check
    if not hasattr(element, "code") or not element.code:
        return 40  # Minimum height (reduced from 60)

    code = getattr(element, "code", "")

    # FIXED: More efficient code height calculation
    # Count lines
    lines = code.count("\n") + 1

    # Calculate wrapping with reduced internal padding
    chars_per_line = max(
        1, int((available_width - 20) / 7.5)
    )  # Reduced padding from 40pt

    # More efficient line wrapping calculation
    wrapped_lines = 0
    for line in code.split("\n"):
        line_length = len(line)
        if line_length > chars_per_line:
            # Calculate wrapped lines using integer division
            wrapped_lines += (line_length - 1) // chars_per_line

    total_lines = lines + wrapped_lines

    # Calculate height with reduced padding
    height = (total_lines * 16) + 20  # Reduced line height from 18pt, padding from 40pt

    return max(height, 40)  # Minimum code height (reduced from 60pt)
