import logging

from markdowndeck.layout.calculator.element_utils import (
    adjust_vertical_spacing,
    apply_horizontal_alignment,
    mark_related_elements,
)
from markdowndeck.layout.constants import (
    SECTION_PADDING,
    VALIGN_BOTTOM,
    VALIGN_MIDDLE,
    VALIGN_TOP,
)
from markdowndeck.models import Element, ElementType, Slide
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


def calculate_section_based_positions(calculator, slide: Slide) -> Slide:
    """
    Calculates positions for the slide's content starting from the root_section.
    """
    if not slide.root_section:
        return slide

    body_area = calculator.get_body_zone_area()
    is_vertical_layout = _determine_layout_orientation(slide.root_section.children)

    slide.root_section.position = (body_area[0], body_area[1])
    slide.root_section.size = (body_area[2], body_area[3])

    _distribute_and_position_sections_unified(
        calculator, slide.root_section.children, body_area, is_vertical_layout
    )
    _position_elements_in_all_sections(calculator, slide)
    return slide


def _determine_layout_orientation(children: list[Element | Section]) -> bool:
    """
    Determine whether sections should use vertical layout based on their directives.
    REFACTORED: Filters for Section objects before checking attributes.
    """
    sections = [child for child in children if isinstance(child, Section)]
    if not sections:
        return True

    has_height_only_directives = any(
        s.directives.get("height") and not s.directives.get("width") for s in sections
    )
    has_row_sections = any(s.type == "row" for s in sections)
    has_width_directives = any(s.directives.get("width") for s in sections)

    if len(sections) > 1 and has_row_sections:
        return True
    if len(sections) > 1 and not has_width_directives:
        return True

    return (has_height_only_directives or len(sections) == 1) and not has_row_sections


def _calculate_section_intrinsic_height_and_set_child_sizes(
    calculator, section: Section, available_width: float, available_height: float = 0
) -> float:
    """
    Calculate intrinsic height AND set the final size for all child elements.
    """
    section_elements = [
        child for child in section.children if not hasattr(child, "children")
    ]
    if not section_elements:
        return 40.0

    padding = (
        section.directives.get("padding", SECTION_PADDING)
        if section.directives
        else SECTION_PADDING
    )
    content_width = max(10.0, available_width - 2 * padding)
    content_height = max(10.0, available_height - 2 * padding)
    mark_related_elements(section_elements)

    total_content_height = 0.0
    for i, element in enumerate(section_elements):
        if element.element_type == ElementType.IMAGE:
            from markdowndeck.layout.metrics.image import calculate_image_display_size

            element_width, element_height = calculate_image_display_size(
                element, content_width, content_height
            )
        else:
            element_width = calculator._calculate_element_width(element, content_width)
            element_height = calculator.calculate_element_height_with_proactive_scaling(
                element, element_width, 0
            )
        element.size = (element_width, element_height)
        total_content_height += element_height
        if i < len(section_elements) - 1:
            total_content_height += adjust_vertical_spacing(
                element, calculator.VERTICAL_SPACING
            )

    total_height = total_content_height + (2 * padding)
    return max(total_height, 20.0)


def _distribute_and_position_sections_unified(
    calculator,
    children: list[Element | Section],
    area: tuple[float, float, float, float],
    is_vertical_layout: bool,
) -> None:
    """
    Distribute space among sections using the unified sequential model.
    """
    # REFACTORED: Filter for only Section objects to prevent AttributeErrors on malformed slides.
    sections = [child for child in children if isinstance(child, Section)]

    if not sections:
        return

    area_left, area_top, area_width, area_height = area

    logger.debug(
        f"Distributing space for {len(sections)} sections in area: "
        f"({area_left:.1f}, {area_top:.1f}, {area_width:.1f}, {area_height:.1f}), "
        f"vertical={is_vertical_layout}"
    )

    if is_vertical_layout:
        _position_vertical_sections_sequential(
            calculator, sections, area_left, area_top, area_width, area_height
        )
    else:
        _position_horizontal_sections_equal_division(
            calculator, sections, area_left, area_top, area_width, area_height
        )


def _position_vertical_sections_sequential(
    calculator,
    sections: list[Section],
    area_left: float,
    area_top: float,
    area_width: float,
    area_height: float,
) -> None:
    """
    Position vertical sections using sequential, content-aware model with proactive image scaling.
    """
    current_y = area_top

    for _i, section in enumerate(sections):
        explicit_height = None
        if hasattr(section, "directives") and section.directives:
            height_directive = section.directives.get("height")
            if height_directive is not None:
                try:
                    if (
                        isinstance(height_directive, float)
                        and 0 < height_directive <= 1
                    ):
                        explicit_height = area_height * height_directive
                    elif (
                        isinstance(height_directive, int | float)
                        and height_directive > 1
                    ):
                        explicit_height = float(height_directive)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid height directive: {height_directive}")

        section_width = area_width
        if hasattr(section, "directives") and section.directives:
            width_directive = section.directives.get("width")
            if width_directive is not None:
                try:
                    if isinstance(width_directive, float) and 0 < width_directive <= 1:
                        section_width = area_width * width_directive
                    elif (
                        isinstance(width_directive, int | float) and width_directive > 1
                    ):
                        section_width = min(float(width_directive), area_width)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid width directive: {width_directive}")

        if explicit_height is not None:
            section_height = explicit_height
        else:
            section_height = _calculate_section_intrinsic_height_and_set_child_sizes(
                calculator, section, section_width, area_height
            )

        section.position = (area_left, current_y)
        section.size = (section_width, section_height)

        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]
        if child_sections:
            subsection_area = (
                section.position[0],
                section.position[1],
                section.size[0],
                section.size[1],
            )
            subsection_layout = _determine_layout_orientation(child_sections)
            _distribute_and_position_sections_unified(
                calculator, child_sections, subsection_area, subsection_layout
            )
        current_y += section_height + calculator.VERTICAL_SPACING


def _position_horizontal_sections_equal_division(
    calculator,
    sections: list[Section],
    area_left: float,
    area_top: float,
    area_width: float,
    area_height: float,
) -> None:
    """
    Position horizontal sections using equal division for implicit widths.
    """
    section_widths = _calculate_predictable_dimensions(
        sections, area_width, calculator.HORIZONTAL_SPACING, "width"
    )
    current_x = area_left

    for i, section in enumerate(sections):
        section_width = section_widths[i]
        section_height = area_height
        if hasattr(section, "directives") and section.directives:
            height_directive = section.directives.get("height")
            if height_directive is not None:
                try:
                    if (
                        isinstance(height_directive, float)
                        and 0 < height_directive <= 1
                    ):
                        section_height = area_height * height_directive
                    elif (
                        isinstance(height_directive, int | float)
                        and height_directive > 1
                    ):
                        section_height = min(float(height_directive), area_height)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid height directive: {height_directive}")

        section.position = (current_x, area_top)
        section.size = (section_width, section_height)

        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]
        if child_sections:
            subsection_area = (
                section.position[0],
                section.position[1],
                section.size[0],
                section.size[1],
            )
            subsection_layout = _determine_layout_orientation(child_sections)
            _distribute_and_position_sections_unified(
                calculator, child_sections, subsection_area, subsection_layout
            )
        current_x += section_width + calculator.HORIZONTAL_SPACING


def _calculate_predictable_dimensions(
    sections: list[Section],
    available_dimension: float,
    spacing: float,
    dimension_key: str,
) -> list[float]:
    """
    Calculate predictable dimensions for sections with explicit and implicit sizing.
    """
    num_sections = len(sections)
    if num_sections == 0:
        return []
    total_spacing = spacing * (num_sections - 1)
    usable_dimension = available_dimension - total_spacing
    absolute_indices, proportional_indices, implicit_indices = {}, {}, []
    absolute_total = 0.0

    for i, section in enumerate(sections):
        directive_value = (
            section.directives.get(dimension_key)
            if hasattr(section, "directives") and section.directives
            else None
        )
        if isinstance(directive_value, int | float) and directive_value > 1.0:
            absolute_indices[i] = float(directive_value)
            absolute_total += float(directive_value)
        elif isinstance(directive_value, float) and 0.0 < directive_value <= 1.0:
            proportional_indices[i] = directive_value
        else:
            implicit_indices.append(i)

    proportional_total = 0.0
    for i, proportion in proportional_indices.items():
        size = usable_dimension * proportion
        proportional_indices[i] = size
        proportional_total += size

    remaining_for_implicit = max(
        0.0, usable_dimension - absolute_total - proportional_total
    )
    implicit_size = (
        remaining_for_implicit / len(implicit_indices) if implicit_indices else 0.0
    )

    dimensions = [0.0] * num_sections
    for i in range(num_sections):
        if i in absolute_indices:
            dimensions[i] = absolute_indices[i]
        elif i in proportional_indices:
            dimensions[i] = proportional_indices[i]
        else:
            dimensions[i] = implicit_size

    if absolute_total > usable_dimension:
        logger.warning(
            f"Absolute {dimension_key} directives ({absolute_total:.1f}) exceed usable space ({usable_dimension:.1f}). Sections may overlap."
        )
    return dimensions


def _position_elements_in_all_sections(calculator, slide: Slide) -> None:
    """
    Position elements within all sections.
    REFACTORED: Starts traversal from the single root_section.
    """
    if not slide.root_section:
        return
    leaf_sections = []
    _collect_leaf_sections([slide.root_section], leaf_sections)
    for section in leaf_sections:
        if [child for child in section.children if not hasattr(child, "children")]:
            _position_elements_within_section(calculator, section)


def _collect_leaf_sections(
    sections: list[Section], leaf_sections: list[Section]
) -> None:
    """Recursively collect all leaf sections (sections with elements)."""
    for section in sections:
        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]
        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]
        if child_sections:
            _collect_leaf_sections(child_sections, leaf_sections)
        elif section_elements:
            leaf_sections.append(section)


def _position_elements_within_section(calculator, section: Section) -> None:
    """
    Position elements within a single section using pre-calculated sizes.
    """
    section_elements = [
        child for child in section.children if not hasattr(child, "children")
    ]
    if not section_elements or not section.position or not section.size:
        return

    section_left, section_top = section.position
    section_width, section_height = section.size
    padding = (
        section.directives.get("padding", SECTION_PADDING)
        if section.directives
        else SECTION_PADDING
    )
    content_left = section_left + padding
    content_top = section_top + padding
    content_width = max(10.0, section_width - 2 * padding)
    content_height = max(10.0, section_height - 2 * padding)

    for element in section_elements:
        if not element.size:
            element_width = calculator._calculate_element_width(element, content_width)
            element_height = calculator.calculate_element_height_with_proactive_scaling(
                element, element_width, 0
            )
            element.size = (element_width, element_height)

    _apply_vertical_alignment_and_position_unified(
        calculator,
        section_elements,
        content_left,
        content_top,
        content_width,
        content_height,
        section.directives or {},
    )


def _apply_vertical_alignment_and_position_unified(
    calculator,
    elements: list[Element],
    content_left: float,
    content_top: float,
    content_width: float,
    content_height: float,
    directives: dict,
) -> None:
    """
    Apply vertical alignment and position elements with unified spacing logic.
    """
    if not elements:
        return
    vertical_gap = directives.get("gap", calculator.VERTICAL_SPACING)

    total_content_height = sum(element.size[1] for element in elements if element.size)
    total_content_height += adjust_vertical_spacing(elements[0], vertical_gap) * (
        len(elements) - 1
    )

    valign = directives.get("valign", VALIGN_TOP).lower()
    if valign == VALIGN_MIDDLE and total_content_height < content_height:
        start_y = content_top + (content_height - total_content_height) / 2
    elif valign == VALIGN_BOTTOM and total_content_height < content_height:
        start_y = content_top + content_height - total_content_height
    else:
        start_y = content_top

    current_y = start_y
    for i, element in enumerate(elements):
        if not element.size:
            continue
        apply_horizontal_alignment(
            element, content_left, content_width, current_y, directives
        )
        current_y += element.size[1]
        if i < len(elements) - 1:
            current_y += adjust_vertical_spacing(element, vertical_gap)
