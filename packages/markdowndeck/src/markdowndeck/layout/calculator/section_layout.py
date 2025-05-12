"""Section-based layout calculations for slides."""

import logging
from typing import Any

from markdowndeck.models import (
    AlignmentType,
    Element,
    ElementType,
    Slide,
)
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


def calculate_section_based_positions(calculator, slide: Slide) -> Slide:
    """
    Calculate positions for a section-based slide layout using the fixed body zone.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to calculate positions for

    Returns:
        The updated slide with positioned sections and elements
    """
    # Step 1: Position header elements (title, subtitle) within the fixed header zone
    calculator._position_header_elements(slide)

    # Step 2: Position footer element if present within the fixed footer zone
    calculator._position_footer_element(slide)

    # Step 3: Use the fixed body zone dimensions for section layout with adjustment
    body_top_adjustment = 5.0  # Same adjustment used in zone_layout.py
    body_area = (
        calculator.body_left,  # x
        calculator.body_top - body_top_adjustment,  # y - Now with adjustment!
        calculator.body_width,  # width
        calculator.body_height,  # height
    )

    # Step 4: Check for top-level horizontal layout (columns)
    has_horizontal_layout = False
    top_level_sections = []

    # Detect horizontal layout based on width directives in top-level sections
    for section in slide.sections:
        if section.directives and "width" in section.directives:
            has_horizontal_layout = True
            top_level_sections.append(section)
        else:
            # If any section doesn't have width directive, default to vertical
            top_level_sections = []
            has_horizontal_layout = False
            break

    if has_horizontal_layout and top_level_sections:
        logger.info(f"Using horizontal column layout for slide {slide.object_id}")
        # Create a horizontal layout (columns)
        _distribute_space_and_position_sections(
            calculator, top_level_sections, body_area, is_vertical_split=False
        )

        # Position elements within each column
        _position_elements_in_sections(calculator, slide)
    else:
        # Default to vertical layout
        # Distribute space among sections within the fixed body zone
        _distribute_space_and_position_sections(
            calculator, slide.sections, body_area, is_vertical_split=True
        )

        # Position elements within each section
        _position_elements_in_sections(calculator, slide)

    logger.debug(f"Section-based layout completed for slide {slide.object_id}")
    return slide


def _distribute_space_and_position_sections(
    calculator,
    sections: list[Section],
    area: tuple[float, float, float, float],
    is_vertical_split: bool,
) -> None:
    """
    Distribute space among sections and position them within the given area.
    All sections must fit within the specified area (usually the body zone).

    Args:
        calculator: The PositionCalculator instance
        sections: List of section models
        area: Tuple of (x, y, width, height) defining the available area
        is_vertical_split: True for vertical distribution, False for horizontal
    """
    if not sections:
        return

    # Extract area parameters
    area_left, area_top, area_width, area_height = area

    # Log the area being distributed
    logger.debug(
        f"Distributing space for {len(sections)} sections in area: "
        f"left={area_left:.1f}, top={area_top:.1f}, width={area_width:.1f}, height={area_height:.1f}, "
        f"is_vertical={is_vertical_split}"
    )

    # Determine the primary dimension to distribute
    if is_vertical_split:
        main_position = area_top  # y-coordinate
        main_dimension = area_height  # height
        cross_dimension = area_width  # width (constant)
    else:
        main_position = area_left  # x-coordinate
        main_dimension = area_width  # width
        cross_dimension = area_height  # height (constant)

    # Define constants
    min_section_dim = 20.0  # Minimum section dimension in points
    spacing = calculator.vertical_spacing if is_vertical_split else calculator.horizontal_spacing
    total_spacing = spacing * (len(sections) - 1)

    # Initialize tracking variables
    dim_key = "height" if is_vertical_split else "width"
    explicit_sections = {}  # section_index: dimension
    implicit_section_indices = []

    # Track sections with min_height requirements from directives
    min_heights = {}  # section_index: min_height

    # First pass: identify explicit and implicit sections
    for i, section in enumerate(sections):
        dim_directive = section.directives.get(dim_key)

        if dim_directive is not None:
            if isinstance(dim_directive, float) and 0.0 < dim_directive <= 1.0:
                # Percentage/fraction of total
                explicit_sections[i] = main_dimension * dim_directive

                # For height directives, store the calculated height as a minimum requirement
                if dim_key == "height":
                    min_height = main_dimension * dim_directive
                    min_heights[i] = min_height
                    section.min_height = min_height
                    logger.debug(f"Set minimum height for section {section.id} to {min_height:.1f}")
            elif isinstance(dim_directive, int | float) and dim_directive > 1.0:
                # Absolute dimension - ensure it doesn't exceed main_dimension
                explicit_sections[i] = min(float(dim_directive), main_dimension - total_spacing)

                # For absolute height directives, also store as minimum requirement
                if dim_key == "height":
                    min_height = min(float(dim_directive), main_dimension - total_spacing)
                    min_heights[i] = min_height
                    section.min_height = min_height
                    logger.debug(f"Set minimum height for section {section.id} to {min_height:.1f}")
            else:
                # Invalid directive, treat as implicit
                implicit_section_indices.append(i)
        else:
            # No directive, treat as implicit
            implicit_section_indices.append(i)

    # Calculate total explicit dimension
    total_explicit_dim = sum(explicit_sections.values())

    # Ensure explicit dimensions don't exceed available space (with spacing)
    if total_explicit_dim > main_dimension - total_spacing:
        # Scale down explicit sections proportionally
        scale_factor = (main_dimension - total_spacing) / total_explicit_dim
        for i in explicit_sections:
            explicit_sections[i] *= scale_factor
            # Also scale min_heights if they exist
            if i in min_heights:
                min_heights[i] *= scale_factor
                sections[i].min_height = min_heights[i]

        logger.debug(f"Scaled down explicit sections by {scale_factor:.2f} to fit available space")

    # Calculate remaining dimension for implicit sections
    remaining_dim = main_dimension - total_explicit_dim - total_spacing
    remaining_dim = max(0, remaining_dim)  # Avoid negative values

    # Distribute remaining dimension among implicit sections
    if implicit_section_indices:
        dim_per_implicit = remaining_dim / len(implicit_section_indices)
        dim_per_implicit = max(min_section_dim, dim_per_implicit)
        logger.debug(f"Allocated {dim_per_implicit:.1f} points per implicit section")
    else:
        dim_per_implicit = 0

    # Second pass: position and size each section
    current_pos = main_position

    for i, section in enumerate(sections):
        # Determine section dimension
        if i in explicit_sections:
            section_dim = explicit_sections[i]
        elif i in implicit_section_indices:
            section_dim = dim_per_implicit
        else:
            # This should not happen, but handle it gracefully
            section_dim = min_section_dim

        # Ensure minimum dimension
        section_dim = max(min_section_dim, section_dim)

        # Ensure section dimension respects min_height from directive
        if hasattr(section, "min_height") and is_vertical_split:
            section_dim = max(section_dim, section.min_height)
            logger.debug(f"Applied minimum height {section.min_height:.1f} to section {section.id}")

        # Ensure section doesn't exceed area boundaries
        if is_vertical_split and current_pos + section_dim > area_top + area_height:
            section_dim = max(min_section_dim, (area_top + area_height) - current_pos)
            logger.warning(
                f"Section {section.id} exceeded available vertical space. "
                f"Adjusted height to {section_dim:.1f}"
            )

        # Position and size the section
        if is_vertical_split:
            section.position = (area_left, current_pos)
            section.size = (cross_dimension, section_dim)
        else:
            section.position = (current_pos, area_top)
            section.size = (section_dim, cross_dimension)

        # Process subsections recursively if this is a row
        if is_vertical_split and section.type == "row" and section.subsections:
            subsection_area = (
                section.position[0],
                section.position[1],
                section.size[0],
                section.size[1],
            )
            _distribute_space_and_position_sections(
                calculator,
                section.subsections,
                subsection_area,
                is_vertical_split=False,  # Horizontal distribution for row's subsections
            )

        # Move to next position
        current_pos += section_dim + spacing

        logger.debug(
            f"Positioned section {section.id}: pos=({section.position[0]:.1f}, {section.position[1]:.1f}), "
            f"size=({section.size[0]:.1f}, {section.size[1]:.1f})"
        )


def _position_elements_in_sections(calculator, slide: Slide) -> None:
    """
    Position elements within their respective sections.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide with sections to position elements in
    """
    if not slide.sections:
        return

    # Create a flat list of leaf sections (sections with elements)
    leaf_sections = []

    def collect_leaf_sections(sections_list):
        for section in sections_list:
            if section.type == "row" and section.subsections:
                collect_leaf_sections(section.subsections)
            elif section.type == "section":
                leaf_sections.append(section)

    collect_leaf_sections(slide.sections)
    logger.debug(f"Found {len(leaf_sections)} leaf sections to position elements in")

    # Position elements within each leaf section
    for section in leaf_sections:
        if section.elements and section.position and section.size:
            section_area = (
                section.position[0],
                section.position[1],
                section.size[0],
                section.size[1],
            )
            _position_elements_within_section(
                calculator, section.elements, section_area, section.directives
            )
        else:
            logger.warning(f"Section {section.id} has no elements, position, or size")


def _position_elements_within_section(
    calculator,
    elements: list[Element],
    area: tuple[float, float, float, float],
    directives: dict[str, Any],
) -> None:
    """
    Position elements within a section. Elements are laid out vertically
    within the strict boundaries of the section area.

    Args:
        calculator: The PositionCalculator instance
        elements: List of elements to position
        area: Tuple of (x, y, width, height) defining the section area
        directives: Section directives
    """
    if not elements:
        return

    area_x, area_y, area_width, area_height = area
    logger.debug(
        f"Positioning {len(elements)} elements within section area: "
        f"x={area_x:.1f}, y={area_y:.1f}, width={area_width:.1f}, height={area_height:.1f}"
    )

    # Apply padding from directives - REDUCED to improve space efficiency
    padding = directives.get("padding", 0.0)
    if isinstance(padding, int | float) and padding > 0:
        area_x += padding
        area_y += padding
        area_width = max(10.0, area_width - (2 * padding))
        area_height = max(10.0, area_height - (2 * padding))

    # Calculate total content height and prepare elements
    elements_heights = []
    total_height_with_spacing = 0

    # Identify related elements (e.g., heading + list)
    # Mark text elements followed by lists as related
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]
        if current.element_type == ElementType.TEXT and next_elem.element_type in (
            ElementType.BULLET_LIST,
            ElementType.ORDERED_LIST,
            ElementType.TABLE,
        ):
            current.related_to_next = True
            next_elem.related_to_prev = True
            logger.debug(
                f"Marked elements as related: {getattr(current, 'object_id', 'unknown')} -> "
                f"{getattr(next_elem, 'object_id', 'unknown')}"
            )

    for i, element in enumerate(elements):
        # Ensure element has a size
        if not hasattr(element, "size") or not element.size:
            element.size = calculator.default_sizes.get(element.element_type, (area_width, 50))

        # Calculate element width and height
        element_width = min(element.size[0], area_width)
        # More accurate height with reduced padding
        from markdowndeck.layout.metrics import calculate_element_height

        element_height = calculate_element_height(element, element_width)
        element.size = (element_width, element_height)
        elements_heights.append(element_height)

        # Add spacing (except after the last element)
        total_height_with_spacing += element_height
        if i < len(elements) - 1:
            total_height_with_spacing += calculator.vertical_spacing

    # If content exceeds section height, consider adjusting elements to fit
    if total_height_with_spacing > area_height:
        logger.warning(
            f"Total content height ({total_height_with_spacing:.1f}) exceeds section height ({area_height:.1f}). "
            f"Some elements may not be fully visible."
        )

        # Scale down all elements proportionally if they exceed section height
        if total_height_with_spacing > area_height * 1.1:  # Only scale if significantly exceeding
            scale_factor = (area_height - 5) / total_height_with_spacing  # 5pt buffer
            for i, height in enumerate(elements_heights):
                elements_heights[i] = height * scale_factor
                elements[i].size = (
                    elements[i].size[0],
                    elements[i].size[1] * scale_factor,
                )
            # Update total height after scaling
            total_height_with_spacing = area_height - 5
            logger.debug(f"Scaled down elements by factor {scale_factor:.2f} to fit section")

    # Apply vertical alignment
    valign = directives.get("valign", "top").lower()

    if valign == "middle" and total_height_with_spacing < area_height:
        start_y = area_y + (area_height - total_height_with_spacing) / 2
    elif valign == "bottom" and total_height_with_spacing < area_height:
        start_y = area_y + area_height - total_height_with_spacing
    else:
        start_y = area_y

    # Position elements
    current_y = start_y
    # Track elements that should be kept together for overflow handling
    element_groups = []
    current_group = []

    for i, element in enumerate(elements):
        # Apply horizontal alignment
        element_align = directives.get("align", "left").lower()

        if hasattr(element, "horizontal_alignment"):
            element.horizontal_alignment = AlignmentType(element_align)

        # Delegate to _apply_horizontal_alignment
        from markdowndeck.layout.calculator.element_utils import (
            apply_horizontal_alignment,
        )

        apply_horizontal_alignment(element, area_x, area_width, current_y)

        # Add to current group
        current_group.append(element)

        # Check if element would overflow section
        element_bottom = current_y + element.size[1]
        remaining_height = area_y + area_height - element_bottom

        # Check if this element would overflow but has a related next element
        is_last_in_group = (
            i == len(elements) - 1
            or not hasattr(element, "related_to_next")
            or not element.related_to_next
        )

        if element_bottom > area_y + area_height:
            logger.warning(
                f"Element {getattr(element, 'object_id', 'unknown')} ({element.element_type}) would overflow "
                f"section. y={current_y:.1f}, height={element.size[1]:.1f}, section_bottom={area_y + area_height:.1f}"
            )

            # Mark the element for overflow handling
            element.would_overflow = True

            # If this element is related to next, mark both for keeping together
            if (
                hasattr(element, "related_to_next")
                and element.related_to_next
                and i < len(elements) - 1
            ):
                element.keep_with_next = True
                elements[i + 1].keep_with_prev = True
                logger.debug(f"Marked elements {i} and {i + 1} to be kept together in overflow")

        # Check remaining space for next element if there is one
        if i < len(elements) - 1:
            next_element_height = elements_heights[i + 1]
            if remaining_height < next_element_height + calculator.vertical_spacing:
                # Log that next element won't fit
                logger.debug(
                    f"Next element won't fit in remaining space: "
                    f"remaining={remaining_height:.1f}, needed={next_element_height + calculator.vertical_spacing:.1f}"
                )

                # If current element is related to next, mark them both for overflow as a unit
                if hasattr(element, "related_to_next") and element.related_to_next:
                    # Mark these elements to be kept together during overflow handling
                    element.keep_with_next = True
                    elements[i + 1].keep_with_prev = True
                    logger.debug(
                        f"Elements {i} and {i + 1} will be kept together during overflow handling"
                    )

        # Finish current group if this is last in group
        if is_last_in_group and current_group:
            element_groups.append(current_group)
            current_group = []

        # Move to next position
        current_y += element.size[1] + calculator.vertical_spacing

    # Add any remaining elements to the last group
    if current_group:
        element_groups.append(current_group)

    # Store the logical element groups with the section for overflow handling
    if hasattr(directives, "section") and element_groups:
        directives["section"].element_groups = element_groups
        logger.debug(f"Stored {len(element_groups)} logical element groups for overflow handling")
