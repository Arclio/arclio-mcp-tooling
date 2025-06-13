"""
Refactored Section Layout Calculator - Two-Pass Algorithm

ARCHITECTURAL FLAW RESOLVED:
The original implementation suffered from a circular dependency where parent section
sizing depended on child sizing, which in turn depended on parent available space.
This led to inconsistent calculations causing both visual compression and false overflow.

NEW ARCHITECTURE - TWO-PASS ALGORITHM:

Pass 1: Intrinsic Size Calculation (Bottom-Up)
- Calculate natural sizes of all elements based on content
- Apply container constraints and proactive image scaling
- Propagate sizes up the section hierarchy
- Respects Law #1 (Container-First) and Law #2 (Proactive Image Scaling)

Pass 2: Position Assignment (Top-Down)
- With all sizes determined, assign final positions
- Distribute space according to layout directives
- Respects Law #3 (Explicit Layout with zero defaults)

This eliminates circular dependencies and ensures stable, predictable layout calculations
that strictly adhere to the Container-First sizing model and Blank Canvas principles.
"""

import logging
from typing import Optional, Tuple

from markdowndeck.layout.calculator.element_utils import (
    adjust_vertical_spacing,
    apply_horizontal_alignment,
)
from markdowndeck.layout.constants import (
    MIN_SECTION_HEIGHT,
    SECTION_PADDING,
    VALIGN_BOTTOM,
    VALIGN_MIDDLE,
)
from markdowndeck.models import ElementType, Section

logger = logging.getLogger(__name__)


def calculate_recursive_layout(calculator, root_section: Section, area: tuple) -> None:
    """
    Public entry point for the new two-pass layout algorithm.

    Args:
        calculator: The position calculator instance
        root_section: The root section to layout
        area: (x, y, width, height) of available area
    """
    if root_section is None:
        return

    # Initialize background elements collection
    if not hasattr(calculator, "_section_background_elements"):
        calculator._section_background_elements = []

    area_x, area_y, area_width, area_height = area

    # PASS 1: Calculate intrinsic sizes bottom-up
    logger.debug("Starting Pass 1: Intrinsic size calculation")
    intrinsic_width, intrinsic_height = _calculate_intrinsic_size(
        calculator, root_section, area_width, area_height
    )

    # Set the root section's final size
    root_section.size = (intrinsic_width, intrinsic_height)
    root_section.position = (area_x, area_y)

    # PASS 2: Assign positions top-down
    logger.debug("Starting Pass 2: Position assignment")
    _assign_positions_recursive(calculator, root_section)


def _calculate_intrinsic_size(
    calculator, section: Section, available_width: float, available_height: float
) -> Tuple[float, float]:
    """
    Pass 1: Calculate the intrinsic size needed by a section and all its children.
    This is a bottom-up calculation that resolves sizes before positioning.

    Returns: (width, height) that this section requires
    """
    if not section.children:
        min_width = _calculate_dimension(
            section.directives.get("width"), available_width, 50.0
        )
        min_height = _calculate_dimension(
            section.directives.get("height"), available_height, MIN_SECTION_HEIGHT
        )
        return min_width, min_height

    # Calculate padding that affects content area
    padding_val = float(
        section.directives.get("padding", SECTION_PADDING)
        if isinstance(section.directives.get("padding"), (int, float))
        else 0.0
    )
    content_width = max(10.0, available_width - 2 * padding_val)
    content_height = max(10.0, available_height - 2 * padding_val)

    # Determine layout direction
    is_horizontal = section.type == "row"
    gap = float(
        section.directives.get(
            "gap",
            (
                calculator.HORIZONTAL_SPACING
                if is_horizontal
                else calculator.VERTICAL_SPACING
            ),
        )
    )

    if is_horizontal:
        return _calculate_horizontal_intrinsic_size(
            calculator, section, content_width, content_height, gap, padding_val
        )
    else:
        return _calculate_vertical_intrinsic_size(
            calculator, section, content_width, content_height, gap, padding_val
        )


def _calculate_vertical_intrinsic_size(
    calculator,
    section: Section,
    content_width: float,
    content_height: float,
    gap: float,
    padding_val: float,
) -> Tuple[float, float]:
    """Calculate intrinsic size for vertical (stacked) layout."""
    total_height = 0.0
    max_child_width = 0.0

    for i, child in enumerate(section.children):
        if isinstance(child, Section):
            # Recursive call for child sections
            child_width, child_height = _calculate_intrinsic_size(
                calculator, child, content_width, content_height
            )
            child.size = (child_width, child_height)
        else:
            # Element sizing with proactive scaling
            child_width = _calculate_element_width(child, content_width)
            child_height = _calculate_element_height_with_constraints(
                calculator, child, child_width, content_height
            )
            child.size = (child_width, child_height)

        total_height += child.size[1]
        max_child_width = max(max_child_width, child.size[0])

        # Add gap between children (not after last child)
        if i < len(section.children) - 1:
            total_height += gap

    # Apply section size directives if present
    final_width = _calculate_dimension(
        section.directives.get("width"), content_width, max_child_width
    )
    final_height = _calculate_dimension(
        section.directives.get("height"), content_height, total_height
    )

    # Add padding to final dimensions
    return final_width + 2 * padding_val, final_height + 2 * padding_val


def _calculate_horizontal_intrinsic_size(
    calculator,
    section: Section,
    content_width: float,
    content_height: float,
    gap: float,
    padding_val: float,
) -> Tuple[float, float]:
    """Calculate intrinsic size for horizontal (row) layout."""
    total_width = 0.0
    max_child_height = 0.0

    # First pass: calculate preferred widths for sections with width directives
    section_children = [c for c in section.children if isinstance(c, Section)]
    if section_children:
        col_widths = _calculate_predictable_dimensions(
            section_children, content_width, gap, "width"
        )
        width_idx = 0

    for i, child in enumerate(section.children):
        if isinstance(child, Section):
            # Use calculated column width for sections
            child_width = col_widths[width_idx] if section_children else content_width
            width_idx += 1

            # Calculate height with the determined width
            _, child_height = _calculate_intrinsic_size(
                calculator, child, child_width, content_height
            )
            child.size = (child_width, child_height)
        else:
            # Elements in horizontal layout take full available width for height calc
            child_width = content_width
            child_height = _calculate_element_height_with_constraints(
                calculator, child, child_width, content_height
            )
            child.size = (child_width, child_height)

        total_width += child.size[0]
        max_child_height = max(max_child_height, child.size[1])

        # Add gap between children (not after last child)
        if i < len(section.children) - 1:
            total_width += gap

    # Apply section size directives if present
    final_width = _calculate_dimension(
        section.directives.get("width"), content_width, total_width
    )
    final_height = _calculate_dimension(
        section.directives.get("height"), content_height, max_child_height
    )

    # Add padding to final dimensions
    return final_width + 2 * padding_val, final_height + 2 * padding_val


def _calculate_element_height_with_constraints(
    calculator, element, available_width: float, available_height: float
) -> float:
    """
    Calculate element height with both width and height constraints.
    This implements Law #2 (Proactive Image Scaling) by passing both constraints.
    """
    if element.element_type == ElementType.IMAGE:
        # For images, apply proactive scaling with both width and height constraints
        from markdowndeck.layout.metrics.image import calculate_image_display_size

        _, scaled_height = calculate_image_display_size(
            element, available_width, available_height
        )
        return scaled_height
    else:
        # For other elements, use the standard height calculation
        return calculator.calculate_element_height_with_proactive_scaling(
            element, available_width, available_height
        )


def _calculate_element_width(element, container_width: float) -> float:
    """Calculate element width, respecting zero-size elements."""
    # If an element has its size explicitly set to (0, 0), its width is 0
    if hasattr(element, "size") and element.size == (0, 0):
        return 0.0

    # Check for width directive on the element
    if hasattr(element, "directives") and "width" in element.directives:
        return _calculate_dimension(
            element.directives["width"], container_width, container_width
        )

    return container_width


def _assign_positions_recursive(calculator, section: Section) -> None:
    """
    Pass 2: Assign final positions to all children within a section.
    This is a top-down pass that uses the sizes calculated in Pass 1.
    """
    if not section.children or not section.position or not section.size:
        return

    content_area = _get_content_area(section)
    is_horizontal = section.type == "row"

    if is_horizontal:
        _position_horizontal_children(
            calculator, section.children, content_area, section
        )
    else:
        _position_vertical_children(calculator, section.children, content_area, section)

    # Recursively assign positions to child sections
    for child in section.children:
        if isinstance(child, Section):
            _assign_positions_recursive(calculator, child)
        else:
            # Apply section directives to elements during layout (Task 3)
            if hasattr(calculator, "_merge_section_directives_to_element"):
                calculator._merge_section_directives_to_element(child, section)


def _get_content_area(section: Section) -> tuple:
    """Calculate the available area for children inside a section, accounting for padding."""
    pos = section.position or (0, 0)
    size = section.size or (0, 0)
    padding = section.directives.get("padding", SECTION_PADDING)
    padding_val = float(padding) if isinstance(padding, (int, float)) else 0.0

    return (
        pos[0] + padding_val,
        pos[1] + padding_val,
        max(10.0, size[0] - 2 * padding_val),
        max(10.0, size[1] - 2 * padding_val),
    )


def _position_vertical_children(calculator, children, area, parent_section):
    """Position children in a vertical stack using pre-calculated sizes."""
    if not children:
        return

    area_left, area_top, area_width, area_height = area
    parent_directives = parent_section.directives if parent_section else {}
    gap = parent_directives.get("gap", calculator.VERTICAL_SPACING)

    # Calculate total height needed by all children
    child_heights = [child.size[1] for child in children if child.size]
    total_children_height = sum(child_heights) + max(0, len(child_heights) - 1) * gap

    # Apply vertical alignment
    start_y = _apply_vertical_alignment(
        area_top, area_height, child_heights, gap, parent_directives
    )

    current_y = start_y
    for child in children:
        if not child.size:
            continue

        apply_horizontal_alignment(
            child, area_left, area_width, current_y, parent_directives
        )
        current_y += child.size[1] + adjust_vertical_spacing(child, gap)


def _position_horizontal_children(calculator, children, area, parent_section):
    """Position children horizontally using pre-calculated sizes."""
    if not children:
        return

    area_left, area_top, area_width, area_height = area
    parent_directives = parent_section.directives if parent_section else {}
    gap = parent_directives.get("gap", calculator.HORIZONTAL_SPACING)

    current_x = area_left
    for child in children:
        if not child.size:
            continue

        child.position = (current_x, area_top)
        current_x += child.size[0] + gap


def _apply_vertical_alignment(area_top, area_height, child_heights, gap, directives):
    """Calculate the starting Y position based on valign directive."""
    valign = directives.get("valign", "top").lower()
    total_content_height = sum(child_heights) + max(0, len(child_heights) - 1) * gap

    if valign == VALIGN_MIDDLE and total_content_height < area_height:
        return area_top + (area_height - total_content_height) / 2
    if valign == VALIGN_BOTTOM and total_content_height < area_height:
        return area_top + area_height - total_content_height
    return area_top


def _calculate_dimension(directive_value, total_dimension, default_value) -> float:
    """Helper to parse a width/height directive, always returning a float."""
    if directive_value is None:
        return default_value

    try:
        # Percentage value (e.g., 50% or 0.5)
        if isinstance(directive_value, str) and "%" in directive_value:
            return total_dimension * (float(directive_value.strip("%")) / 100.0)
        if isinstance(directive_value, float) and 0 < directive_value <= 1:
            return total_dimension * directive_value
        # Absolute point value
        if isinstance(directive_value, (int, float)) and directive_value > 1:
            return min(float(directive_value), total_dimension)
    except (ValueError, TypeError):
        pass

    return default_value


def _calculate_predictable_dimensions(
    sections: list[Section],
    available_dimension: float,
    spacing: float,
    dimension_key: str,
) -> list[float]:
    """
    Calculate dimensions for sections with explicit width/height directives.
    Handles container-first clamping for over-subscribed layouts.
    """
    num_sections = len(sections)
    if num_sections == 0:
        return []

    total_spacing = spacing * (num_sections - 1) if num_sections > 1 else 0
    usable_dimension = max(0, available_dimension - total_spacing)

    dimensions = [0.0] * num_sections
    specified_indices = []
    unspecified_indices = []
    specified_total = 0.0

    # First pass: assign all specified dimensions
    for i, section in enumerate(sections):
        size = _calculate_dimension(
            section.directives.get(dimension_key), usable_dimension, None
        )
        if size is not None:
            dimensions[i] = size
            specified_total += size
            specified_indices.append(i)
        else:
            unspecified_indices.append(i)

    # Second pass: handle over-subscription by proportional scaling
    if specified_total > usable_dimension:
        scale_factor = usable_dimension / specified_total
        for i in specified_indices:
            dimensions[i] *= scale_factor
        # Unspecified sections get no space
        for i in unspecified_indices:
            dimensions[i] = 0.0
    else:
        # Distribute remaining space to unspecified sections
        remaining_dim = usable_dimension - specified_total
        if unspecified_indices:
            per_unspecified = (
                remaining_dim / len(unspecified_indices) if remaining_dim > 0 else 0
            )
            for i in unspecified_indices:
                dimensions[i] = per_unspecified

    return dimensions
