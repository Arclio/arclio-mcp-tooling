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


def calculate_list_element_height(element: ListElement | dict, available_width: float) -> float:
    """
    Calculate the pure intrinsic height for a list, with performance caps.
    """
    list_element = cast(ListElement, element) if isinstance(element, ListElement) else ListElement(**element)

    if not list_element.items:
        return MIN_LIST_HEIGHT

    # Use a recursive helper with depth limiting
    total_height = _calculate_items_height_recursive(list_element.items, available_width, current_level=0, max_depth=10)

    # Add top and bottom padding for the entire list
    total_height += LIST_PADDING * 2

    # Apply minimum height and a reasonable overall cap to prevent extreme values
    final_height = max(total_height, MIN_LIST_HEIGHT)
    return min(final_height, 20000.0)  # Hard cap height at 20k points


def _calculate_items_height_recursive(
    items: list[ListItem], available_width: float, current_level: int, max_depth: int
) -> float:
    """Recursively calculates item heights with a hard depth limit."""
    if current_level >= max_depth:
        logger.warning(f"List nesting exceeds max_depth of {max_depth}, capping height calculation.")
        return 0  # Stop calculating height at max depth

    total_height = 0.0
    # For performance, only calculate a subset of items at each level if the list is huge
    items_to_process = items[:200]

    for i, item in enumerate(items_to_process):
        item_text_width = max(
            10.0,
            available_width - (current_level * LIST_INDENT_PER_LEVEL) - LIST_BULLET_WIDTH,
        )

        temp_text_element = TextElement(
            element_type=ElementType.TEXT,
            text=item.text,
            formatting=getattr(item, "formatting", []),
        )
        item_height = calculate_text_element_height(temp_text_element, item_text_width)

        if item.children:
            child_height = _calculate_items_height_recursive(item.children, available_width, current_level + 1, max_depth)
            item_height += child_height

        total_height += item_height
        if i < len(items_to_process) - 1:
            total_height += LIST_ITEM_SPACING

    return total_height
