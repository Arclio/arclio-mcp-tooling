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


def calculate_text_element_height(element: TextElement | Element, available_width: float) -> float:
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
        return 40  # Minimum height for empty text

    text = element.text

    # Base parameters
    min_height = 50 if element.element_type == ElementType.QUOTE else 40
    base_padding = 20  # Base padding for all text elements
    line_height = 22  # Height per line of text

    # Count explicit line breaks
    explicit_lines = text.count("\n") + 1

    # Calculate wrapping based on character count and available width
    avg_char_width = 9  # Average character width in points (approximate)
    chars_per_line = max(1, int(available_width / avg_char_width))

    # Different approaches for word-based vs character-based wrapping
    # Word-based wrapping (more accurate but slower)
    words = text.split()
    line_count = 1
    current_line_length = 0

    for word in words:
        word_length = len(word) * avg_char_width
        # Add word to current line if it fits, otherwise start a new line
        if current_line_length + word_length <= available_width:
            current_line_length += word_length + avg_char_width  # Add space
        else:
            line_count += 1
            current_line_length = word_length

    # Alternative character-based calculation (simpler)
    char_based_lines = max(1, len(text) / chars_per_line)

    # Use the maximum of all approaches for safety
    calculated_lines = max(explicit_lines, line_count, char_based_lines)

    # Add extra height for formatting
    if hasattr(element, "formatting") and element.formatting:
        # Formatted text sometimes needs more height
        calculated_lines = calculated_lines * 1.1

    # Add extra height for quotes
    if element.element_type == ElementType.QUOTE:
        base_padding += 10  # Extra padding for quotes

    # Add extra height for titles
    if element.element_type == ElementType.TITLE:
        base_padding += 15  # Extra padding for titles
        line_height = 28  # Titles have larger line height
    elif element.element_type == ElementType.SUBTITLE:
        base_padding += 5  # Some extra padding for subtitles
        line_height = 24  # Subtitles have larger line height

    # Calculate final height with padding
    height = (calculated_lines * line_height) + base_padding

    # Ensure minimum height
    return max(height, min_height)


def calculate_list_element_height(element: ListElement | Element, available_width: float) -> float:
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
        return 40  # Minimum height for empty list

    items = getattr(element, "items", [])

    # Calculate list height based on number of items and nesting
    total_height = 0
    max(1, int(available_width / 9))  # 9px per char

    # Function to calculate item height recursively
    def calculate_item_height(item, level=0):
        # Base height for the item
        item_height = 30

        # Add indent based on level
        indent_width = level * 20
        item_width = available_width - indent_width
        item_chars_per_line = max(1, int(item_width / 9))

        # Calculate lines based on text length
        text_length = len(item.text)
        line_count = max(1, text_length / item_chars_per_line)

        # Add height for text including wrapping
        item_height += (line_count - 1) * 20

        # Process children recursively
        for child in item.children:
            item_height += calculate_item_height(child, level + 1)

        return item_height

    # Calculate height for all items
    for item in items:
        total_height += calculate_item_height(item)

    # Add padding
    total_height += 20

    # Minimum height
    return max(total_height, 40)


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
        return 60  # Minimum height for empty table

    headers = getattr(element, "headers", [])
    rows = getattr(element, "rows", [])

    # Calculate table dimensions
    len(rows)
    col_count = max(len(headers) if headers else 0, max(len(row) for row in rows) if rows else 0)

    if col_count == 0:
        return 60  # Minimum height for empty table

    # Calculate cell width
    cell_width = (available_width - 10) / col_count  # Subtract border width

    # Base height calculation
    header_height = 30 if headers else 0
    row_height = 0

    # Calculate row heights based on content
    for row in rows:
        max_cell_height = 30  # Minimum cell height

        for cell_idx, cell in enumerate(row):
            if cell_idx >= col_count:
                break

            # Calculate cell text height
            cell_text = str(cell)
            chars_per_line = max(1, int(cell_width / 9))
            lines = max(1, len(cell_text) / chars_per_line)
            cell_height = 20 + (lines - 1) * 15  # 20pt base height + extra for lines

            max_cell_height = max(max_cell_height, cell_height)

        row_height += max_cell_height

    # Total height with padding
    total_height = header_height + row_height + 40  # Add padding

    return max(total_height, 60)  # Minimum table height


def calculate_code_element_height(element: CodeElement | Element, available_width: float) -> float:
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
        return 60  # Minimum height for empty code block

    code = getattr(element, "code", "")

    # Count lines
    lines = code.count("\n") + 1

    # Calculate if lines need wrapping
    chars_per_line = max(1, int((available_width - 40) / 7.5))  # Code uses monospace font
    wrapped_lines = 0

    for line in code.split("\n"):
        line_length = len(line)
        if line_length > chars_per_line:
            # Calculate wrapped lines for this line
            wrapped_lines += (line_length / chars_per_line) - 1

    total_lines = lines + wrapped_lines

    # Calculate height based on lines + padding
    height = (total_lines * 18) + 40  # 18pt per line + padding

    return max(height, 60)  # Minimum code height
