"""
Enhanced overflow handler integrated with the new two-pass layout system.

IMPROVEMENTS:
- Better integration with the new layout algorithm
- Proper handling of unsplittable elements (Rule #2 compliance)
- Enhanced position/size clearing for continuation slides
- Improved problematic directive removal (Rule #3 compliance)
"""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

from markdowndeck.models.constants import ElementType
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Enhanced overflow handling strategy implementing the unanimous consent model
    with better integration for the new two-pass layout system.
    """

    def __init__(self, slide_height: float, top_margin: float):
        self.slide_height = slide_height
        self.top_margin = top_margin
        logger.debug(
            f"StandardOverflowHandler initialized. Slide height: {self.slide_height}, "
            f"Top margin: {self.top_margin}"
        )

    def handle_overflow(
        self, slide: "Slide", overflowing_section: "Section", continuation_number: int
    ) -> tuple["Slide", "Slide | None"]:
        """
        Handle overflow by partitioning the overflowing section and creating a continuation slide.
        """
        logger.info(
            f"Handling overflow for section {overflowing_section.id} "
            f"at position {overflowing_section.position}"
        )

        _body_start_y, body_end_y = self._calculate_body_boundaries(slide)
        available_height = body_end_y

        logger.debug(
            f"Using absolute boundary for overflow section: {available_height} "
            f"(body_end_y={body_end_y})"
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
            f"Created continuation slide with root section "
            f"'{getattr(overflowing_part, 'id', 'N/A')}'"
        )
        return modified_original, continuation_slide

    def _calculate_body_boundaries(self, slide: "Slide") -> tuple[float, float]:
        """Calculate the dynamic body area for a specific slide."""
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
        Enhanced to work with the new two-pass layout system.
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

        # Separate elements and child sections
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
        elif section_elements:
            return self._apply_rule_a(section, available_height)

        logger.warning(f"Empty section {section.id} encountered during partitioning")
        return None, None

    def _apply_rule_a(
        self, section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule A: Standard section partitioning with elements.
        Enhanced with better unsplittable element handling.
        """
        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]
        if not section_elements:
            return None, None

        # Find the first element that overflows
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
            # No overflow detected
            return section, None

        # Calculate remaining height for the overflowing element
        element_top = overflow_element.position[1] if overflow_element.position else 0
        remaining_height = max(0.0, available_height - element_top)

        # Handle element splitting with proper unsplittable element detection
        fitted_part, overflowing_part = self._split_element_safely(
            overflow_element, remaining_height
        )

        # Restore position for fitted part if it exists
        if fitted_part and overflow_element.position:
            fitted_part.position = overflow_element.position

        # Build fitted section
        fitted_elements = deepcopy(section_elements[:overflow_element_index])
        if fitted_part:
            fitted_elements.append(fitted_part)

        # Build overflowing section
        overflowing_elements = []
        if overflowing_part:
            overflowing_elements.append(overflowing_part)
        if overflow_element_index + 1 < len(section_elements):
            overflowing_elements.extend(
                deepcopy(section_elements[overflow_element_index + 1 :])
            )

        # Create fitted section
        fitted_section = None
        if fitted_elements:
            fitted_section = deepcopy(section)
            fitted_section.children = fitted_elements

        # Create overflowing section with enhanced cleanup
        overflowing_section = None
        if overflowing_elements:
            overflowing_section = deepcopy(section)
            overflowing_section.children = overflowing_elements

            # Enhanced cleanup for continuation slides
            self._cleanup_for_continuation(overflowing_section)

        return fitted_section, overflowing_section

    def _split_element_safely(self, element, remaining_height: float) -> tuple:
        """
        Safely split an element, proactively checking for unsplittable types.
        This implements Rule #2 by avoiding calls to .split() on unsplittable elements.
        """
        # Proactively check for known unsplittable element types
        if element.element_type in [ElementType.IMAGE]:
            logger.debug(
                f"Element {element.element_type.value} is unsplittable by design. "
                f"Moving entirely to continuation slide."
            )
            return None, deepcopy(element)

        # Try to split splittable elements
        if hasattr(element, "split") and callable(element.split):
            try:
                fitted_part, overflowing_part = element.split(remaining_height)
                logger.debug(
                    f"Successfully split {element.element_type.value} element. "
                    f"Fitted: {fitted_part is not None}, "
                    f"Overflowing: {overflowing_part is not None}"
                )
                return fitted_part, overflowing_part
            except NotImplementedError:
                logger.warning(
                    f"Element {element.element_type.value} .split() raised "
                    f"NotImplementedError. Treating as unsplittable."
                )
                return None, deepcopy(element)
            except Exception as e:
                logger.error(
                    f"Error splitting {element.element_type.value}: {e}. "
                    f"Treating as unsplittable."
                )
                return None, deepcopy(element)
        else:
            logger.warning(
                f"Element type {element.element_type.value} does not have a "
                f".split() method. Treating as atomic."
            )
            return None, deepcopy(element)

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

        # Check if the entire row overflows
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

        # Create a cleaned copy for the continuation slide
        overflowing_row = deepcopy(row_section)
        self._cleanup_for_continuation(overflowing_row)

        return None, overflowing_row

    def _partition_section_with_subsections(
        self, section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Partition a section by splitting child sections when they overflow.
        """
        fitted_children, overflowing_children = [], []
        has_overflowed = False

        for child_section in section.children:
            is_element = not hasattr(child_section, "children")
            position = getattr(child_section, "position", None)
            size = getattr(child_section, "size", None)

            if is_element:
                # Handle elements directly
                if not has_overflowed:
                    fitted_children.append(deepcopy(child_section))
                else:
                    overflowing_children.append(deepcopy(child_section))
                continue

            if not position or not size:
                # Section without position/size - treat as non-overflowing
                if not has_overflowed:
                    fitted_children.append(deepcopy(child_section))
                else:
                    overflowing_children.append(deepcopy(child_section))
                continue

            section_bottom = position[1] + size[1]
            if not has_overflowed and section_bottom <= available_height:
                # Section fits completely
                fitted_children.append(deepcopy(child_section))
            else:
                # Section overflows - try to split it
                has_overflowed = True

                # Calculate available height for this child section
                child_available_height = (
                    available_height - position[1] if position else available_height
                )

                # Recursively partition the child section
                fitted_child, overflowing_child = self._partition_section(
                    child_section, child_available_height, visited
                )

                if fitted_child:
                    fitted_children.append(fitted_child)
                if overflowing_child:
                    overflowing_children.append(overflowing_child)

        # Create sections
        fitted_section = deepcopy(section) if fitted_children else None
        if fitted_section:
            fitted_section.children = fitted_children

        overflowing_section = deepcopy(section) if overflowing_children else None
        if overflowing_section:
            overflowing_section.children = overflowing_children
            self._cleanup_for_continuation(overflowing_section)

        return fitted_section, overflowing_section

    def _cleanup_for_continuation(self, section: "Section") -> None:
        """
        Enhanced cleanup for continuation slides that works with the new layout system.
        """
        # Clear position and size for the section itself
        section.position = None
        section.size = None

        # Remove problematic directives per Rule #3
        problematic_directives = ["height"]
        for directive in problematic_directives:
            if directive in section.directives:
                logger.debug(
                    f"Removing problematic [{directive}] directive from "
                    f"overflowing section {section.id}"
                )
                del section.directives[directive]

        # Recursively clear position and size of all children
        self._clear_positions_recursive(section)

    def _clear_positions_recursive(self, section: "Section") -> None:
        """
        Recursively clear position and size for all children to ensure
        the layout manager recalculates everything from scratch.
        """
        for child in section.children:
            if hasattr(child, "position"):
                child.position = None
            if hasattr(child, "size"):
                child.size = None

            # Recursively clear child sections
            if hasattr(child, "children"):
                self._clear_positions_recursive(child)

    def _has_actual_content(self, sections: list["Section"]) -> bool:
        """Check if sections contain any actual renderable content."""
        if not sections:
            return False

        for section in sections:
            if not section:
                continue
            for child in section.children:
                if not hasattr(child, "children"):
                    # This is an element, so we have content
                    return True
                if self._has_actual_content([child]):
                    return True
        return False
