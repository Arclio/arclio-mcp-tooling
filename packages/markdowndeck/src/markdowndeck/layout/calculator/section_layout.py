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
        calculator.body_top - body_top_adjustment,  # y - with adjustment!
        calculator.body_width,  # width
        calculator.body_height,  # height
    )

    # Log the body area dimensions
    logger.debug(
        f"Body area for sections: left={body_area[0]:.1f}, top={body_area[1]:.1f}, "
        f"width={body_area[2]:.1f}, height={body_area[3]:.1f}"
    )

    # Process all top-level sections - don't assume a special horizontal layout
    # This ensures vertical stacking of sections by default
    if slide.sections:
        # CRITICAL FIX: Always pass the full body area to top-level sections
        # regardless of their individual width directives
        _distribute_space_and_position_sections(
            calculator, slide.sections, body_area, is_vertical_split=True
        )

        # Position elements within all sections recursively
        _position_elements_in_sections(calculator, slide)
        logger.debug(f"Positioned elements in all sections for slide {slide.object_id}")
    else:
        logger.debug(f"No sections to position for slide {slide.object_id}")

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

    # CRITICAL FIX: For row sections, ensure they get the full width regardless of directives
    # We check the first section to see if this is a row with column subsections
    is_row_with_columns = any(
        section.type == "row" and section.subsections for section in sections
    )

    if is_row_with_columns and not is_vertical_split:
        logger.debug("Processing a row with columns - ensuring full width allocation")

    # Determine the primary dimension to distribute based on orientation
    if is_vertical_split:
        main_position = area_top  # y-coordinate
        main_dimension = area_height  # height
        cross_dimension = area_width  # width (constant)
    else:
        main_position = area_left  # x-coordinate
        main_dimension = area_width  # width
        cross_dimension = area_height  # height (constant)

    # Define constants for layout
    min_section_dim = 20.0  # Minimum section dimension in points
    spacing = (
        calculator.vertical_spacing
        if is_vertical_split
        else calculator.horizontal_spacing
    )
    total_spacing = spacing * (len(sections) - 1)

    # Initialize tracking variables
    dim_key = "height" if is_vertical_split else "width"
    explicit_sections = {}  # section_index: dimension
    implicit_section_indices = []

    # Track sections with min dimensions from directives
    min_dimensions = {}  # section_index: min_dimension

    # First pass: identify explicit and implicit sections
    for i, section in enumerate(sections):
        # Ensure section has directives
        if not hasattr(section, "directives") or section.directives is None:
            section.directives = {}

        # CRITICAL FIX: For row sections, always allocate full width
        # but process contained columns normally for horizontal distribution
        if (
            section.type == "row"
            and section.directives.get("width")
            and not is_vertical_split
        ):
            logger.debug(
                f"OVERRIDING width directive for row section {section.id} - "
                f"row gets full container width regardless of directive"
            )
            section.directives.pop("width", None)  # Remove width directive from row

        # Get dimension directive, if any
        dim_directive = section.directives.get(dim_key)

        if dim_directive is not None:
            if isinstance(dim_directive, float) and 0.0 < dim_directive <= 1.0:
                # Percentage/fraction of total
                explicit_sections[i] = main_dimension * dim_directive

                # Store the calculated dimension as a minimum requirement
                min_dim = main_dimension * dim_directive
                min_dimensions[i] = min_dim

                # Set min_height or min_width attribute based on dimension
                if dim_key == "height":
                    section.min_height = min_dim
                else:
                    section.min_width = min_dim

                logger.debug(
                    f"Set minimum {dim_key} for section {section.id} to {min_dim:.1f}"
                )
            elif isinstance(dim_directive, int | float) and dim_directive > 1.0:
                # Absolute dimension - ensure it doesn't exceed main_dimension
                explicit_sections[i] = min(
                    float(dim_directive), main_dimension - total_spacing
                )

                # Store as minimum requirement
                min_dim = min(float(dim_directive), main_dimension - total_spacing)
                min_dimensions[i] = min_dim

                # Set min_height or min_width attribute based on dimension
                if dim_key == "height":
                    section.min_height = min_dim
                else:
                    section.min_width = min_dim

                logger.debug(
                    f"Set minimum {dim_key} for section {section.id} to {min_dim:.1f}"
                )
            else:
                # Invalid directive, treat as implicit
                implicit_section_indices.append(i)
        else:
            # No directive, treat as implicit
            implicit_section_indices.append(i)

    # Calculate total explicit dimension
    total_explicit_dim = sum(explicit_sections.values())

    # CRITICAL FIX: If this is a row being laid out horizontally,
    # and it doesn't have explicit columns with width, allocate equal space to all
    if not is_vertical_split and not explicit_sections:
        logger.debug("No explicit widths in horizontal layout - distributing equally")
        dim_per_section = (main_dimension - total_spacing) / len(sections)
        for i in range(len(sections)):
            explicit_sections[i] = dim_per_section
            implicit_section_indices = []  # Clear implicit sections

    # Ensure explicit dimensions don't exceed available space (with spacing)
    if total_explicit_dim > 0 and total_explicit_dim > main_dimension - total_spacing:
        # Scale down explicit sections proportionally
        scale_factor = (main_dimension - total_spacing) / total_explicit_dim
        for i in explicit_sections:
            explicit_sections[i] *= scale_factor
            # Also scale min_dimensions if they exist
            if i in min_dimensions:
                min_dimensions[i] *= scale_factor

                # Update min_height or min_width attribute
                if dim_key == "height":
                    sections[i].min_height = min_dimensions[i]
                else:
                    sections[i].min_width = min_dimensions[i]

        logger.debug(
            f"Scaled down explicit sections by {scale_factor:.2f} to fit available space"
        )

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

        # Ensure section dimension respects min_height/min_width from directive
        if dim_key == "height" and hasattr(section, "min_height"):
            section_dim = max(section_dim, section.min_height)
            logger.debug(
                f"Applied minimum height {section.min_height:.1f} to section {section.id}"
            )
        elif dim_key == "width" and hasattr(section, "min_width"):
            section_dim = max(section_dim, section.min_width)
            logger.debug(
                f"Applied minimum width {section.min_width:.1f} to section {section.id}"
            )

        # Ensure section doesn't exceed area boundaries
        if is_vertical_split and current_pos + section_dim > area_top + area_height:
            section_dim = max(min_section_dim, (area_top + area_height) - current_pos)
            logger.warning(
                f"Section {section.id} exceeded available vertical space. "
                f"Adjusted height to {section_dim:.1f}"
            )
        elif (
            not is_vertical_split and current_pos + section_dim > area_left + area_width
        ):
            section_dim = max(min_section_dim, (area_left + area_width) - current_pos)
            logger.warning(
                f"Section {section.id} exceeded available horizontal space. "
                f"Adjusted width to {section_dim:.1f}"
            )

        # CRITICAL FIX: Special handling for row sections to ensure they get full width
        # when being positioned vertically (stacked)
        if is_vertical_split and section.type == "row":
            if section.directives.get("width"):
                logger.debug(
                    f"IGNORING width directive for row section {section.id} in vertical layout - "
                    f"using full container width"
                )

            # Position and size the row section using full width
            section.position = (area_left, current_pos)
            section.size = (cross_dimension, section_dim)
        else:
            # Position and size regular sections normally
            if is_vertical_split:
                section.position = (area_left, current_pos)
                section.size = (cross_dimension, section_dim)
            else:
                section.position = (current_pos, area_top)
                section.size = (section_dim, cross_dimension)

        # Ensure the position and size are logged
        logger.debug(
            f"Set section {section.id} position to {section.position} and size to {section.size}"
        )

        # CRITICAL FIX: Process subsections recursively with correct orientation
        # Handle row sections specially to ensure columns are placed side-by-side
        if section.subsections:
            # Create a subsection area based on this section's geometry
            subsection_area = (
                section.position[0],  # x
                section.position[1],  # y
                section.size[0],  # width
                section.size[1],  # height
            )

            # Row sections ALWAYS get horizontal distribution for their columns
            # regardless of the current is_vertical_split value
            if section.type == "row":
                logger.debug(
                    f"Processing row section {section.id} subsections with HORIZONTAL layout"
                )
                _distribute_space_and_position_sections(
                    calculator,
                    section.subsections,
                    subsection_area,
                    is_vertical_split=False,  # Force horizontal for row's columns
                )
            else:
                # Regular sections maintain current orientation for subsections
                logger.debug(
                    f"Processing regular section {section.id} subsections with "
                    f"is_vertical={is_vertical_split}"
                )
                _distribute_space_and_position_sections(
                    calculator,
                    section.subsections,
                    subsection_area,
                    is_vertical_split=is_vertical_split,
                )

        # Move to next position with spacing
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
            elif section.elements:  # Only include sections that have elements
                leaf_sections.append(section)

    collect_leaf_sections(slide.sections)
    logger.info(f"Found {len(leaf_sections)} leaf sections with elements to position")

    # Position elements within each leaf section
    for section in leaf_sections:
        if section.position is None or section.size is None:
            logger.warning(
                f"Section {section.id} has no position or size. "
                "Cannot position elements properly. Using default positioning."
            )
            # Provide default values if missing
            if section.position is None:
                section.position = (calculator.body_left, calculator.body_top)
                logger.debug(
                    f"Assigned default position {section.position} to section {section.id}"
                )
            if section.size is None:
                # CRITICAL FIX: Use the full body width as default width, not half
                section.size = (calculator.body_width, calculator.body_height / 2)
                logger.debug(
                    f"Assigned default size {section.size} to section {section.id}"
                )

        # Now that we ensured section has position and size, use them
        section_area = (
            section.position[0],
            section.position[1],
            section.size[0],
            section.size[1],
        )

        logger.debug(
            f"Positioning {len(section.elements)} elements in section {section.id} with area "
            f"x={section_area[0]:.1f}, y={section_area[1]:.1f}, "
            f"width={section_area[2]:.1f}, height={section_area[3]:.1f}"
        )

        _position_elements_within_section(
            calculator, section.elements, section_area, section.directives
        )
        logger.debug(
            f"Positioned {len(section.elements)} elements in section {section.id}"
        )


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

        # Skip None elements
        if current is None or next_elem is None:
            logger.warning(
                f"Element at index {i} or {i + 1} is None. Skipping relation marking."
            )
            continue

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
        # Skip None elements
        if element is None:
            logger.warning(f"Element at index {i} is None. Skipping.")
            continue

        # Skip elements without required attributes
        if not hasattr(element, "size") or element.size is None:
            logger.warning(
                f"Element {getattr(element, 'object_id', 'unknown')} lacks size attribute. Skipping."
            )
            continue

        # CRITICAL FIX: Use the full section width for element width calculation
        # This prevents squashed/vertical text due to elements having insufficient width
        element_width = min(element.size[0], area_width)

        # Ensure element width is at least 50% of area width to prevent squashed text
        if element.element_type in (
            ElementType.TEXT,
            ElementType.BULLET_LIST,
            ElementType.ORDERED_LIST,
        ):
            element_width = max(element_width, area_width * 0.5)

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
        if (
            total_height_with_spacing > area_height * 1.1
        ):  # Only scale if significantly exceeding
            scale_factor = (area_height - 5) / total_height_with_spacing  # 5pt buffer
            for i, height in enumerate(elements_heights):
                elements_heights[i] = height * scale_factor
                elements[i].size = (
                    elements[i].size[0],
                    elements[i].size[1] * scale_factor,
                )
            # Update total height after scaling
            total_height_with_spacing = area_height - 5
            logger.debug(
                f"Scaled down elements by factor {scale_factor:.2f} to fit section"
            )

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
                logger.debug(
                    f"Marked elements {i} and {i + 1} to be kept together in overflow"
                )

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
        logger.debug(
            f"Stored {len(element_groups)} logical element groups for overflow handling"
        )
