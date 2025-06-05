"""Refactored zone-based layout calculations - Content-aware element positioning."""

import logging

from markdowndeck.layout.calculator.element_utils import mark_related_elements
from markdowndeck.layout.constants import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    VERTICAL_SPACING,
    VERTICAL_SPACING_REDUCTION,
)
from markdowndeck.layout.metrics import calculate_element_height
from markdowndeck.models import Slide

logger = logging.getLogger(__name__)


def calculate_zone_based_positions(calculator, slide: Slide) -> Slide:
    """
    Calculate positions using zone-based layout with content-aware sizing.

    In zone-based layout, elements are stacked vertically in the body zone.
    Each element's height is determined by its intrinsic content needs.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to calculate positions for

    Returns:
        The updated slide with positioned elements
    """
    logger.debug(f"Starting zone-based layout for slide {slide.object_id}")

    # Get body elements (header and footer already positioned)
    body_elements = calculator.get_body_elements(slide)

    if not body_elements:
        logger.debug("No body elements to position")
        return slide

    # Mark related elements for closer spacing
    mark_related_elements(body_elements)

    # Calculate intrinsic sizes for all elements first
    _calculate_element_sizes(calculator, body_elements)

    # Position elements vertically in the body zone
    _position_elements_vertically(calculator, body_elements)

    logger.debug(f"Zone-based layout completed for slide {slide.object_id}")
    return slide


def _calculate_element_sizes(calculator, elements: list) -> None:
    """
    Calculate intrinsic sizes for all elements based on their content.

    This implements Principle #2: Content-Based Sizing for elements.
    Each element's width defaults to the body zone width, and height
    is determined by content using the metrics engine.

    Args:
        calculator: The PositionCalculator instance
        elements: List of elements to size
    """
    body_width = calculator.body_width

    for element in elements:
        # Calculate element width
        element_width = calculator._calculate_element_width(element, body_width)

        # Calculate element height using appropriate metrics
        element_height = calculate_element_height(element, element_width)

        # Set the calculated size
        element.size = (element_width, element_height)

        logger.debug(
            f"Calculated size for element {getattr(element, 'object_id', 'unknown')}: "
            f"{element_width:.1f} x {element_height:.1f}"
        )


def _position_elements_vertically(calculator, elements: list) -> None:
    """
    Position elements vertically in the body zone with appropriate spacing.

    Elements are stacked from top to bottom, with spacing between them.
    Related elements get reduced spacing for better visual grouping.

    Args:
        calculator: The PositionCalculator instance
        elements: List of elements to position (must have sizes calculated)
    """
    current_y = calculator.body_top
    body_left = calculator.body_left
    body_width = calculator.body_width

    for i, element in enumerate(elements):
        if not element.size:
            logger.warning(
                f"Element {getattr(element, 'object_id', 'unknown')} has no size"
            )
            continue

        element_width, element_height = element.size

        # Apply horizontal alignment
        x_position = _calculate_horizontal_position(
            element, body_left, body_width, element_width
        )

        # Position the element
        element.position = (x_position, current_y)

        logger.debug(
            f"Positioned element {getattr(element, 'object_id', 'unknown')} at "
            f"({x_position:.1f}, {current_y:.1f})"
        )

        # Move to next position
        current_y += element_height

        # Add spacing to next element (if not the last one)
        if i < len(elements) - 1:
            spacing = VERTICAL_SPACING

            # Reduce spacing for related elements
            if hasattr(element, "related_to_next") and element.related_to_next:
                spacing *= VERTICAL_SPACING_REDUCTION

            current_y += spacing


def _calculate_horizontal_position(
    element, container_left: float, container_width: float, element_width: float
) -> float:
    """
    Calculate the horizontal position for an element based on its alignment.

    Args:
        element: The element to position
        container_left: Left edge of the container
        container_width: Width of the container
        element_width: Width of the element

    Returns:
        X-coordinate for the element
    """
    # Check for alignment directive
    alignment = ALIGN_LEFT  # Default

    if hasattr(element, "directives") and element.directives:
        align_directive = element.directives.get("align")
        if align_directive:
            alignment = align_directive.lower()

    # Check element's horizontal_alignment attribute
    elif hasattr(element, "horizontal_alignment"):
        alignment_attr = element.horizontal_alignment
        alignment = (
            alignment_attr.value.lower()
            if hasattr(alignment_attr, "value")
            else str(alignment_attr).lower()
        )

    # Calculate position based on alignment
    if alignment == ALIGN_CENTER:
        return container_left + (container_width - element_width) / 2
    if alignment == ALIGN_RIGHT:
        return container_left + container_width - element_width
    # ALIGN_LEFT or any other value
    return container_left
