"""List element metrics for layout calculations."""

import logging
from typing import cast  # Added cast

from markdowndeck.layout.metrics.text import (
    calculate_text_element_height,
)  # Use the refined text height calculator
from markdowndeck.models import (
    ElementType,
    ListElement,
    ListItem,
    TextElement,
)  # ListItem needs TextElement for text processing if complex

logger = logging.getLogger(__name__)


def calculate_list_element_height(
    element: ListElement | dict, available_width: float
) -> float:
    """
    Calculate the height needed for a list element.

    Args:
        element: The list element (or dict representation).
        available_width: Available width for the list content.

    Returns:
        Calculated height in points.
    """
    list_element = (
        cast(ListElement, element)
        if isinstance(element, ListElement)
        else ListElement(**element)
    )

    if not list_element.items:
        return 20  # Minimal height for an empty list

    total_height = 0.0
    item_spacing = 5  # Spacing between list items
    base_level_padding = 10  # Padding at the top/bottom of the list

    for item in list_element.items:
        total_height += _calculate_single_item_total_height(
            item, available_width, 0, item_spacing
        )

    # Add spacing for the last item if there are items
    if list_element.items:
        total_height -= item_spacing  # Remove extra spacing after the last item

    total_height += base_level_padding * 2  # Top and bottom padding for the whole list

    final_height = max(
        total_height, 30.0
    )  # Ensure a minimum reasonable height for a non-empty list
    logger.debug(
        f"List ({list_element.element_type}) calculated height: {final_height:.2f} for width {available_width:.2f}"
    )
    return final_height


def _calculate_single_item_total_height(
    item: ListItem, available_width: float, level: int, item_spacing: float
) -> float:
    """
    Calculates the total height for a single list item, including its text and any nested children.
    """
    indent_per_level = 20  # Points of indentation per nesting level
    current_item_indent = level * indent_per_level
    item_text_width = max(
        10.0, available_width - current_item_indent - 10
    )  # Subtract indent and some bullet padding

    # Use the text_element_height_calculator for the item's text
    # Create a temporary TextElement for height calculation
    temp_text_element = TextElement(
        element_type=ElementType.TEXT,
        text=item.text,
        formatting=item.formatting if hasattr(item, "formatting") else [],
    )
    item_text_height = calculate_text_element_height(temp_text_element, item_text_width)

    current_item_total_height = item_text_height + item_spacing

    if item.children:
        children_height = 0
        for child_item in item.children:
            children_height += _calculate_single_item_total_height(
                child_item, available_width, level + 1, item_spacing
            )
        # If there are children, the current item's spacing might already be part of the first child's height calculation
        # or we ensure there's at least some spacing before children start.
        # For simplicity, we sum them up. If the text height itself has padding, this might be generous.
        current_item_total_height += (
            children_height - item_spacing
        )  # Avoid double counting spacing if children height includes it.

    return current_item_total_height
