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

    This function calculates the intrinsic height an element needs for its content,
    given an available width. It does not apply any overflow constraints or scaling
    to fit within slide boundaries.

    Args:
        element: The element to calculate height for
        available_width: The available width for the element

    Returns:
        The calculated height in points (intrinsic height based on content)
    """
    # Handle None input gracefully
    if element is None:
        return 60.0  # Default fallback height

    # Handle elements without element_type attribute
    if not hasattr(element, "element_type"):
        return 60.0  # Default fallback height

    # Dispatch to specific optimized metric functions based on element type
    if element.element_type in (
        ElementType.TEXT,
        ElementType.QUOTE,
        ElementType.TITLE,
        ElementType.SUBTITLE,
        ElementType.FOOTER,
    ):
        # Use specialized text metrics
        from markdowndeck.layout.metrics.text import calculate_text_element_height

        return calculate_text_element_height(element, available_width)

    if element.element_type in (ElementType.BULLET_LIST, ElementType.ORDERED_LIST):
        # Use specialized list metrics
        from markdowndeck.layout.metrics.list import calculate_list_element_height

        return calculate_list_element_height(element, available_width)

    if element.element_type == ElementType.TABLE:
        # Use specialized table metrics
        from markdowndeck.layout.metrics.table import calculate_table_element_height

        return calculate_table_element_height(element, available_width)

    if element.element_type == ElementType.CODE:
        # Use specialized code metrics
        from markdowndeck.layout.metrics.code import calculate_code_element_height

        return calculate_code_element_height(element, available_width)

    if element.element_type == ElementType.IMAGE:
        # Use specialized image metrics with aspect ratio awareness
        from markdowndeck.layout.metrics.image import calculate_image_element_height

        # Calculate height based on available width and maintaining aspect ratio
        # Get available height from parent section if possible
        available_height = 0
        if hasattr(element, "_section_height"):
            available_height = element._section_height
        elif hasattr(element, "_parent_height"):
            available_height = element._parent_height

        return calculate_image_element_height(
            element, available_width, available_height
        )

    # Default height for unknown element types
    return 60


# Fallback implementations for when specialized metric modules are not available


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
    # Import specialized implementation if available
    try:
        from markdowndeck.layout.metrics.text import (
            calculate_text_element_height as specialized_text_height,
        )

        return specialized_text_height(element, available_width)
    except ImportError:
        pass

    # Fallback implementation
    if not hasattr(element, "text") or not element.text:
        return 20  # Minimum height for empty text

    text = element.text

    # For footers, strip HTML comments (speaker notes)
    if element.element_type == ElementType.FOOTER:
        import re

        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        return 30.0  # Fixed footer height

    # Element type specific parameters
    if element.element_type == ElementType.TITLE:
        avg_char_width_pt = 5.5
        line_height_pt = 20.0
        padding_pt = 5.0
        min_height = 30.0
    elif element.element_type == ElementType.SUBTITLE:
        avg_char_width_pt = 5.0
        line_height_pt = 18.0
        padding_pt = 4.0
        min_height = 25.0
    elif element.element_type == ElementType.QUOTE:
        avg_char_width_pt = 5.0
        line_height_pt = 16.0
        padding_pt = 8.0
        min_height = 25.0
    else:  # Default for all other text elements
        avg_char_width_pt = 5.0
        line_height_pt = 14.0
        padding_pt = 3.0
        min_height = 18.0

    # Calculate effective width
    effective_width = max(1.0, available_width - 4.0)

    # Calculate line count based on text wrapping
    lines = text.split("\n")
    line_count = 0

    for line in lines:
        if not line.strip():  # Empty line
            line_count += 1
        else:
            # Calculate characters per line based on available width
            chars_per_line = max(1, int(effective_width / avg_char_width_pt))
            text_length = len(line)
            lines_needed = (text_length + chars_per_line - 1) // chars_per_line
            line_count += lines_needed

    # Calculate final height
    calculated_height = (line_count * line_height_pt) + padding_pt

    # Apply minimum height based on element type
    return max(min_height, calculated_height)


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
    # Import specialized implementation if available
    try:
        from markdowndeck.layout.metrics.list import (
            calculate_list_element_height as specialized_list_height,
        )

        return specialized_list_height(element, available_width)
    except ImportError:
        pass

    # Fallback implementation
    if not hasattr(element, "items") or not element.items:
        return 20  # Minimum height for empty list

    items = getattr(element, "items", [])

    # Calculate height based on number of items and nesting
    total_height = 0
    base_item_height = 24
    item_spacing = 4

    for item in items:
        # Calculate height for this item
        item_height = base_item_height

        # Add height for text based on potential wrapping
        text_length = len(item.text)
        chars_per_line = max(1, int(available_width / 5.0))
        lines_needed = (text_length + chars_per_line - 1) // chars_per_line
        item_height += (lines_needed - 1) * 14

        # Add height of children if any
        if hasattr(item, "children") and item.children:
            for child in item.children:
                child_text_length = len(child.text)
                child_width = available_width - 16  # indent
                child_chars_per_line = max(1, int(child_width / 5.0))
                child_lines = (
                    child_text_length + child_chars_per_line - 1
                ) // child_chars_per_line
                child_height = 22 + ((child_lines - 1) * 14)
                item_height += child_height + (item_spacing / 2)

        total_height += item_height + item_spacing

    # Remove spacing after the last item
    if total_height > 0:
        total_height -= item_spacing

    # Add minimal padding
    total_height += 8

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
    # Import specialized implementation if available
    try:
        from markdowndeck.layout.metrics.table import (
            calculate_table_element_height as specialized_table_height,
        )

        return specialized_table_height(element, available_width)
    except ImportError:
        pass

    # Fallback implementation
    if not hasattr(element, "rows") or not element.rows:
        return 35  # Minimum height for empty table

    headers = getattr(element, "headers", [])
    rows = getattr(element, "rows", [])

    # Calculate table dimensions
    row_count = len(rows)
    col_count = max(
        len(headers) if headers else 0, max(len(row) for row in rows) if rows else 0
    )

    if col_count == 0:
        return 35

    # Base height calculation
    header_height = 22 if headers else 0
    row_height = 20
    total_height = header_height + (row_count * row_height) + 8  # Minimal padding

    return max(total_height, 35.0)


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
    # Import specialized implementation if available
    try:
        from markdowndeck.layout.metrics.code import (
            calculate_code_element_height as specialized_code_height,
        )

        return specialized_code_height(element, available_width)
    except ImportError:
        pass

    # Fallback implementation
    if not hasattr(element, "code") or not element.code:
        return 30  # Minimum height for empty code block

    code = getattr(element, "code", "")
    language = getattr(element, "language", "")

    # Parameters for code blocks
    avg_char_width_pt = 7.5
    line_height_pt = 14.0
    padding_pt = 8.0
    language_height = (
        12.0
        if language and language.lower() not in ("text", "plaintext", "plain")
        else 0
    )

    # Calculate lines of code
    effective_width = max(1.0, available_width - 12.0)
    chars_per_line = max(1, int(effective_width / avg_char_width_pt))
    lines = code.split("\n")
    line_count = 0

    for line in lines:
        if not line:  # Empty line
            line_count += 1
        else:
            text_length = len(line)
            lines_needed = (text_length + chars_per_line - 1) // chars_per_line
            line_count += lines_needed

    # Calculate final height
    calculated_height = (line_count * line_height_pt) + padding_pt + language_height

    return max(calculated_height, 35.0)
