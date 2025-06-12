import logging
from copy import deepcopy
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.elements.base import Element
    from markdowndeck.models.slide import Section

from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Standard overflow handling strategy implementing the unanimous consent model.
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
            f"Created continuation slide with root section '{overflowing_part.id}'"
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

        if section_elements:
            return self._apply_rule_a(section, available_height, visited)
        if child_sections:
            if section.type == "row":
                return self._apply_rule_b_unanimous_consent(
                    section, available_height, visited
                )
            return self._partition_section_with_subsections(
                section, available_height, visited
            )

        logger.warning(f"Empty section {section.id} encountered during partitioning")
        return None, None

    def _apply_rule_a(
        self, section: "Section", available_height: float, visited: set[str]
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
            if element.position and element.size:
                element_bottom = element.position[1] + element.size[1]
                if element_bottom > available_height:
                    overflow_element_index = i
                    overflow_element = element
                    break
        if overflow_element_index == -1:
            return section, None
        element_top = overflow_element.position[1] if overflow_element.position else 0
        remaining_height = max(0.0, available_height - element_top)
        fitted_part, overflowing_part = overflow_element.split(remaining_height)
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
        return fitted_section, overflowing_section

    def _apply_rule_b_unanimous_consent(
        self, row_section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule B: Coordinated row of columns partitioning with unanimous consent model.
        """
        from markdowndeck.models.slide import Section

        child_sections = cast(
            list[Section],
            [child for child in row_section.children if hasattr(child, "children")],
        )
        logger.debug(
            f"Applying Rule B (unanimous consent) to row section {row_section.id} with {len(child_sections)} columns"
        )
        if not child_sections:
            return None, None

        can_split_flags = []
        for column in child_sections:
            overflowing_element = self._find_overflowing_element_in_column(
                column, available_height
            )
            if not overflowing_element:
                can_split_flags.append(True)
                continue
            remaining_height = self._calculate_remaining_height_for_element(
                column, overflowing_element, available_height
            )
            can_split_flags.append(
                self._is_element_splittable(overflowing_element, remaining_height)
            )

        if not all(can_split_flags):
            logger.info(
                f"Unanimous consent FAILED for row section {row_section.id}. Promoting entire row."
            )
            return None, deepcopy(row_section)

        logger.info(f"Unanimous consent ACHIEVED for row section {row_section.id}.")
        fitted_columns, overflowing_columns = [], []
        for column in child_sections:
            fitted_col, overflowing_col = self._partition_section(
                column, available_height, visited.copy()
            )
            fitted_columns.append(fitted_col or self._create_empty_section_like(column))
            if overflowing_col:
                overflowing_columns.append(overflowing_col)

        fitted_row = deepcopy(row_section)
        fitted_row.children = fitted_columns
        overflowing_row = None
        if any(col.children for col in overflowing_columns if col is not None):
            overflowing_row = deepcopy(row_section)
            overflowing_row.children = overflowing_columns
            overflowing_row.position = None
            overflowing_row.size = None

        return fitted_row, overflowing_row

    def _partition_section_with_subsections(
        self, section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """Partition a section that contains other nested sections."""
        from markdowndeck.models.slide import Section

        fitted_children, overflowing_children = [], []
        has_overflow = False
        child_sections = cast(list[Section], section.children)

        for child_section in child_sections:
            if has_overflow:
                overflowing_children.append(deepcopy(child_section))
                continue

            section_bottom = (
                (child_section.position[1] + child_section.size[1])
                if child_section.position and child_section.size
                else 0
            )
            if section_bottom > available_height:
                has_overflow = True
                fitted_part, overflowing_part = self._partition_section(
                    child_section, available_height, visited.copy()
                )
                if fitted_part:
                    fitted_children.append(fitted_part)
                if overflowing_part:
                    overflowing_children.append(overflowing_part)
            else:
                fitted_children.append(deepcopy(child_section))

        fitted_section = deepcopy(section) if fitted_children else None
        if fitted_section:
            fitted_section.children = fitted_children

        overflowing_section = deepcopy(section) if overflowing_children else None
        if overflowing_section:
            overflowing_section.children = overflowing_children
            overflowing_section.position = None
            overflowing_section.size = None

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

    def _find_overflowing_element_in_column(
        self, column: "Section", available_height: float
    ) -> "Element | None":
        for element in column.children:
            if not hasattr(element, "children") and element.position and element.size:
                if element.position[1] + element.size[1] > available_height:
                    return cast("Element", element)
        return None

    def _calculate_remaining_height_for_element(
        self, column: "Section", target_element: "Element", available_height: float
    ) -> float:
        if target_element.position:
            return max(0.0, available_height - target_element.position[1])
        return available_height

    def _is_element_splittable(
        self, element: "Element", available_height: float
    ) -> bool:
        if not hasattr(element, "split"):
            return False
        try:
            fitted, _ = element.split(available_height)
            return fitted is not None
        except Exception:
            return False

    def _create_empty_section_like(self, section: "Section") -> "Section":
        empty_section = deepcopy(section)
        empty_section.children = []
        return empty_section
