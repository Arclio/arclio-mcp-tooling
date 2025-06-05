"""Refactored section-based layout calculations - Predictable division with content-aware elements."""

import logging

from markdowndeck.layout.calculator.element_utils import apply_horizontal_alignment
from markdowndeck.layout.constants import (
    HORIZONTAL_SPACING,
    SECTION_PADDING,
    VALIGN_BOTTOM,
    VALIGN_MIDDLE,
    VALIGN_TOP,
    VERTICAL_SPACING,
)
from markdowndeck.models import Element, Slide
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


def calculate_section_based_positions(calculator, slide: Slide) -> Slide:
    """
    Calculate positions for a section-based slide layout using predictable division.

    This implements the Layout Dichotomy principle:
    - Containers (sections) are sized predictably based on directives or equal division
    - Elements within containers are sized based on their content needs

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to calculate positions for

    Returns:
        The updated slide with positioned sections and elements
    """
    logger.debug(f"Starting section-based layout for slide {slide.object_id}")

    if not slide.sections:
        logger.warning("No sections found for section-based layout")
        return slide

    # Get the body zone area for section distribution
    body_area = calculator.get_body_zone_area()

    # Determine layout orientation based on section directives
    # Default to vertical layout (sections stacked top to bottom)
    # Override to horizontal for specific cases:
    has_width_directives = any(
        hasattr(section, "directives")
        and section.directives
        and "width" in section.directives
        for section in slide.sections
    )

    # Sections marked as type="row" force horizontal layout for their children
    has_row_sections = any(section.type == "row" for section in slide.sections)

    # Use horizontal layout when width directives exist or row sections exist
    is_vertical_layout = not (has_width_directives or has_row_sections)

    logger.debug(
        f"Layout orientation: {'vertical' if is_vertical_layout else 'horizontal'} "
        f"(width_directives={has_width_directives}, row_sections={has_row_sections})"
    )

    _distribute_and_position_sections(
        calculator, slide.sections, body_area, is_vertical_layout
    )

    # Position elements within all sections using two-pass pattern
    _position_elements_in_all_sections(calculator, slide)

    logger.debug(f"Section-based layout completed for slide {slide.object_id}")
    return slide


def _distribute_and_position_sections(
    calculator,
    sections: list[Section],
    area: tuple[float, float, float, float],
    is_vertical_layout: bool,
) -> None:
    """
    Distribute space among sections and position them using predictable division.

    This implements Principle #2: Predictable Division for containers.

    Args:
        calculator: The PositionCalculator instance
        sections: List of sections to position
        area: (left, top, width, height) of available area
        is_vertical_layout: True for vertical stacking, False for horizontal
    """
    if not sections:
        return

    area_left, area_top, area_width, area_height = area

    logger.debug(
        f"Distributing space for {len(sections)} sections in area: "
        f"({area_left:.1f}, {area_top:.1f}, {area_width:.1f}, {area_height:.1f}), "
        f"vertical={is_vertical_layout}"
    )

    # Calculate dimensions based on layout orientation
    if is_vertical_layout:
        main_dimension = area_height
        cross_dimension = area_width
        spacing = VERTICAL_SPACING
        dimension_key = "height"
    else:
        main_dimension = area_width
        cross_dimension = area_height
        spacing = HORIZONTAL_SPACING
        dimension_key = "width"

    # Apply predictable division for the main dimension
    section_dimensions = _calculate_predictable_dimensions(
        sections, main_dimension, spacing, dimension_key
    )

    # For vertical layout, also calculate width dimensions if any sections have width directives
    section_widths = None
    if is_vertical_layout:
        # Check if any sections have width directives
        has_width_directives = any(
            hasattr(section, "directives")
            and section.directives
            and "width" in section.directives
            for section in sections
        )
        if has_width_directives:
            section_widths = _calculate_predictable_dimensions(
                sections, area_width, HORIZONTAL_SPACING, "width"
            )

    # Position each section
    current_position = area_top if is_vertical_layout else area_left

    for i, section in enumerate(sections):
        section_main_dim = section_dimensions[i]

        if is_vertical_layout:
            # Vertical layout: sections stacked top to bottom
            section_width = section_widths[i] if section_widths else cross_dimension
            section.position = (area_left, current_position)
            section.size = (section_width, section_main_dim)
        else:
            # Horizontal layout: sections side by side
            section.position = (current_position, area_top)
            section.size = (section_main_dim, cross_dimension)

        logger.debug(
            f"Positioned section {section.id}: pos=({section.position[0]:.1f}, {section.position[1]:.1f}), "
            f"size=({section.size[0]:.1f}, {section.size[1]:.1f})"
        )

        # Handle subsections recursively
        if hasattr(section, "subsections") and section.subsections:
            subsection_area = (
                section.position[0],
                section.position[1],
                section.size[0],
                section.size[1],
            )

            # Row sections always get horizontal distribution for their children
            if section.type == "row":
                _distribute_and_position_sections(
                    calculator, section.subsections, subsection_area, False
                )
            else:
                # Regular sections maintain current orientation
                _distribute_and_position_sections(
                    calculator, section.subsections, subsection_area, is_vertical_layout
                )

        # Move to next position
        current_position += section_main_dim + spacing


def _calculate_predictable_dimensions(
    sections: list[Section],
    available_dimension: float,
    spacing: float,
    dimension_key: str,
) -> list[float]:
    num_sections = len(sections)
    if num_sections == 0:
        return []

    total_spacing = spacing * (num_sections - 1)
    usable_dimension = available_dimension - total_spacing

    explicitly_sized_indices = {}
    explicitly_sized_total = 0.0
    implicit_indices = []

    # First pass: identify explicit sections and sum their requests
    for i, section in enumerate(sections):
        directive_value = (
            section.directives.get(dimension_key)
            if hasattr(section, "directives") and section.directives
            else None
        )
        if directive_value is not None:
            try:
                size = 0.0
                if isinstance(directive_value, float) and 0.0 < directive_value <= 1.0:
                    size = usable_dimension * directive_value
                elif isinstance(directive_value, int | float) and directive_value > 1.0:
                    size = float(directive_value)

                if size > 0.0:
                    explicitly_sized_indices[i] = size
                    explicitly_sized_total += size
                    continue
            except (ValueError, TypeError):
                pass
        implicit_indices.append(i)

    # Scale down explicit sizes if they collectively exceed the usable space
    # But only scale percentage-based directives, not absolute ones
    if explicitly_sized_total > usable_dimension:
        # Separate absolute vs percentage directives
        absolute_indices = {}
        percentage_indices = {}
        absolute_total = 0.0
        percentage_total = 0.0

        for i in explicitly_sized_indices:
            section = sections[i]
            directive_value = (
                section.directives.get(dimension_key)
                if hasattr(section, "directives") and section.directives
                else None
            )
            if directive_value is not None:
                if isinstance(directive_value, float) and 0.0 < directive_value <= 1.0:
                    # Percentage directive
                    percentage_indices[i] = explicitly_sized_indices[i]
                    percentage_total += explicitly_sized_indices[i]
                elif isinstance(directive_value, int | float) and directive_value > 1.0:
                    # Absolute directive - don't scale
                    absolute_indices[i] = explicitly_sized_indices[i]
                    absolute_total += explicitly_sized_indices[i]

        # If absolute directives alone exceed space, we have a problem
        if absolute_total > usable_dimension:
            logger.warning(
                f"Absolute {dimension_key} directives ({absolute_total:.1f}) exceed available space ({usable_dimension:.1f}). "
                f"Sections may overlap."
            )
            # Keep absolute sizes as-is, even if they cause overflow
        else:
            # Scale only percentage directives to fit remaining space
            remaining_for_percentage = usable_dimension - absolute_total
            if percentage_total > remaining_for_percentage and percentage_total > 0:
                scale_factor = remaining_for_percentage / percentage_total
                for i in percentage_indices:
                    explicitly_sized_indices[i] *= scale_factor

        # Recalculate total after scaling
        explicitly_sized_total = sum(explicitly_sized_indices.values())

    # Distribute remaining space to implicit sections
    remaining_space = usable_dimension - explicitly_sized_total
    num_implicit = len(implicit_indices)
    implicit_size = remaining_space / num_implicit if num_implicit > 0 else 0

    # Build the final dimensions list
    dimensions = [0.0] * num_sections
    for i in range(num_sections):
        dimensions[i] = explicitly_sized_indices.get(i, implicit_size)

    logger.debug(
        f"Calculated {dimension_key} dimensions: explicit={len(explicitly_sized_indices)}, "
        f"implicit={num_implicit}, dimensions={[f'{d:.1f}' for d in dimensions]}"
    )

    return dimensions


def _position_elements_in_all_sections(calculator, slide: Slide) -> None:
    """
    Position elements within all sections using the two-pass vertical alignment pattern.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide containing sections with elements
    """
    # Find all leaf sections (sections that contain elements, not other sections)
    leaf_sections = []
    _collect_leaf_sections(slide.sections, leaf_sections)

    logger.debug(f"Found {len(leaf_sections)} leaf sections to position elements in")

    for section in leaf_sections:
        if section.elements:
            _position_elements_within_section(calculator, section)


def _collect_leaf_sections(
    sections: list[Section], leaf_sections: list[Section]
) -> None:
    """Recursively collect all leaf sections (sections with elements)."""
    for section in sections:
        if hasattr(section, "subsections") and section.subsections:
            _collect_leaf_sections(section.subsections, leaf_sections)
        elif section.elements:
            leaf_sections.append(section)


def _position_elements_within_section(calculator, section: Section) -> None:
    """
    Position elements within a single section using the two-pass pattern.

    Pass 1: Calculate intrinsic sizes for all elements
    Pass 2: Position elements based on vertical alignment directive

    Args:
        calculator: The PositionCalculator instance
        section: The section containing elements to position
    """
    if not section.elements or not section.position or not section.size:
        return

    section_left, section_top = section.position
    section_width, section_height = section.size

    # Apply section padding
    padding = (
        section.directives.get("padding", SECTION_PADDING)
        if section.directives
        else SECTION_PADDING
    )

    content_left = section_left + padding
    content_top = section_top + padding
    content_width = max(10.0, section_width - 2 * padding)
    content_height = max(10.0, section_height - 2 * padding)

    logger.debug(
        f"Positioning {len(section.elements)} elements in section {section.id}: "
        f"content_area=({content_left:.1f}, {content_top:.1f}, {content_width:.1f}, {content_height:.1f})"
    )

    # Pass 1: Calculate intrinsic sizes for all elements
    _calculate_element_sizes_in_section(calculator, section.elements, content_width)

    # Pass 2: Position elements based on vertical alignment
    _apply_vertical_alignment_and_position(
        section.elements,
        content_left,
        content_top,
        content_width,
        content_height,
        section.directives or {},
    )


def _calculate_element_sizes_in_section(
    calculator, elements: list[Element], available_width: float
) -> None:
    """
    Calculate intrinsic sizes for all elements in a section (Pass 1).

    Args:
        calculator: The PositionCalculator instance
        elements: List of elements to size
        available_width: Available width in the section
    """
    for element in elements:
        # Calculate element width within section
        element_width = calculator._calculate_element_width(element, available_width)

        # Calculate intrinsic height based on content
        element_height = _calculate_element_intrinsic_height(element, element_width)

        element.size = (element_width, element_height)

        logger.debug(
            f"Element {getattr(element, 'object_id', 'unknown')} sized: "
            f"{element_width:.1f} x {element_height:.1f}"
        )


def _calculate_element_intrinsic_height(
    element: Element, available_width: float
) -> float:
    """Calculate intrinsic height for an element using appropriate metrics."""
    from markdowndeck.layout.metrics import calculate_element_height

    return calculate_element_height(element, available_width)


def _apply_vertical_alignment_and_position(
    elements: list[Element],
    content_left: float,
    content_top: float,
    content_width: float,
    content_height: float,
    directives: dict,
) -> None:
    """
    Apply vertical alignment and position elements (Pass 2).

    Args:
        elements: List of elements with calculated sizes
        content_left: Left edge of content area
        content_top: Top edge of content area
        content_width: Width of content area
        content_height: Height of content area
        directives: Section directives including valign
    """
    # Calculate total height needed for all elements
    total_content_height = 0.0
    for i, element in enumerate(elements):
        if element.size:
            total_content_height += element.size[1]
            if i < len(elements) - 1:  # Add spacing except after last element
                total_content_height += VERTICAL_SPACING

    # Determine starting Y position based on vertical alignment
    valign = directives.get("valign", VALIGN_TOP).lower()

    if valign == VALIGN_MIDDLE and total_content_height < content_height:
        start_y = content_top + (content_height - total_content_height) / 2
        logger.debug(f"Applied middle vertical alignment, start_y={start_y:.1f}")
    elif valign == VALIGN_BOTTOM and total_content_height < content_height:
        start_y = content_top + content_height - total_content_height
        logger.debug(f"Applied bottom vertical alignment, start_y={start_y:.1f}")
    else:
        start_y = content_top  # Top alignment (default)

    # Position elements sequentially
    current_y = start_y

    for i, element in enumerate(elements):
        if not element.size:
            continue

        element_width, element_height = element.size

        # Apply horizontal alignment using the centralized utility function
        # This modifies element.position in-place
        apply_horizontal_alignment(
            element, content_left, content_width, current_y, directives
        )

        logger.debug(
            f"Positioned element {getattr(element, 'object_id', 'unknown')} at "
            f"({element.position[0]:.1f}, {element.position[1]:.1f})"
        )

        # Move to next position
        current_y += element_height
        if i < len(elements) - 1:  # Add spacing except after last element
            current_y += VERTICAL_SPACING
