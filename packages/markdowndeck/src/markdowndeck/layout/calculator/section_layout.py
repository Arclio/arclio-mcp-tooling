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
from markdowndeck.models import Element, ElementType, Section

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

    # REFACTORED: The buggy `_process_fill_directives_recursive` pass is removed.
    # [fill] sizing is now handled directly inside the main layout calculation.

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
    if (
        parent_section
        and parent_section.type == "row"
        and section.directives.get("width")
    ):
        explicit_width = available_width
        logger.debug(
            f"Using calculated column width: {explicit_width} for section with width directive {section.directives.get('width')}"
        )

    else:
        explicit_width = _calculate_dimension(
            section.directives.get("width"),
            available_width,
            available_width,
            calculator,
            parent_section,
            dimension_type="width",
        )

    explicit_height = _calculate_dimension(
        section.directives.get("height"),
        available_height,
        available_height,
        calculator,
        parent_section,
        dimension_type="height",
    )

    # If this section has an explicit height, this is the hard limit for its children.
    # Otherwise, the available_height from the parent is the limit.
    child_available_height = (
        explicit_height if "height" in section.directives else available_height
    )

    if not section.children:
        # For a leaf section, its size is its explicit size.
        return explicit_width, explicit_height

    padding_val = float(
        section.directives.get("padding", SECTION_PADDING)
        if isinstance(section.directives.get("padding"), int | float)
        else 0.0
    )
    child_content_width = max(10.0, explicit_width - 2 * padding_val)
    # The height available for children is constrained by this section's *resolved* height.
    child_content_height = max(10.0, child_available_height - 2 * padding_val)

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

    final_width = explicit_width
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
        # FIXED: Handle [fill] directive directly during layout.
        if (
            isinstance(child, Element)
            and child.element_type == ElementType.IMAGE
            and child.directives.get("fill")
        ):
            # FIXED: Reinstate validation for [fill] parent per LAYOUT_SPEC.md Rule #5.
            parent_directives = section.directives or {}
            if "width" not in parent_directives or "height" not in parent_directives:
                raise ValueError(
                    f"Image with [fill] directive requires parent container '{section.id}' to have explicit 'width' and 'height' directives."
                )
            child.size = (content_width, content_height)
            logger.debug(
                f"Sizing [fill] image {getattr(child, 'object_id', 'N/A')} to parent content area: {child.size}"
            )
        elif isinstance(child, Section):
            child_width, child_height = _calculate_intrinsic_size(
                calculator, child, content_width, content_height, parent_section=section
            )
            child.size = (child_width, child_height)
        else:
            if not child.size:
                child_width = _calculate_element_width(
                    child, content_width, calculator, section
                )
                # FIXED: Pass down the content_height constraint to the element calculation.
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

        _, child_height = _calculate_intrinsic_size(
            calculator, child, child_width, content_height, parent_section=section
        )
        child.size = (child_width, child_height)
        total_width += child.size[0]
        max_child_height = max(max_child_height, child.size[1])

        if i < len(child_sections) - 1:
            total_width += gap

    return total_width, max_child_height


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
    """
    if element.element_type == ElementType.IMAGE:
        from markdowndeck.layout.metrics.image import calculate_image_display_size

        scaled_width, scaled_height = calculate_image_display_size(
            element, available_width, available_height, parent_section
        )
        element.size = (scaled_width, scaled_height)
        return scaled_height
    return calculator.calculate_element_height_with_proactive_scaling(
        element, available_width, available_height
    )


def _calculate_element_width(
    element, container_width: float, calculator, parent_section: Section
) -> float:
    """Calculate element width, respecting zero-size elements."""
    if hasattr(element, "size") and element.size == (0, 0):
        return 0.0

    if hasattr(element, "directives") and "width" in element.directives:
        return _calculate_dimension(
            element.directives["width"],
            container_width,
            container_width,
            calculator,
            parent_section,
            dimension_type="width",
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

    for child in section.children:
        if isinstance(child, Section):
            _assign_positions_recursive(calculator, child)
        else:
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
    # Ensure gap is a float
    gap_value = parent_directives.get("gap", calculator.VERTICAL_SPACING)
    try:
        gap = float(gap_value)
    except (ValueError, TypeError):
        gap = float(calculator.VERTICAL_SPACING)

    child_heights = [child.size[1] for child in children if child and child.size]
    start_y = _apply_vertical_alignment(
        area_top, area_height, child_heights, gap, parent_directives
    )

    current_y = start_y
    for i, child in enumerate(children):
        if not child or not child.size:
            continue

        # Apply horizontal alignment which sets the position
        apply_horizontal_alignment(
            child, area_left, area_width, current_y, parent_directives
        )

        # Increment current_y for the next element
        current_y += child.size[1]
        if i < len(children) - 1:  # Only add gap if it's not the last element
            current_y += adjust_vertical_spacing(child, gap)


def _position_horizontal_children(calculator, children, area, parent_section):
    """Position children horizontally using pre-calculated sizes."""
    if not children:
        return

    area_left, area_top, area_width, area_height = area
    parent_directives = parent_section.directives if parent_section else {}
    gap = parent_directives.get("gap", calculator.HORIZONTAL_SPACING)

    current_x = area_left
    for child in children:
        if child.size:
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
    """
    if directive_value is None:
        return default_value

    try:
        if (isinstance(directive_value, str) and "%" in directive_value) or (
            isinstance(directive_value, float) and 0 < directive_value <= 1
        ):
            percentage = (
                float(directive_value.strip("%")) / 100.0
                if isinstance(directive_value, str)
                else directive_value
            )
            if parent_section and (dimension_type in parent_section.directives):
                reference_dimension = container_dimension
            else:
                if dimension_type == "width":
                    reference_dimension = calculator.max_content_width
                else:
                    reference_dimension = calculator.max_content_height
            return reference_dimension * percentage

        if isinstance(directive_value, int | float) and directive_value > 1:
            return min(float(directive_value), container_dimension)

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
    Calculates column widths, robustly handling mixed types and clamping.
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

    for i, section in enumerate(sections):
        d_val = section.directives.get(dimension_key)
        if d_val is None:
            implicit_indices.append(i)
        elif isinstance(d_val, str) and "%" in d_val:
            proportional_indices.append(i)
            proportional_percent += float(d_val.strip("%")) / 100.0
        elif isinstance(d_val, float) and 0 < d_val <= 1:
            proportional_indices.append(i)
            proportional_percent += d_val
        elif isinstance(d_val, int | float) and d_val > 1:
            absolute_indices.append(i)
            absolute_dim += float(d_val)
        else:
            implicit_indices.append(i)

    proportional_dim_request = proportional_percent * usable_dimension
    total_specified_dim = absolute_dim + proportional_dim_request

    if total_specified_dim <= usable_dimension:
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
    else:
        for i in implicit_indices:
            dimensions[i] = 0.0

        scale_factor = (
            usable_dimension / total_specified_dim if total_specified_dim > 0 else 0
        )

        for i in absolute_indices:
            original_val = float(sections[i].directives.get(dimension_key))
            dimensions[i] = original_val * scale_factor

        for i in proportional_indices:
            d_val = sections[i].directives.get(dimension_key)
            percentage = (
                float(str(d_val).strip("%")) / 100.0
                if isinstance(d_val, str)
                else float(d_val)
            )
            original_request = usable_dimension * percentage
            dimensions[i] = original_request * scale_factor

    return dimensions
