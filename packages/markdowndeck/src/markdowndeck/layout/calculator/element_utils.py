"""Element positioning and grouping utilities for layout calculations."""

import logging

from markdowndeck.layout.constants import (
    VERTICAL_SPACING_REDUCTION,
)
from markdowndeck.models import (
    Element,
    ElementType,
)

logger = logging.getLogger(__name__)


def apply_horizontal_alignment(
    element: Element,
    area_x: float,
    area_width: float,
    y_pos: float,
    section_directives: dict = None,
) -> None:
    """
    Apply horizontal alignment to an element within an area.

    This is the unified function for all horizontal alignment logic,
    consolidating both element-level and section-level alignment directives.

    Args:
        element: Element to align
        area_x: X-coordinate of the area
        area_width: Width of the area
        y_pos: Y-coordinate for the element
        section_directives: Optional section directives to check for alignment
    """
    element_width = element.size[0]

    # Determine alignment - priority: element directives > element alignment > section directives > default
    alignment_str = None

    # First check element's own directives
    if hasattr(element, "directives") and element.directives and "align" in element.directives:
        alignment_str = element.directives["align"]
    # Then check element's horizontal_alignment attribute
    elif hasattr(element, "horizontal_alignment"):
        alignment = element.horizontal_alignment
        alignment_str = alignment.value if hasattr(alignment, "value") else str(alignment).lower()
    # Finally check section directives
    elif section_directives and "align" in section_directives:
        alignment_str = section_directives["align"]

    # Default to left if no alignment specified
    if not alignment_str:
        alignment_str = "left"

    # Normalize alignment string
    alignment_str = alignment_str.lower()

    # Calculate x position based on alignment
    if alignment_str == "center":
        x_pos = area_x + (area_width - element_width) / 2
    elif alignment_str == "right":
        x_pos = area_x + area_width - element_width
    else:  # left or justify
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
        return spacing * VERTICAL_SPACING_REDUCTION  # Reduce spacing by 40%

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
    # Disabled for now as it conflicts with test expectations
    # _mark_consecutive_paragraphs(elements)

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

        current_level = getattr(current, "directives", {}).get("heading_level")
        next_level = getattr(next_elem, "directives", {}).get("heading_level")

        if current_level is not None and next_level is not None:
            try:
                # Mark as related if the next element is a direct subheading
                if int(next_level) > int(current_level):
                    current.related_to_next = True
                    next_elem.related_to_prev = True
                    logger.debug(
                        f"Marked heading and subheading as related: "
                        f"{getattr(current, 'object_id', 'unknown')} (level {current_level}) -> "
                        f"{getattr(next_elem, 'object_id', 'unknown')} (level {next_level})"
                    )
            except (ValueError, TypeError):
                # Ignore if heading_level is not a number
                continue


def _mark_consecutive_paragraphs(elements: list[Element]) -> None:
    """Mark consecutive paragraph elements as related."""
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        # Check if either element has a heading_level directive (should not be marked as consecutive paragraphs)
        current_is_heading = hasattr(current, "directives") and current.directives and "heading_level" in current.directives
        next_is_heading = hasattr(next_elem, "directives") and next_elem.directives and "heading_level" in next_elem.directives

        if (
            current.element_type == ElementType.TEXT
            and next_elem.element_type == ElementType.TEXT
            and hasattr(current, "text")
            and hasattr(next_elem, "text")
            and not current.text.strip().startswith("#")
            and not next_elem.text.strip().startswith("#")
            and not current_is_heading  # Don't mark headings as consecutive paragraphs
            and not next_is_heading  # Don't mark headings as consecutive paragraphs
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
