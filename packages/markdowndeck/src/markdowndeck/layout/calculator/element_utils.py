"""Element positioning and grouping utilities for layout calculations."""

import logging

from markdowndeck.layout.constants import (
    VERTICAL_SPACING_REDUCTION,
)
from markdowndeck.models import (
    AlignmentType,
    Element,
    ElementType,
)

logger = logging.getLogger(__name__)


def apply_horizontal_alignment(
    element: Element,
    area_x: float,
    area_width: float,
    y_pos: float,
) -> None:
    """
    Apply horizontal alignment to an element within an area.

    Args:
        element: Element to align
        area_x: X-coordinate of the area
        area_width: Width of the area
        y_pos: Y-coordinate for the element
    """
    element_width = element.size[0]
    alignment = getattr(element, "horizontal_alignment", AlignmentType.LEFT)

    if alignment == AlignmentType.CENTER:
        x_pos = area_x + (area_width - element_width) / 2
    elif alignment == AlignmentType.RIGHT:
        x_pos = area_x + area_width - element_width
    else:  # LEFT or JUSTIFY
        x_pos = area_x

    element.position = (x_pos, y_pos)


def adjust_vertical_spacing(element: Element, spacing: float) -> float:
    """
    Adjust vertical spacing based on element relationships.

    Args:
        element: Element to check for relationship flags
        spacing: Current spacing value to adjust

    Returns:
        Adjusted spacing value
    """
    # If this element is related to the next one, reduce spacing
    if hasattr(element, "related_to_next") and element.related_to_next:
        return spacing * VERTICAL_SPACING_REDUCTION  # Reduce spacing by 30%

    # If no adjustment needed, return original spacing
    return spacing


def mark_related_elements(elements: list[Element]) -> None:
    """
    Mark related elements that should be kept together during layout and overflow.

    Args:
        elements: List of elements to process
    """
    if not elements:
        return

    # Pattern 1: Text heading followed by a list or table
    _mark_heading_and_list_pairs(elements)

    # Pattern 2: Heading followed by subheading
    _mark_heading_hierarchies(elements)

    # Pattern 3: Sequential paragraphs (consecutive text elements)
    _mark_consecutive_paragraphs(elements)

    # Pattern 4: Images followed by captions (text elements)
    _mark_image_caption_pairs(elements)


def _mark_heading_and_list_pairs(elements: list[Element]) -> None:
    """Mark heading elements followed by lists or tables as related."""
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        # Check if current is a text element (potential heading)
        # and check if next is a list or table
        if current.element_type == ElementType.TEXT and next_elem.element_type in (
            ElementType.BULLET_LIST,
            ElementType.ORDERED_LIST,
            ElementType.TABLE,
        ):
            # Mark these elements as related
            current.related_to_next = True
            next_elem.related_to_prev = True
            logger.debug(
                f"Marked elements as related: {getattr(current, 'object_id', 'unknown')} -> "
                f"{getattr(next_elem, 'object_id', 'unknown')}"
            )


def _mark_heading_hierarchies(elements: list[Element]) -> None:
    """Mark hierarchical headings (heading followed by subheading) as related."""
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if (
            current.element_type == ElementType.TEXT
            and next_elem.element_type == ElementType.TEXT
            and hasattr(current, "text")
            and hasattr(next_elem, "text")
            and current.text
            and next_elem.text
        ):
            # Check if current looks like a heading (starts with #, ##, etc)
            current_text = current.text.strip()
            next_text = next_elem.text.strip()

            # Simple heuristic: if both start with # and current has fewer #s,
            # consider them related (heading + subheading)
            if (
                current_text.startswith("#")
                and next_text.startswith("#")
                and current_text.count("#") < next_text.count("#")
            ):
                current.related_to_next = True
                next_elem.related_to_prev = True
                logger.debug(
                    f"Marked heading and subheading as related: "
                    f"{getattr(current, 'object_id', 'unknown')} -> "
                    f"{getattr(next_elem, 'object_id', 'unknown')}"
                )


def _mark_consecutive_paragraphs(elements: list[Element]) -> None:
    """Mark consecutive paragraph elements as related."""
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if (
            current.element_type == ElementType.TEXT
            and next_elem.element_type == ElementType.TEXT
            and hasattr(current, "text")
            and hasattr(next_elem, "text")
            and not current.text.strip().startswith("#")
            and not next_elem.text.strip().startswith("#")
        ):
            # Mark consecutive paragraphs as related
            current.related_to_next = True
            next_elem.related_to_prev = True
            logger.debug(
                f"Marked consecutive paragraphs as related: "
                f"{getattr(current, 'object_id', 'unknown')} -> "
                f"{getattr(next_elem, 'object_id', 'unknown')}"
            )


def _mark_image_caption_pairs(elements: list[Element]) -> None:
    """Mark images followed by text elements (likely captions) as related."""
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if current.element_type == ElementType.IMAGE and next_elem.element_type == ElementType.TEXT:
            # Mark image and caption as related
            current.related_to_next = True
            next_elem.related_to_prev = True
            # Improve caption positioning
            if hasattr(next_elem, "directives"):
                next_elem.directives["caption"] = True
            logger.debug(
                f"Marked image and caption as related: "
                f"{getattr(current, 'object_id', 'unknown')} -> "
                f"{getattr(next_elem, 'object_id', 'unknown')}"
            )
