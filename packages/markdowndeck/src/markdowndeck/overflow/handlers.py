"""Core overflow handling strategies for content distribution."""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

from markdowndeck.overflow.constants import MINIMUM_CONTENT_RATIO_TO_SPLIT
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Standard overflow handling strategy with intelligent content partitioning.

    This handler implements a recursive partitioning algorithm that respects
    element relationships and applies smart splitting rules to create clean
    continuation slides.
    """

    def __init__(self, body_height: float):
        """
        Initialize the overflow handler.

        Args:
            body_height: The available height in the slide's body zone
        """
        self.body_height = body_height
        logger.debug(
            f"StandardOverflowHandler initialized with body_height={body_height}"
        )

    def handle_overflow(
        self, slide: "Slide", overflowing_section: "Section"
    ) -> tuple["Slide", "Slide"]:
        """
        Handle overflow by partitioning the overflowing section and creating a continuation slide.

        Args:
            slide: The original slide with overflow
            overflowing_section: The first section that overflows

        Returns:
            Tuple of (modified_original_slide, continuation_slide)
        """
        logger.info(
            f"Handling overflow for section at position {overflowing_section.position}"
        )

        # Calculate available height before the overflowing section
        available_height = self.body_height - overflowing_section.position[1]
        logger.debug(f"Available height for overflow section: {available_height}")

        # Partition the overflowing section
        fitted_part, overflowing_part = self._partition_section(
            overflowing_section, available_height
        )

        # Find the index of the overflowing section in the original slide
        section_index = -1
        for i, section in enumerate(slide.sections):
            if section is overflowing_section:
                section_index = i
                break

        if section_index == -1:
            logger.error("Could not find overflowing section in slide sections list")
            return slide, slide  # Fallback - return duplicate slides

        # Collect subsequent sections that should move to continuation slide
        subsequent_sections = slide.sections[section_index + 1 :]

        # Create sections for continuation slide
        continuation_sections = []
        if overflowing_part:
            continuation_sections.append(overflowing_part)
        continuation_sections.extend(deepcopy(subsequent_sections))

        # Create continuation slide
        slide_builder = SlideBuilder(slide)
        continuation_slide = slide_builder.create_continuation_slide(
            continuation_sections, 1
        )

        # Modify original slide
        modified_original = deepcopy(slide)

        # Replace overflowing section with fitted part (if any)
        if fitted_part:
            modified_original.sections[section_index] = fitted_part
        else:
            # Remove the section entirely if nothing fits
            modified_original.sections.pop(section_index)

        # Remove all subsequent sections from original slide
        modified_original.sections = modified_original.sections[
            : section_index + (1 if fitted_part else 0)
        ]

        # Update elements list to match the modified sections
        self._rebuild_elements_from_sections(modified_original)

        logger.info(
            f"Created continuation slide with {len(continuation_sections)} sections"
        )
        return modified_original, continuation_slide

    def _partition_section(
        self, section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Recursively partition a section to fit within available height.

        Args:
            section: The section to partition
            available_height: The height available for this section

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
        """
        logger.debug(
            f"Partitioning section {section.id} with available_height={available_height}"
        )

        if section.elements:
            # Base case: Section has elements - apply Rule A
            return self._apply_rule_a(section, available_height)

        if section.subsections:
            # Recursive case: Section has subsections
            if section.type == "row":
                # Rule B: Row of columns partitioning
                return self._apply_rule_b(section, available_height)
            # Standard subsection partitioning
            return self._partition_section_with_subsections(section, available_height)

        # Empty section
        logger.warning(f"Empty section {section.id} encountered during partitioning")
        return None, None

    def _apply_rule_a(
        self, section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule A: Standard section partitioning with elements.

        Args:
            section: Section containing elements
            available_height: Available height for this section

        Returns:
            Tuple of (fitted_part, overflowing_part)
        """
        logger.debug(
            f"Applying Rule A to section {section.id} with {len(section.elements)} elements"
        )

        if not section.elements:
            return None, None

        # Calculate section width for element measurements
        section_width = section.size[0] if section.size else 400.0

        # Find the split point among elements
        fitted_elements = []
        current_height = 0.0
        split_element_parts = None

        for i, element in enumerate(section.elements):
            # Calculate height this element would require
            from markdowndeck.layout.metrics import calculate_element_height

            element_height = calculate_element_height(element, section_width)

            if current_height + element_height <= available_height:
                # Element fits completely
                fitted_elements.append(deepcopy(element))
                current_height += element_height
            else:
                # Element crosses the boundary - apply threshold rule
                remaining_height = available_height - current_height

                # Check if element is splittable and meets threshold
                if self._is_element_splittable(element) and self._meets_split_threshold(
                    element, remaining_height, section_width
                ):
                    # Split the element
                    logger.debug(
                        f"Splitting element {element.element_type} at threshold"
                    )
                    fitted_part, overflowing_part = element.split(remaining_height)

                    if fitted_part:
                        fitted_elements.append(fitted_part)

                    if overflowing_part:
                        split_element_parts = (fitted_part, overflowing_part, i)
                else:
                    # Don't split - promote entire element to next slide
                    logger.debug(
                        f"Promoting entire element {element.element_type} to next slide"
                    )
                    split_element_parts = (None, element, i)

                break

        # Construct result sections
        fitted_section = None
        overflowing_section = None

        if fitted_elements:
            fitted_section = deepcopy(section)
            fitted_section.elements = fitted_elements
            # Update section size
            fitted_section.size = (section_width, current_height)

        # Handle overflowing elements
        overflowing_elements = []

        if split_element_parts:
            _, overflowing_element_part, split_index = split_element_parts

            if overflowing_element_part:
                overflowing_elements.append(overflowing_element_part)

            # Add all subsequent elements
            overflowing_elements.extend(deepcopy(section.elements[split_index + 1 :]))

        if overflowing_elements:
            overflowing_section = deepcopy(section)
            overflowing_section.elements = overflowing_elements
            # Reset position for continuation slide
            overflowing_section.position = None
            overflowing_section.size = None

        logger.debug(
            f"Rule A result: fitted={len(fitted_elements) if fitted_elements else 0} elements, "
            f"overflowing={len(overflowing_elements)} elements"
        )

        return fitted_section, overflowing_section

    def _apply_rule_b(
        self, row_section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule B: Row of columns partitioning.

        Args:
            row_section: Section of type "row" containing column subsections
            available_height: Available height for this row

        Returns:
            Tuple of (fitted_row, overflowing_row)
        """
        logger.debug(
            f"Applying Rule B to row section {row_section.id} with {len(row_section.subsections)} columns"
        )

        if not row_section.subsections:
            return None, None

        # Find the tallest column and identify overflowing elements
        tallest_column = None
        max_height = 0.0
        overflowing_element = None

        for column in row_section.subsections:
            if column.size and column.size[1] > max_height:
                max_height = column.size[1]
                tallest_column = column

        if not tallest_column:
            logger.warning("Could not identify tallest column in row section")
            return None, deepcopy(row_section)

        # Find the overflowing element in the tallest column
        if tallest_column.elements:
            column_width = tallest_column.size[0] if tallest_column.size else 400.0
            current_y = 0.0

            for element in tallest_column.elements:
                from markdowndeck.layout.metrics import calculate_element_height

                element_height = calculate_element_height(element, column_width)
                if current_y + element_height > available_height:
                    overflowing_element = element
                    break
                current_y += element_height

        # Check if overflowing element is splittable
        if overflowing_element and not self._is_element_splittable(overflowing_element):
            # Entire row is atomic
            logger.debug(
                "Row contains unsplittable overflowing element - promoting entire row"
            )
            return None, deepcopy(row_section)

        # Determine vertical split point (Y-coordinate)
        split_y = available_height

        # Partition all columns at the same Y-coordinate
        fitted_columns = []
        overflowing_columns = []

        for column in row_section.subsections:
            fitted_col, overflowing_col = self._partition_section(column, split_y)

            if fitted_col:
                fitted_columns.append(fitted_col)
            if overflowing_col:
                overflowing_columns.append(overflowing_col)

        # Construct result rows
        fitted_row = None
        overflowing_row = None

        if fitted_columns:
            fitted_row = deepcopy(row_section)
            fitted_row.subsections = fitted_columns

        if overflowing_columns:
            overflowing_row = deepcopy(row_section)
            overflowing_row.subsections = overflowing_columns
            # Reset position for continuation slide
            overflowing_row.position = None
            overflowing_row.size = None

        logger.debug(
            f"Rule B result: fitted={len(fitted_columns)} columns, "
            f"overflowing={len(overflowing_columns)} columns"
        )

        return fitted_row, overflowing_row

    def _partition_section_with_subsections(
        self, section: "Section", available_height: float
    ) -> tuple["Section | None", "Section | None"]:
        """
        Partition a section containing subsections (non-row).

        Args:
            section: Section containing subsections
            available_height: Available height for this section

        Returns:
            Tuple of (fitted_part, overflowing_part)
        """
        # Find first overflowing subsection
        overflowing_subsection_index = -1

        for i, subsection in enumerate(section.subsections):
            if subsection.position and subsection.size:
                subsection_bottom = subsection.position[1] + subsection.size[1]
                if subsection_bottom > available_height:
                    overflowing_subsection_index = i
                    break

        if overflowing_subsection_index == -1:
            # No overflow in subsections
            return deepcopy(section), None

        # Recursively partition the overflowing subsection
        overflowing_subsection = section.subsections[overflowing_subsection_index]
        subsection_available_height = available_height - (
            overflowing_subsection.position[1] if overflowing_subsection.position else 0
        )

        fitted_subsection, overflowing_subsection_part = self._partition_section(
            overflowing_subsection, subsection_available_height
        )

        # Build result sections
        fitted_section = None
        overflowing_section = None

        # Fitted part includes subsections before overflow point plus fitted part of overflowing subsection
        fitted_subsections = deepcopy(
            section.subsections[:overflowing_subsection_index]
        )
        if fitted_subsection:
            fitted_subsections.append(fitted_subsection)

        if fitted_subsections:
            fitted_section = deepcopy(section)
            fitted_section.subsections = fitted_subsections

        # Overflowing part includes overflowing part of subsection plus all subsequent subsections
        overflowing_subsections = []
        if overflowing_subsection_part:
            overflowing_subsections.append(overflowing_subsection_part)
        overflowing_subsections.extend(
            deepcopy(section.subsections[overflowing_subsection_index + 1 :])
        )

        if overflowing_subsections:
            overflowing_section = deepcopy(section)
            overflowing_section.subsections = overflowing_subsections
            # Reset position for continuation slide
            overflowing_section.position = None
            overflowing_section.size = None

        return fitted_section, overflowing_section

    def _is_element_splittable(self, element) -> bool:
        """
        Check if an element supports splitting.

        Args:
            element: The element to check

        Returns:
            True if the element can be split across slides
        """
        # Images are atomic
        from markdowndeck.models import ElementType

        if element.element_type == ElementType.IMAGE:
            return False

        # Check if element has a split method
        return hasattr(element, "split") and callable(element.split)

    def _meets_split_threshold(
        self, element, available_height: float, element_width: float
    ) -> bool:
        """
        Apply the threshold rule to determine if an element should be split.

        Args:
            element: The element to check
            available_height: Height available for this element
            element_width: Width of the element

        Returns:
            True if the element should be split (meets minimum ratio threshold)
        """
        from markdowndeck.layout.metrics import calculate_element_height

        total_element_height = calculate_element_height(element, element_width)

        if total_element_height == 0:
            return False

        ratio_that_fits = available_height / total_element_height
        meets_threshold = ratio_that_fits >= MINIMUM_CONTENT_RATIO_TO_SPLIT

        logger.debug(
            f"Threshold check: ratio={ratio_that_fits:.2f}, threshold={MINIMUM_CONTENT_RATIO_TO_SPLIT}, meets={meets_threshold}"
        )

        return meets_threshold

    def _rebuild_elements_from_sections(self, slide: "Slide") -> None:
        """
        Rebuild the slide's elements list from its sections.

        Args:
            slide: The slide to rebuild elements for
        """
        slide.elements = []

        # Keep title and footer elements
        original_elements = []
        original_elements = (
            slide._original_elements
            if hasattr(slide, "_original_elements")
            else deepcopy(slide.elements)
        )

        for element in original_elements:
            from markdowndeck.models import ElementType

            if element.element_type in (ElementType.TITLE, ElementType.FOOTER):
                slide.elements.append(element)

        # Extract elements from sections
        def extract_elements(sections):
            for section in sections:
                if section.elements:
                    slide.elements.extend(deepcopy(section.elements))
                if section.subsections:
                    extract_elements(section.subsections)

        extract_elements(slide.sections)
