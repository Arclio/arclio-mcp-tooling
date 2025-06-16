import logging

from markdowndeck.layout.calculator.element_utils import (
    adjust_vertical_spacing,
    apply_horizontal_alignment,
)
from markdowndeck.layout.constants import (
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
        calculator, root_section, area_width, area_height, parent_section=None
    )

    # Set the root section's final size
    root_section.size = (intrinsic_width, intrinsic_height)
    root_section.position = (area_x, area_y)

    # NEW: PASS 1.5: Process [fill] directive images now that all section sizes are known
    logger.debug("Starting Pass 1.5: Fill directive processing")
    _process_fill_directives_recursive(root_section)

    # PASS 2: Assign positions top-down
    logger.debug("Starting Pass 2: Position assignment")
    _assign_positions_recursive(calculator, root_section)


def _calculate_intrinsic_size(
    calculator,
    section: Section,
    available_width: float,
    available_height: float,
    parent_section: Section | None,
) -> tuple[float, float]:
    """
    Pass 1: Calculate the intrinsic size needed by a section and all its children.
    This is a bottom-up calculation that resolves sizes before positioning.
    REFACTORED: Now resolves this section's explicit dimensions *before* recursing.
    """
    # FIXED: If this section is a child of a row, the available_width passed here
    # is already the correctly calculated column width from _calculate_predictable_dimensions.
    # Don't recalculate it using _calculate_dimension as that would double-apply the fraction.
    if (
        parent_section
        and parent_section.type == "row"
        and section.directives.get("width")
    ):
        # Use the available_width directly - it's already the correctly calculated width
        explicit_width = available_width
        logger.debug(
            f"Using calculated column width: {explicit_width} for section with width directive {section.directives.get('width')}"
        )

    else:
        # First, determine the explicit dimensions of THIS section.
        # This is the key fix for the percentage resolution algorithm.
        explicit_width = _calculate_dimension(
            section.directives.get("width"),
            available_width,
            available_width,  # Default to available if not specified
            calculator,
            parent_section,
            dimension_type="width",
        )

    explicit_height = _calculate_dimension(
        section.directives.get("height"),
        available_height,
        available_height,  # Default to available if not specified
        calculator,
        parent_section,
        dimension_type="height",
    )

    if not section.children:
        # For a leaf section, its size is its explicit size.
        return explicit_width, explicit_height

    # Calculate padding that affects content area for children
    padding_val = float(
        section.directives.get("padding", SECTION_PADDING)
        if isinstance(section.directives.get("padding"), int | float)
        else 0.0
    )
    # The width and height available for children are based on this section's *explicit* dimensions.
    child_content_width = max(10.0, explicit_width - 2 * padding_val)
    child_content_height = max(10.0, explicit_height - 2 * padding_val)

    # Determine layout direction and gap for children
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
        intrinsic_child_width, intrinsic_child_height = (
            _calculate_horizontal_intrinsic_size(
                calculator, section, child_content_width, child_content_height, gap
            )
        )
    else:
        intrinsic_child_width, intrinsic_child_height = (
            _calculate_vertical_intrinsic_size(
                calculator, section, child_content_width, child_content_height, gap
            )
        )

    # The section's final size is its explicit size, NOT the intrinsic size of its children.
    # The intrinsic size is used to determine if overflow will occur later.
    # However, for layout purposes, the explicit size is the source of truth.
    final_width = explicit_width
    # If height was not explicitly set, it's inferred from children.
    final_height = (
        explicit_height
        if "height" in section.directives
        else intrinsic_child_height + (2 * padding_val)
    )

    return final_width, final_height


def _calculate_vertical_intrinsic_size(
    calculator,
    section: Section,
    content_width: float,
    content_height: float,
    gap: float,
) -> tuple[float, float]:
    """Calculate intrinsic size for vertical (stacked) layout's children."""
    total_height = 0.0
    max_child_width = 0.0

    for i, child in enumerate(section.children):
        if isinstance(child, Section):
            child_width, child_height = _calculate_intrinsic_size(
                calculator, child, content_width, content_height, parent_section=section
            )
            child.size = (child_width, child_height)
        else:
            # Skip early [fill] directive handling - it will be handled after parent sizing
            pass
            if not child.size:
                child_width = _calculate_element_width(
                    child, content_width, calculator, section
                )
                child_height = _calculate_element_height_with_constraints(
                    calculator, child, child_width, content_height, section
                )
                child.size = (child_width, child_height)

        total_height += child.size[1]
        max_child_width = max(max_child_width, child.size[0])

        if i < len(section.children) - 1:
            total_height += gap

    return max_child_width, total_height


def _calculate_horizontal_intrinsic_size(
    calculator,
    section: Section,
    content_width: float,
    content_height: float,
    gap: float,
) -> tuple[float, float]:
    """Calculate intrinsic size for horizontal (row) layout's children."""
    total_width = 0.0
    max_child_height = 0.0

    child_sections = [c for c in section.children if isinstance(c, Section)]
    col_widths = _calculate_predictable_dimensions(
        child_sections, content_width, gap, "width", calculator, section
    )

    for i, child in enumerate(child_sections):
        child_width = col_widths[i]

        # Handle [fill] directive for any image elements in this child section
        _handle_fill_directive_in_section(child, child_width, content_height)

        _, child_height = _calculate_intrinsic_size(
            calculator, child, child_width, content_height, parent_section=section
        )
        child.size = (child_width, child_height)
        total_width += child.size[0]
        max_child_height = max(max_child_height, child.size[1])

        if i < len(child_sections) - 1:
            total_width += gap

    return total_width, max_child_height


def _handle_fill_directive_in_section(
    section: Section, available_width: float, available_height: float
) -> None:
    """
    Recursively handle [fill] directive for image elements within a section.
    """
    if not section.children:
        return

    for child in section.children:
        if isinstance(child, Section):
            _handle_fill_directive_in_section(child, available_width, available_height)
        elif (
            child.element_type == ElementType.IMAGE
            and hasattr(child, "directives")
            and child.directives.get("fill", False)
        ):
            # TODO: Implement fill directive handling in Task 3
            pass


def _calculate_element_height_with_constraints(
    calculator,
    element,
    available_width: float,
    available_height: float,
    parent_section: Section = None,
) -> float:
    """
    Calculate element height with both width and height constraints.
    This implements Law #2 (Proactive Image Scaling) by passing both constraints.

    UPDATED: Implements [fill] directive validation and sizing per LAYOUT_SPEC.md Rule #4a
    """
    if element.element_type == ElementType.IMAGE:
        # Check if this is a [fill] image that needs special handling
        if hasattr(element, "_is_fill_image") and element._is_fill_image:
            # This shouldn't happen in normal flow since we validate at a higher level
            # But we'll implement basic [fill] sizing here as fallback
            element.size = (
                available_width,
                available_height if available_height > 0 else available_width * 9 / 16,
            )
            return element.size[1]

        # For images, apply proactive scaling with both width and height constraints
        from markdowndeck.layout.metrics.image import calculate_image_display_size

        scaled_width, scaled_height = calculate_image_display_size(
            element, available_width, available_height, parent_section
        )
        # This is where the invalid image size was being lost. Set it on the element.
        element.size = (scaled_width, scaled_height)
        return scaled_height
    # For other elements, use the standard height calculation
    return calculator.calculate_element_height_with_proactive_scaling(
        element, available_width, available_height
    )


def _calculate_element_width(
    element, container_width: float, calculator, parent_section: Section
) -> float:
    """Calculate element width, respecting zero-size elements."""
    # If an element has its size explicitly set to (0, 0), its width is 0
    if hasattr(element, "size") and element.size == (0, 0):
        return 0.0

    # Check for width directive on the element ITSELF (not inherited from section)
    if hasattr(element, "directives") and "width" in element.directives:
        return _calculate_dimension(
            element.directives["width"],
            container_width,
            container_width,
            calculator,
            parent_section,
            dimension_type="width",
        )

    # FIXED: Elements should use their container's full width by default
    # They should NOT inherit the section's width directive
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
    padding_val = float(padding) if isinstance(padding, int | float) else 0.0

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
    sum(child_heights) + max(0, len(child_heights) - 1) * gap

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
    # FIXED: Set each child's height to the row's height before positioning
    for child in children:
        if child.size:
            # Force child height to match the row's content height
            child.size = (child.size[0], area_height)

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


def _calculate_dimension(
    directive_value,
    container_dimension: float,
    default_value: float,
    calculator,
    parent_section: Section | None,
    dimension_type: str,
) -> float:
    """
    Helper to parse a width/height directive, implementing Percentage Dimension Resolution.
    REFACTORED: To implement LAYOUT_SPEC.md Rule #9 correctly.
    """
    if directive_value is None:
        return default_value

    try:
        # Percentage value (e.g., "50%" or 0.5)
        if (isinstance(directive_value, str) and "%" in directive_value) or (
            isinstance(directive_value, float) and 0 < directive_value <= 1
        ):
            percentage = (
                float(directive_value.strip("%")) / 100.0
                if isinstance(directive_value, str)
                else directive_value
            )
            # Implement Percentage Dimension Resolution Algorithm
            if parent_section and (dimension_type in parent_section.directives):
                # Rule #9.1: Parent has explicit size, use its container dimension.
                reference_dimension = container_dimension
            else:
                # Rule #9.2: Parent size is inferred, use total slide content area.
                if dimension_type == "width":
                    reference_dimension = calculator.max_content_width
                else:  # height
                    reference_dimension = calculator.max_content_height
            return reference_dimension * percentage

        # Absolute point value
        if isinstance(directive_value, int | float) and directive_value > 1:
            return min(float(directive_value), container_dimension)

        # String numeric value (e.g., "400")
        if isinstance(directive_value, str):
            try:
                numeric_value = float(directive_value)
                if numeric_value > 1:
                    return min(numeric_value, container_dimension)
            except ValueError:
                pass

    except (ValueError, TypeError):
        pass

    return default_value


def _calculate_predictable_dimensions(
    sections: list[Section],
    available_dimension: float,
    spacing: float,
    dimension_key: str,
    calculator,
    parent_section: Section | None,
) -> list[float]:
    """
    # REFACTORED: Complete rewrite to correctly handle mixed column types and clamping.
    # This implementation is robust and fixes multiple layout bugs.
    # MAINTAINS: Adherence to "Container-First" and "Horizontal Clamping" principles.
    """
    num_sections = len(sections)
    if not num_sections:
        return []

    dimensions = [0.0] * num_sections
    total_spacing = max(0, spacing * (num_sections - 1))
    usable_dimension = max(0, available_dimension - total_spacing)

    absolute_dim = 0.0
    proportional_percent = 0.0
    implicit_indices, proportional_indices, absolute_indices = [], [], []

    # Pass 1: Categorize sections and sum up explicit requests
    for i, section in enumerate(sections):
        d_val = section.directives.get(dimension_key)
        if d_val is None:
            implicit_indices.append(i)
        elif isinstance(d_val, str) and "%" in d_val:
            # Percentage values like "50%"
            proportional_indices.append(i)
            proportional_percent += float(d_val.strip("%")) / 100.0
        elif isinstance(d_val, float) and 0 < d_val <= 1:
            # FIXED: Fractions like 1/3 (0.333...) are already converted by directive parser
            # They represent a proportion of the usable dimension, not a percentage
            proportional_indices.append(i)
            proportional_percent += (
                d_val  # d_val is already the decimal fraction (0.333 for 1/3)
            )
        elif isinstance(d_val, int | float) and d_val > 1:
            absolute_indices.append(i)
            absolute_dim += float(d_val)
        else:  # Fallback for invalid values
            implicit_indices.append(i)

    # FIXED: Add debugging to understand the calculation
    logger.debug(f"Width calculation for {num_sections} sections:")
    logger.debug(
        f"  available_dimension={available_dimension}, spacing={spacing}, usable_dimension={usable_dimension}"
    )
    logger.debug(
        f"  absolute_dim={absolute_dim}, proportional_percent={proportional_percent}"
    )
    logger.debug(
        f"  absolute_indices={absolute_indices}, proportional_indices={proportional_indices}, implicit_indices={implicit_indices}"
    )

    # Pass 2: Distribute space
    # FIXED: Calculate proportional space requests properly
    proportional_dim_request = proportional_percent * usable_dimension
    total_specified_dim = absolute_dim + proportional_dim_request

    logger.debug(
        f"  proportional_dim_request={proportional_dim_request}, total_specified_dim={total_specified_dim}"
    )

    if total_specified_dim <= usable_dimension:
        # Undersubscribed or fits perfectly
        for i in absolute_indices:
            dimensions[i] = float(sections[i].directives.get(dimension_key))
        for i in proportional_indices:
            d_val = sections[i].directives.get(dimension_key)
            percentage = (
                float(str(d_val).strip("%")) / 100.0
                if isinstance(d_val, str)
                else float(d_val)
            )
            dimensions[i] = usable_dimension * percentage

        remaining_for_implicit = usable_dimension - sum(dimensions)
        if implicit_indices:
            per_implicit = max(0, remaining_for_implicit / len(implicit_indices))
            for i in implicit_indices:
                dimensions[i] = per_implicit

        logger.debug(f"  Undersubscribed: dimensions={dimensions}")
    else:
        # Oversubscribed: scale down specified columns, implicit get zero
        for i in implicit_indices:
            dimensions[i] = 0.0

        scale_factor = (
            usable_dimension / total_specified_dim if total_specified_dim > 0 else 0
        )

        logger.debug(f"  Oversubscribed: scale_factor={scale_factor}")

        for i in absolute_indices:
            original_val = float(sections[i].directives.get(dimension_key))
            dimensions[i] = original_val * scale_factor
            logger.debug(
                f"    Absolute column {i}: {original_val} * {scale_factor} = {dimensions[i]}"
            )

        for i in proportional_indices:
            d_val = sections[i].directives.get(dimension_key)
            percentage = (
                float(str(d_val).strip("%")) / 100.0
                if isinstance(d_val, str)
                else float(d_val)
            )
            # FIXED: Don't double-scale! proportional_dim_request already includes the percentage calculation
            # We should scale based on the original request, not double-scale
            original_request = usable_dimension * percentage
            dimensions[i] = original_request * scale_factor
            logger.debug(
                f"    Proportional column {i}: {percentage} of {usable_dimension} = {original_request}, scaled = {dimensions[i]}"
            )

    logger.debug(f"  Final dimensions={dimensions}")
    return dimensions


def _process_fill_directives_recursive(section: Section) -> None:
    """
    Process [fill] directive images now that all section sizes are known.
    This is a separate pass that runs after intrinsic sizing is complete.
    """
    if not section.children:
        return

    for child in section.children:
        if isinstance(child, Section):
            _process_fill_directives_recursive(child)
        elif child.element_type == ElementType.IMAGE:
            _process_fill_directive_for_image(child, section)


def _process_fill_directive_for_image(image_element, parent_section: Section) -> None:
    """
    Process [fill] directive for a single image element.
    """
    from markdowndeck.models import ElementType

    if image_element.element_type != ElementType.IMAGE:
        return

    directives = image_element.directives or {}
    has_fill = directives.get("fill", False)

    if not has_fill:
        return

    # LAYOUT_SPEC.md Rule #5: Validate that parent section has explicit dimensions.
    parent_directives = parent_section.directives or {}
    parent_has_width = "width" in parent_directives
    parent_has_height = "height" in parent_directives

    if not parent_has_width or not parent_has_height:
        missing_dims = []
        if not parent_has_width:
            missing_dims.append("'width'")
        if not parent_has_height:
            missing_dims.append("'height'")
        raise ValueError(
            f"Image with [fill] directive requires parent container '{parent_section.id}' to have explicit "
            f"{' and '.join(missing_dims)} directive(s)."
        )

    # Sizing is now handled in a separate pass.
    logger.debug(
        f"Validated [fill] directive on image {image_element.object_id} in container {parent_section.id}."
    )
