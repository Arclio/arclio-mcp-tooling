"""Updated overflow handlers with clean imports and improved error handling."""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING

# Clean import organization - avoid duplicates
if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

from markdowndeck.models.constants import ElementType
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Standard overflow handling strategy implementing the unanimous consent model.
    Updated with cleaner imports and better error handling.
    """

    def __init__(self, slide_height: float, top_margin: float):
        self.slide_height = slide_height
        self.top_margin = top_margin
        logger.debug(
            f"StandardOverflowHandler initialized. Slide height: {self.slide_height}, Top margin: {self.top_margin}"
        )

    def handle_overflow(
        self, slide: "Slide", overflowing_section: "Section", continuation_number: int
    ) -> tuple["Slide", "Slide | None"]:
        """
        Handle overflow by partitioning the overflowing section and creating a continuation slide.
        """
        logger.info(
            f"Handling overflow for section {overflowing_section.id} at position {overflowing_section.position}"
        )

        _body_start_y, body_end_y = self._calculate_body_boundaries(slide)
        available_height = body_end_y
        logger.debug(
            f"Using absolute boundary for overflow section: {available_height} (body_end_y={body_end_y})"
        )

        fitted_part, overflowing_part = self._partition_section(
            overflowing_section, available_height, visited=set()
        )

        has_content = self._has_actual_content(
            [overflowing_part] if overflowing_part else []
        )

        if not has_content:
            logger.info(
                "No overflowing content found; no continuation slide will be created."
            )
            modified_original = deepcopy(slide)
            modified_original.root_section = fitted_part
            return modified_original, None

        slide_builder = SlideBuilder(slide)
        continuation_slide = slide_builder.create_continuation_slide(
            overflowing_part, continuation_number
        )

        modified_original = deepcopy(slide)
        modified_original.root_section = fitted_part

        logger.info(
            f"Created continuation slide with root section '{getattr(overflowing_part, 'id', 'N/A')}'"
        )
        return modified_original, continuation_slide

    def _calculate_body_boundaries(self, slide: "Slide") -> tuple[float, float]:
        """Calculates the dynamic body area for a specific slide."""
        from markdowndeck.layout.constants import (
            DEFAULT_MARGIN_BOTTOM,
            HEADER_TO_BODY_SPACING,
        )

        top_offset = self.top_margin
        bottom_offset = DEFAULT_MARGIN_BOTTOM
        title = slide.get_title_element()
        if title and title.size and title.position:
            top_offset = title.position[1] + title.size[1] + HEADER_TO_BODY_SPACING
        footer = slide.get_footer_element()
        if footer and footer.size and footer.position:
            bottom_offset = self.slide_height - footer.position[1]
        body_start_y = top_offset
        body_end_y = self.slide_height - bottom_offset
        return body_start_y, body_end_y

    def _partition_section(
        self, section: "Section", available_height: float, visited: set[str] = None
    ) -> tuple["Section | None", "Section | None"]:
        """
        Recursively partition a section to fit within available height.
        """
        if visited is None:
            visited = set()
        if section.id in visited:
            logger.warning(
                f"Circular reference detected for section {section.id}. Stopping partition."
            )
            return None, None
        visited.add(section.id)

        logger.debug(
            f"Partitioning section {section.id} with available_height={available_height}"
        )

        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]
        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]

        if child_sections:
            if section.type == "row":
                return self._apply_rule_b_unanimous_consent(
                    section, available_height, visited
                )
            return self._partition_section_with_subsections(
                section, available_height, visited
            )
        if section_elements:
            return self._apply_rule_a(section, available_height)

        logger.warning(f"Empty section {section.id} encountered during partitioning")
        return None, None

    def _apply_rule_a(
        self, section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule A: Standard section partitioning with elements.
        """
        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]
        if not section_elements:
            return None, None

        overflow_element_index = -1
        overflow_element = None
        for i, element in enumerate(section_elements):
            if element.position and element.size and element.size[1] > 0:
                element_bottom = element.position[1] + element.size[1]
                if element_bottom > available_height:
                    overflow_element_index = i
                    overflow_element = element
                    break

        if overflow_element_index == -1:
            return section, None

        element_top = overflow_element.position[1] if overflow_element.position else 0
        remaining_height = max(0.0, available_height - element_top)

        # FIXED: Proactively check for unsplittable elements per OVERFLOW_SPEC.md Rule #2.
        # This avoids calling .split() on an ImageElement, which would raise NotImplementedError.
        if overflow_element.element_type in [ElementType.IMAGE]:
            logger.debug(
                f"Unsplittable element {overflow_element.element_type.value} caused overflow. Moving entirely."
            )
            fitted_part, overflowing_part = None, deepcopy(overflow_element)
        elif hasattr(overflow_element, "split"):
            fitted_part, overflowing_part = overflow_element.split(remaining_height)
        else:
            logger.warning(
                f"Element type {overflow_element.element_type.value} does not have a .split() method. Treating as atomic."
            )
            fitted_part, overflowing_part = None, deepcopy(overflow_element)

        if fitted_part and overflow_element.position:
            fitted_part.position = overflow_element.position

        fitted_elements = deepcopy(section_elements[:overflow_element_index])
        if fitted_part:
            fitted_elements.append(fitted_part)

        overflowing_elements = []
        if overflowing_part:
            overflowing_elements.append(overflowing_part)
        if overflow_element_index + 1 < len(section_elements):
            overflowing_elements.extend(
                deepcopy(section_elements[overflow_element_index + 1 :])
            )

        fitted_section = None
        if fitted_elements:
            fitted_section = deepcopy(section)
            fitted_section.children = fitted_elements

        overflowing_section = None
        if overflowing_elements:
            overflowing_section = deepcopy(section)
            overflowing_section.children = overflowing_elements
            overflowing_section.position = None
            overflowing_section.size = None
            # FIXED: Do not propagate problematic directives per OVERFLOW_SPEC.md Rule #3.
            # This prevents infinite loops caused by fixed-height containers.
            if "height" in overflowing_section.directives:
                logger.debug(
                    f"Removing problematic [height] directive from overflowing section {overflowing_section.id}"
                )
                del overflowing_section.directives["height"]

        return fitted_section, overflowing_section

    def _apply_rule_b_unanimous_consent(
        self, row_section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule B: Coordinated row of columns partitioning with unanimous consent model.
        """
        child_sections = [
            child for child in row_section.children if hasattr(child, "children")
        ]
        if not child_sections:
            return row_section, None

        row_bottom = (
            (row_section.position[1] + row_section.size[1])
            if row_section.position and row_section.size
            else 0
        )
        if row_bottom <= available_height:
            return row_section, None

        logger.info(
            f"Row section {row_section.id} overflows. Promoting entire row to next slide."
        )
        return None, deepcopy(row_section)

    def _partition_section_with_subsections(
        self, section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Partition a section by moving whole child sections, not splitting them.
        """
        fitted_children, overflowing_children = [], []
        has_overflowed = False

        for child_section in section.children:
            is_element = not hasattr(child_section, "children")
            position = getattr(child_section, "position", None)
            size = getattr(child_section, "size", None)

            if is_element or not position or not size:
                if not has_overflowed:
                    fitted_children.append(deepcopy(child_section))
                else:
                    overflowing_children.append(deepcopy(child_section))
                continue

            section_bottom = position[1] + size[1]
            if not has_overflowed and section_bottom <= available_height:
                fitted_children.append(deepcopy(child_section))
            else:
                has_overflowed = True
                overflowing_children.append(deepcopy(child_section))

        fitted_section = deepcopy(section) if fitted_children else None
        if fitted_section:
            fitted_section.children = fitted_children

        overflowing_section = deepcopy(section) if overflowing_children else None
        if overflowing_section:
            overflowing_section.children = overflowing_children
            overflowing_section.position = None
            overflowing_section.size = None
            if "height" in overflowing_section.directives:
                del overflowing_section.directives["height"]

        return fitted_section, overflowing_section

    def _has_actual_content(self, sections: list["Section"]) -> bool:
        if not sections:
            return False
        for section in sections:
            if not section:
                continue
            for child in section.children:
                if not hasattr(child, "children"):
                    return True
                if self._has_actual_content([child]):
                    return True
        return False
