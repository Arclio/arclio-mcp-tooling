"""Pure list element metrics for layout calculations - Content-aware height calculation."""

import logging
from typing import cast

from markdowndeck.layout.constants import (
    LIST_BULLET_WIDTH,
    # List specific constants
    LIST_INDENT_PER_LEVEL,
    LIST_ITEM_SPACING,
    LIST_PADDING,
    MIN_LIST_HEIGHT,
)
from markdowndeck.layout.metrics.text import calculate_text_element_height
from markdowndeck.models import ElementType, ListElement, ListItem, TextElement

logger = logging.getLogger(__name__)


def calculate_list_element_height(
    element: ListElement | dict, available_width: float
) -> float:
    """
    Calculate the pure intrinsic height needed for a list element based on its content.

    This is a pure measurement function that returns the actual height required
    to render all list items at the given width, including nested items.

    Args:
        element: The list element to measure
        available_width: Available width for the list

    Returns:
        The intrinsic height in points required to render the complete list
    """
    list_element = (
        cast(ListElement, element)
        if isinstance(element, ListElement)
        else ListElement(**element)
    )

    if not list_element.items:
        return MIN_LIST_HEIGHT

    # Calculate total height of all items
    total_height = 0.0

    for i, item in enumerate(list_element.items):
        item_height = _calculate_single_item_height(item, available_width, level=0)
        total_height += item_height

        # Add spacing between items (but not after the last item)
        if i < len(list_element.items) - 1:
            total_height += LIST_ITEM_SPACING

    # Add top and bottom padding for the entire list
    total_height += LIST_PADDING * 2

    # Apply minimum height
    final_height = max(total_height, MIN_LIST_HEIGHT)

    logger.debug(
        f"List height calculation: items={len(list_element.items)}, "
        f"width={available_width:.1f}, final_height={final_height:.1f}"
    )

    return final_height


def _calculate_single_item_height(
    item: ListItem, available_width: float, level: int
) -> float:
    """
    Calculate the height required for a single list item and all its children.

    Args:
        item: The list item to measure
        available_width: Available width for this item
        level: Nesting level (0 = top level)

    Returns:
        Total height needed for this item and its children
    """
    # Calculate available width for this item's text (accounting for indentation)
    indent_width = level * LIST_INDENT_PER_LEVEL
    bullet_width = LIST_BULLET_WIDTH
    item_text_width = max(10.0, available_width - indent_width - bullet_width)

    # Use text metrics to calculate height for this item's text
    temp_text_element = TextElement(
        element_type=ElementType.TEXT,
        text=item.text,
        formatting=getattr(item, "formatting", []),
    )

    item_text_height = calculate_text_element_height(temp_text_element, item_text_width)

    # Start with this item's text height
    total_item_height = item_text_height

    # Add height for children if they exist
    if hasattr(item, "children") and item.children:
        # Calculate available width for children (additional indentation)
        child_available_width = max(10.0, item_text_width - LIST_INDENT_PER_LEVEL)

        for j, child_item in enumerate(item.children):
            child_height = _calculate_single_item_height(
                child_item, child_available_width, level + 1
            )
            total_item_height += child_height

            # Add spacing between child items (but not after the last one)
            if j < len(item.children) - 1:
                total_item_height += LIST_ITEM_SPACING

    return total_item_height


def calculate_list_item_content_width(
    available_width: float, nesting_level: int
) -> float:
    """
    Calculate the available width for list item content at a given nesting level.

    Args:
        available_width: Total available width
        nesting_level: How deeply nested this item is (0 = top level)

    Returns:
        Available width for the item's text content
    """
    total_indent = nesting_level * LIST_INDENT_PER_LEVEL
    bullet_space = LIST_BULLET_WIDTH

    content_width = available_width - total_indent - bullet_space
    return max(10.0, content_width)  # Ensure minimum readable width


def estimate_list_items_count(list_element: ListElement | dict) -> int:
    """
    Count the total number of items in a list, including nested items.

    Args:
        list_element: The list element to count

    Returns:
        Total number of items (including nested)
    """
    items = (
        list_element.get("items", [])
        if isinstance(list_element, dict)
        else getattr(list_element, "items", [])
    )

    if not items:
        return 0

    total_count = len(items)

    # Count nested items recursively
    for item in items:
        if hasattr(item, "children") and item.children:
            # Create a temporary list element for the children
            child_list = {"items": item.children}
            total_count += estimate_list_items_count(child_list)

    return total_count


def get_max_nesting_depth(list_element: ListElement | dict) -> int:
    """
    Determine the maximum nesting depth in a list.

    Args:
        list_element: The list element to analyze

    Returns:
        Maximum nesting depth (1 = no nesting, 2 = one level of nesting, etc.)
    """
    items = (
        list_element.get("items", [])
        if isinstance(list_element, dict)
        else getattr(list_element, "items", [])
    )

    if not items:
        return 0

    max_depth = 1  # At least one level

    for item in items:
        if hasattr(item, "children") and item.children:
            # Create a temporary list element for the children
            child_list = {"items": item.children}
            child_depth = get_max_nesting_depth(child_list)
            max_depth = max(max_depth, 1 + child_depth)

    return max_depth
