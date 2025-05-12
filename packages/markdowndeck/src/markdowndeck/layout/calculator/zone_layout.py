"""Zone-based layout calculations for slides."""

import logging

from markdowndeck.layout.calculator.element_utils import (
    adjust_vertical_spacing,
    apply_horizontal_alignment,
    mark_related_elements,
)
from markdowndeck.layout.constants import (
    BODY_TOP_ADJUSTMENT,
)
from markdowndeck.layout.metrics import calculate_element_height
from markdowndeck.models import (
    ElementType,
)

logger = logging.getLogger(__name__)


def calculate_zone_based_positions(calculator, slide):
    """
    Calculate positions using a zone-based layout model with fixed zones.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to calculate positions for

    Returns:
        The updated slide with positioned elements
    """
    # Step 1: Position header elements (title, subtitle) - within fixed header zone
    calculator._position_header_elements(slide)

    # Step 2: Position footer element if present - within fixed footer zone
    calculator._position_footer_element(slide)

    # Step 3: Position body elements within the fixed body zone
    body_elements = calculator.get_body_elements(slide)

    # Mark related elements (e.g., heading + list)
    mark_related_elements(body_elements)

    # OPTIMIZATION: Adjust starting position to minimize excess spacing
    # Reduced gap between header zone and first body element
    current_y = calculator.body_top - BODY_TOP_ADJUSTMENT

    for element in body_elements:
        # Ensure element has a valid size, defaulting to more conservative sizes
        if not hasattr(element, "size") or not element.size:
            element.size = calculator.default_sizes.get(
                element.element_type, (calculator.body_width, 50)
            )

        # Calculate element width based on directives
        element_width = calculator.body_width
        if hasattr(element, "directives") and "width" in element.directives:
            width_dir = element.directives["width"]
            if isinstance(width_dir, float) and 0.0 < width_dir <= 1.0:
                element_width = calculator.body_width * width_dir
            elif isinstance(width_dir, int | float) and width_dir > 1.0:
                element_width = min(width_dir, calculator.body_width)

        # More accurate height calculation with reduced padding
        element_height = calculate_element_height(element, element_width)
        element.size = (element_width, element_height)

        # OPTIMIZATION: Adjust spacing based on element type
        # Reduce spacing between related elements
        if hasattr(element, "related_to_prev") and element.related_to_prev:
            # If this element is related to the previous one, reduce the spacing
            current_y -= calculator.vertical_spacing * 0.3  # Reduce spacing by 30%

        # Enforce that element does not exceed body zone height
        if current_y + element_height > calculator.body_bottom:
            logger.warning(
                f"Element {getattr(element, 'object_id', 'unknown')} would overflow the body zone. "
                f"Element height: {element_height}, Available height: {calculator.body_bottom - current_y}. "
                f"This will be handled by overflow logic."
            )

        # Position element using horizontal alignment within the body zone
        apply_horizontal_alignment(element, calculator.body_left, calculator.body_width, current_y)

        # Add special handling for spacing after heading elements
        if (
            element.element_type == ElementType.TEXT
            and hasattr(element, "directives")
            and "margin_bottom" in element.directives
        ):
            margin_bottom = element.directives["margin_bottom"]
            current_y += element_height + margin_bottom
        else:
            # Move to next position with standard spacing
            vertical_spacing = calculator.vertical_spacing

            # Use utility function to adjust spacing for related elements
            vertical_spacing = adjust_vertical_spacing(element, vertical_spacing)

            current_y += element_height + vertical_spacing

        # Log element positioning
        logger.debug(
            f"Positioned body element {getattr(element, 'object_id', 'unknown')} "
            f"at y={element.position[1]:.1f}, height={element.size[1]:.1f}"
        )

    return slide
