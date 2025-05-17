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

    # CRITICAL FIX: Top-level sections must be laid out vertically
    # regardless of their types or directives
    if slide.sections:
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

    # CRITICAL FIX: Row sections in horizontal layouts should get full width
    is_row_with_columns = False
    for section in sections:
        if section.type == "row" and section.subsections:
            is_row_with_columns = True
            # Ensure row sections have no width directive when being placed horizontally
            if not is_vertical_split and "width" in section.directives:
                logger.debug(
                    f"Removing width directive from row section {section.id} in horizontal layout"
                )
                del section.directives["width"]
            break

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

    # CRITICAL FIX: First pass: identify and validate explicit and implicit sections
    for i, section in enumerate(sections):
        # Ensure section has directives
        if not hasattr(section, "directives") or section.directives is None:
            section.directives = {}

        # Get dimension directive, if any
        dim_directive = section.directives.get(dim_key)

        if dim_directive is not None:
            try:
                if isinstance(dim_directive, float) and 0.0 < dim_directive <= 1.0:
                    # FIXED: Calculate percentage relative to available dimension minus spacing
                    available_dim = main_dimension - total_spacing
                    explicit_sections[i] = available_dim * dim_directive
                    min_dimensions[i] = explicit_sections[i]

                    # Store calculated dimension on section for reference
                    if dim_key == "height":
                        section.min_height = explicit_sections[i]
                    else:
                        section.min_width = explicit_sections[i]

                    logger.debug(
                        f"Set {dim_key} for section {section.id} to {explicit_sections[i]:.1f} ({dim_directive * 100}%)"
                    )
                elif isinstance(dim_directive, (int, float)) and dim_directive > 1.0:
                    # FIXED: Cap absolute dimensions to available space
                    explicit_sections[i] = min(
                        float(dim_directive), main_dimension - total_spacing
                    )
                    min_dimensions[i] = explicit_sections[i]

                    # Store calculated dimension on section for reference
                    if dim_key == "height":
                        section.min_height = explicit_sections[i]
                    else:
                        section.min_width = explicit_sections[i]

                    logger.debug(
                        f"Set absolute {dim_key} for section {section.id} to {explicit_sections[i]:.1f}pt"
                    )
                else:
                    logger.warning(
                        f"Invalid {dim_key} directive value: {dim_directive} for section {section.id}"
                    )
                    implicit_section_indices.append(i)
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Error processing {dim_key} directive for section {section.id}: {e}"
                )
                implicit_section_indices.append(i)
        else:
            implicit_section_indices.append(i)

    # CRITICAL FIX: For horizontal layouts with no explicit widths, force equal distribution
    if not is_vertical_split and len(implicit_section_indices) == len(sections):
        logger.debug(
            "No explicit widths in horizontal layout - using equal distribution"
        )
        equal_width = (main_dimension - total_spacing) / len(sections)

        for i in range(len(sections)):
            explicit_sections[i] = equal_width
            if i in implicit_section_indices:
                implicit_section_indices.remove(i)

            # Store calculated width on section
            sections[i].min_width = equal_width
            logger.debug(
                f"Set equal width for section {sections[i].id} to {equal_width:.1f}pt"
            )

    # Calculate total explicit dimension
    total_explicit_dim = sum(explicit_sections.values())

    # FIXED: Scale down explicit dimensions proportionally if they exceed available space
    available_space = main_dimension - total_spacing
    if total_explicit_dim > available_space:
        scale_factor = available_space / total_explicit_dim
        for i in explicit_sections:
            original = explicit_sections[i]
            explicit_sections[i] *= scale_factor

            # Update min_dimensions and section attributes
            if i in min_dimensions:
                min_dimensions[i] = explicit_sections[i]

                if dim_key == "height":
                    sections[i].min_height = explicit_sections[i]
                else:
                    sections[i].min_width = explicit_sections[i]

            logger.debug(
                f"Scaled down section {sections[i].id} {dim_key} from {original:.1f} to {explicit_sections[i]:.1f}"
            )

    # FIXED: More accurate remaining dimension calculation
    remaining_dim = max(0, available_space - total_explicit_dim)

    # FIXED: Distribute remaining dimension among implicit sections
    dim_per_implicit = 0
    if implicit_section_indices:
        dim_per_implicit = remaining_dim / len(implicit_section_indices)
        dim_per_implicit = max(min_section_dim, dim_per_implicit)
        logger.debug(f"Allocating {dim_per_implicit:.1f}pt per implicit section")

    # FIXED: Second pass: position and size each section with accurate dimensions
    current_pos = main_position

    for i, section in enumerate(sections):
        # Determine section dimension
        if i in explicit_sections:
            section_dim = explicit_sections[i]
        elif i in implicit_section_indices:
            section_dim = dim_per_implicit
        else:
            section_dim = min_section_dim

        # CRITICAL FIX: Ensure minimum dimension and respect min_height/min_width
        if dim_key == "height" and hasattr(section, "min_height"):
            section_dim = max(section_dim, section.min_height)
        elif dim_key == "width" and hasattr(section, "min_width"):
            section_dim = max(section_dim, section.min_width)

        # CRITICAL FIX: Ensure section doesn't exceed area boundaries
        if is_vertical_split:
            max_allowed = (area_top + area_height) - current_pos
            if section_dim > max_allowed:
                logger.warning(
                    f"Section {section.id} height ({section_dim:.1f}) exceeds remaining vertical space ({max_allowed:.1f}). "
                    f"Adjusting height."
                )
                section_dim = max(min_section_dim, max_allowed)
        else:
            max_allowed = (area_left + area_width) - current_pos
            if section_dim > max_allowed:
                logger.warning(
                    f"Section {section.id} width ({section_dim:.1f}) exceeds remaining horizontal space ({max_allowed:.1f}). "
                    f"Adjusting width."
                )
                section_dim = max(min_section_dim, max_allowed)

        # CRITICAL FIX: Special handling for row sections
        if section.type == "row":
            if is_vertical_split:
                # When stacking rows vertically, they always get full width
                section.position = (area_left, current_pos)
                section.size = (area_width, section_dim)
                logger.debug(
                    f"Positioned row section {section.id} vertically with full width"
                )
            else:
                # When positioning rows horizontally (unusual), respect calculated width
                section.position = (current_pos, area_top)
                section.size = (section_dim, cross_dimension)
                logger.debug(f"Positioned row section {section.id} horizontally")
        else:
            # Position and size regular sections normally
            if is_vertical_split:
                section.position = (area_left, current_pos)
                section.size = (cross_dimension, section_dim)
            else:
                section.position = (current_pos, area_top)
                section.size = (section_dim, cross_dimension)

        # CRITICAL FIX: Process subsections with correct distribution direction
        if section.subsections:
            # Create a subsection area based on this section's geometry
            subsection_area = (
                section.position[0],  # x
                section.position[1],  # y
                section.size[0],  # width
                section.size[1],  # height
            )

            # CRITICAL FIX: Row sections ALWAYS get horizontal distribution for columns
            if section.type == "row":
                logger.debug(
                    f"Processing row section {section.id} subsections with FORCED HORIZONTAL layout"
                )
                _distribute_space_and_position_sections(
                    calculator,
                    section.subsections,
                    subsection_area,
                    is_vertical_split=False,  # Force horizontal for row's subsections
                )
            else:
                # Regular sections maintain the current orientation
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


def _mark_related_elements(elements: list[Element]) -> None:
    """
    Mark related elements that should be kept together during layout and overflow.

    Args:
        elements: List of elements to process
    """
    if not elements:
        return

    # Pattern 1: Text heading followed by a list or table
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        # Skip None elements
        if current is None or next_elem is None:
            continue

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

    # Pattern 2: Heading followed by subheading
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if (
            current.element_type == ElementType.TEXT
            and next_elem.element_type == ElementType.TEXT
            and hasattr(current, "text")
            and hasattr(next_elem, "text")
            and current.text
            and next_elem.text
        ):
            # Check if current looks like a heading (starts with #, ##, etc)
            current_text = current.text.strip()
            next_text = next_elem.text.strip()

            # Simple heuristic: if both start with # and current has fewer #s,
            # consider them related (heading + subheading)
            if (
                current_text.startswith("#")
                and next_text.startswith("#")
                and current_text.count("#") < next_text.count("#")
            ):
                current.related_to_next = True
                next_elem.related_to_prev = True
                logger.debug(
                    f"Marked heading and subheading as related: "
                    f"{getattr(current, 'object_id', 'unknown')} -> "
                    f"{getattr(next_elem, 'object_id', 'unknown')}"
                )

    # Pattern 3: Consecutive paragraphs (consecutive text elements)
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if (
            current.element_type == ElementType.TEXT
            and next_elem.element_type == ElementType.TEXT
            and hasattr(current, "text")
            and hasattr(next_elem, "text")
            and not current.text.strip().startswith("#")
            and not next_elem.text.strip().startswith("#")
        ):
            # Mark consecutive paragraphs as related
            current.related_to_next = True
            next_elem.related_to_prev = True
            logger.debug(
                f"Marked consecutive paragraphs as related: "
                f"{getattr(current, 'object_id', 'unknown')} -> "
                f"{getattr(next_elem, 'object_id', 'unknown')}"
            )

    # Pattern 4: Images followed by captions (text elements)
    for i in range(len(elements) - 1):
        current = elements[i]
        next_elem = elements[i + 1]

        if (
            current.element_type == ElementType.IMAGE
            and next_elem.element_type == ElementType.TEXT
        ):
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

    # FIXED: Apply padding more efficiently
    padding = directives.get("padding", 0.0)
    if isinstance(padding, (int, float)) and padding > 0:
        padding = min(
            padding, area_width * 0.1, area_height * 0.1
        )  # Limit excessive padding
        area_x += padding
        area_y += padding
        area_width = max(10.0, area_width - (2 * padding))
        area_height = max(10.0, area_height - (2 * padding))
        logger.debug(
            f"Applied padding of {padding:.1f}pt, adjusted area: "
            f"x={area_x:.1f}, y={area_y:.1f}, width={area_width:.1f}, height={area_height:.1f}"
        )

    # CRITICAL FIX: Mark related elements that should stay together
    _mark_related_elements(elements)

    # Calculate element heights with stricter width constraints
    elements_heights = []
    total_height_with_spacing = 0

    for i, element in enumerate(elements):
        if element is None:
            logger.warning(f"Element at index {i} is None. Skipping.")
            continue

        if not hasattr(element, "size") or element.size is None:
            logger.warning(
                f"Element {getattr(element, 'object_id', 'unknown')} lacks size attribute. Skipping."
            )
            continue

        # CRITICAL FIX: Ensure element width fits within section with margin
        element_width = min(element.size[0], area_width - 2)  # 2pt safety margin

        # CRITICAL FIX: Different element types need different minimum widths
        if element.element_type in (ElementType.TEXT, ElementType.QUOTE):
            # Text elements need at least 40% of section width to be readable
            element_width = max(element_width, area_width * 0.4)
        elif element.element_type in (
            ElementType.BULLET_LIST,
            ElementType.ORDERED_LIST,
        ):
            # Lists need at least 60% of area width for proper bullets and indentation
            element_width = max(element_width, area_width * 0.6)
        elif element.element_type == ElementType.TABLE:
            # Tables should use nearly full width for readability
            element_width = max(element_width, area_width * 0.85)

        # FIXED: Store full section height in images for aspect ratio calculations
        if element.element_type == ElementType.IMAGE:
            element._section_height = area_height
            element._section_width = area_width
            # For images, limit to 80% of section width if no explicit size
            if element.size[0] > area_width * 0.9 and not "width" in getattr(
                element, "directives", {}
            ):
                element_width = area_width * 0.8

        # CRITICAL FIX: Use refined element height calculation
        from markdowndeck.layout.metrics import calculate_element_height

        element_height = calculate_element_height(element, element_width)

        # Update element size with calculated dimensions
        element.size = (element_width, element_height)
        elements_heights.append(element_height)

        # Track total height needed
        total_height_with_spacing += element_height
        if i < len(elements) - 1:
            # FIXED: Variable spacing for related elements
            next_spacing = calculator.vertical_spacing
            if hasattr(element, "related_to_next") and element.related_to_next:
                next_spacing *= 0.6  # Reduce spacing between related elements
            total_height_with_spacing += next_spacing

    # CRITICAL FIX: If content exceeds section height, adjust elements proportionally
    needs_scaling = total_height_with_spacing > area_height
    if needs_scaling:
        logger.warning(
            f"Content height ({total_height_with_spacing:.1f}pt) exceeds section height ({area_height:.1f}pt). "
            f"Scaling elements to fit."
        )

        # Scale all elements proportionally, but with special handling for titles and small elements
        scale_factor = (area_height - 5) / total_height_with_spacing  # 5pt buffer

        for i, element in enumerate(elements):
            # Never scale titles/headings below readable size
            min_scale = 0.5 if element.element_type == ElementType.TEXT else 0.7
            element_scale = max(min_scale, scale_factor)

            # Update element height and size
            elements_heights[i] *= element_scale
            element.size = (element.size[0], element.size[1] * element_scale)

        # Recalculate total height after scaling
        total_height_with_spacing = sum(
            elements_heights
        ) + calculator.vertical_spacing * (len(elements) - 1)
        logger.debug(
            f"After scaling, content height: {total_height_with_spacing:.1f}pt"
        )

    # CRITICAL FIX: Apply vertical alignment more consistently
    valign = directives.get("valign", "top").lower()
    start_y = area_y  # Default top alignment

    if valign == "middle" and total_height_with_spacing < area_height:
        # Center content vertically in the section
        start_y = area_y + (area_height - total_height_with_spacing) / 2
        logger.debug(f"Applied middle vertical alignment, start_y={start_y:.1f}")
    elif valign == "bottom" and total_height_with_spacing < area_height:
        # Align content to the bottom of the section
        start_y = area_y + area_height - total_height_with_spacing
        logger.debug(f"Applied bottom vertical alignment, start_y={start_y:.1f}")

    # Position elements with precise stacking
    current_y = start_y

    # CRITICAL FIX: Track groups of elements that must stay together
    element_groups = []
    current_group = []

    # Loop through elements and position each one
    for i, element in enumerate(elements):
        # Apply horizontal alignment from directives or element
        element_align = directives.get("align", "left").lower()

        # FIXED: Override section alignment with element's own alignment if specified
        if hasattr(element, "horizontal_alignment"):
            if "align" in getattr(element, "directives", {}):
                element_align = element.directives["align"]
            else:
                element.horizontal_alignment = AlignmentType(element_align)

        # CRITICAL FIX: Element with centered alignment gets proper x position
        from markdowndeck.layout.calculator.element_utils import (
            apply_horizontal_alignment,
        )

        apply_horizontal_alignment(element, area_x, area_width, current_y)

        # Add to current related group
        current_group.append(element)

        # FIXED: Check for overflow and related elements
        element_bottom = current_y + element.size[1]
        is_last_in_group = i == len(elements) - 1 or not getattr(
            element, "related_to_next", False
        )

        # Finish current group if this is last in group
        if is_last_in_group and current_group:
            element_groups.append(current_group)
            current_group = []

        # FIXED: Calculate next position with precise spacing
        next_spacing = calculator.vertical_spacing
        if not is_last_in_group:
            # Reduce spacing between related elements
            next_spacing *= 0.6

        current_y += element.size[1] + next_spacing

    # Add any remaining elements to the last group
    if current_group:
        element_groups.append(current_group)

    # FIXED: Store logical element groups with the section for overflow handling
    if element_groups:
        # This is a fix for the AttributeError - check if directives is a Section or dict
        if (
            isinstance(directives, dict)
            and "section" in directives
            and hasattr(directives["section"], "element_groups")
        ):
            directives["section"].element_groups = element_groups
            logger.debug(
                f"Stored {len(element_groups)} logical element groups for overflow handling"
            )
