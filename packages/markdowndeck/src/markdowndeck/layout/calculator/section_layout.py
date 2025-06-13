import logging

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
    """Public entry point to start the recursive layout process."""
    if root_section is None:
        return

    # REFACTORED: Respect the width directive on the root section. This is the fix.
    section_width = _calculate_dimension(
        root_section.directives.get("width"), area[2], area[2]
    )

    root_section.position = (area[0], area[1])
    # Pass the calculated width to determine the intrinsic height.
    intrinsic_height = _calculate_section_intrinsic_height(
        calculator, root_section, section_width
    )
    # Use the calculated width for the section's final size.
    root_section.size = (section_width, intrinsic_height)

    _layout_children_recursively(calculator, root_section)


def _layout_children_recursively(calculator, parent_section: Section) -> None:
    """
    A truly recursive function that lays out the direct children (Elements and Sections)
    of a given parent section within its assigned area.
    """
    if not parent_section.children:
        return

    content_area = _get_content_area(parent_section)
    is_vertical_layout = parent_section.type != "row"

    for child in parent_section.children:
        if isinstance(child, Section):
            width = _calculate_dimension(
                child.directives.get("width"), content_area[2], content_area[2]
            )
            height = _calculate_section_intrinsic_height(calculator, child, width)
            child.size = (width, height)
        else:
            width = calculator._calculate_element_width(child, content_area[2])
            height = calculator.calculate_element_height_with_proactive_scaling(
                child, width, content_area[3]
            )
            child.size = (width, height)
            child.parent = parent_section

    if is_vertical_layout:
        _position_vertical_children(calculator, parent_section.children, content_area)
    else:
        _position_horizontal_children(calculator, parent_section.children, content_area)

    for child in parent_section.children:
        if isinstance(child, Section):
            _layout_children_recursively(calculator, child)


def _get_content_area(section: Section) -> tuple:
    """Calculates the available area for children inside a section, accounting for padding."""
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


def _position_vertical_children(calculator, children, area):
    """Positions children in a top-to-bottom stack, respecting valign."""
    if not children:
        return
    area_left, area_top, area_width, area_height = area
    parent = getattr(children[0], "parent", None)
    parent_directives = parent.directives if parent else {}
    gap = parent_directives.get("gap", calculator.VERTICAL_SPACING)

    child_heights = [child.size[1] for child in children]
    start_y = _apply_vertical_alignment(
        area_top, area_height, child_heights, gap, parent_directives
    )
    current_y = start_y
    for child in children:
        apply_horizontal_alignment(
            child, area_left, area_width, current_y, parent_directives
        )
        current_y += child.size[1] + adjust_vertical_spacing(child, gap)


def _position_horizontal_children(calculator, children, area):
    """Positions children in a left-to-right row."""
    if not children:
        return
    area_left, area_top, area_width, area_height = area
    parent = getattr(children[0], "parent", None)
    parent_directives = parent.directives if parent else {}
    gap = parent_directives.get("gap", calculator.HORIZONTAL_SPACING)

    section_children = [c for c in children if isinstance(c, Section)]
    col_widths = _calculate_predictable_dimensions(
        section_children, area_width, gap, "width"
    )
    current_x, width_idx = area_left, 0
    for child in children:
        if isinstance(child, Section):
            child_width = col_widths[width_idx]
            width_idx += 1
            child_height = _calculate_dimension(
                child.directives.get("height"), area_height, area_height
            )
            child.size = (child_width, child_height)
            child.position = (current_x, area_top)
            current_x += child_width + gap
        else:
            child.size = (area_width, child.size[1])
            apply_horizontal_alignment(
                child, area_left, area_width, area_top, parent_directives
            )


def _calculate_section_intrinsic_height(
    calculator, section: Section, available_width: float
) -> float:
    """
    Recursively calculates the height a section needs to contain its children.
    FIXED: Now correctly considers the minimum required height for scaled images.
    """
    if not section.children:
        return MIN_SECTION_HEIGHT

    is_vertical = section.type != "row"
    gap = section.directives.get("gap", calculator.VERTICAL_SPACING)
    padding_val = float(
        section.directives.get("padding", SECTION_PADDING)
        if isinstance(section.directives.get("padding"), int | float)
        else 0.0
    )
    content_width = max(10.0, available_width - 2 * padding_val)
    total_height = 0

    if is_vertical:
        child_heights = []
        for child in section.children:
            width = _calculate_dimension(
                child.directives.get("width"), content_width, content_width
            )
            height = (
                _calculate_section_intrinsic_height(calculator, child, width)
                if isinstance(child, Section)
                else calculator.calculate_element_height_with_proactive_scaling(
                    child, width
                )
            )
            child_heights.append(height)
        total_height = sum(child_heights) + max(0, len(child_heights) - 1) * gap
    else:  # Horizontal
        max_child_height = 0
        section_children = [c for c in section.children if isinstance(c, Section)]
        col_widths = _calculate_predictable_dimensions(
            section_children, content_width, gap, "width"
        )
        width_idx = 0
        for child in section.children:
            height = 0
            if isinstance(child, Section):
                width = col_widths[width_idx]
                width_idx += 1
                height = _calculate_section_intrinsic_height(calculator, child, width)
            else:
                # Element in a row takes full width of the row for intrinsic height calculation
                width = content_width
                # FIXED: Correctly calculate the height of child elements, especially images.
                if child.element_type == ElementType.IMAGE:
                    # When calculating intrinsic height of a row, we don't have a vertical limit yet.
                    from markdowndeck.layout.metrics.image import (
                        calculate_image_display_size,
                    )

                    _, scaled_height = calculate_image_display_size(child, width, 0)
                    height = scaled_height
                else:
                    height = calculator.calculate_element_height_with_proactive_scaling(
                        child, width
                    )

            max_child_height = max(max_child_height, height)
        total_height = max_child_height

    return total_height + 2 * padding_val


def _apply_vertical_alignment(area_top, area_height, child_heights, gap, directives):
    """Calculates the starting Y position based on valign directive."""
    valign = directives.get("valign", "top").lower()
    total_content_height = sum(child_heights) + max(0, len(child_heights) - 1) * gap
    if valign == VALIGN_MIDDLE and total_content_height < area_height:
        return area_top + (area_height - total_content_height) / 2
    if valign == VALIGN_BOTTOM and total_content_height < area_height:
        return area_top + area_height - total_content_height
    return area_top


def _calculate_dimension(directive_value, total_dimension, default_value) -> float:
    """Helper to parse a width/height directive, now always returning a float."""
    if directive_value is None:
        return default_value
    try:
        # Percentage value (e.g., 50% or 0.5)
        if isinstance(directive_value, str) and "%" in directive_value:
            return total_dimension * (float(directive_value.strip("%")) / 100.0)
        if isinstance(directive_value, float) and 0 < directive_value <= 1:
            return total_dimension * directive_value
        # Absolute point value
        if isinstance(directive_value, int | float) and directive_value > 1:
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
    """Calculate predictable dimensions for sections with explicit and implicit sizing."""
    num_sections = len(sections)
    if num_sections == 0:
        return []
    total_spacing = spacing * (num_sections - 1) if num_sections > 1 else 0
    usable_dimension = max(0, available_dimension - total_spacing)

    dimensions = [0.0] * num_sections
    specified_total = 0
    unspecified_indices = []

    for i, section in enumerate(sections):
        size = _calculate_dimension(
            section.directives.get(dimension_key), usable_dimension, None
        )
        if size is not None:
            dimensions[i] = size
            specified_total += size
        else:
            unspecified_indices.append(i)

    remaining_dim = usable_dimension - specified_total
    if unspecified_indices:
        per_unspecified = (
            remaining_dim / len(unspecified_indices) if remaining_dim > 0 else 0
        )
        for i in unspecified_indices:
            dimensions[i] = per_unspecified

    return dimensions
