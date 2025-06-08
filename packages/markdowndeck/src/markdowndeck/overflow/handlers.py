"""Core overflow handling strategies with unanimous consent model."""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.elements.base import Element
    from markdowndeck.models.slide import Section

from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)


class StandardOverflowHandler:
    """
    Standard overflow handling strategy implementing the unanimous consent model.

    This handler implements recursive partitioning with the new coordinated splitting
    algorithm that requires unanimous consent from all overflowing elements in
    columnar sections before proceeding with a split.
    """

    def __init__(self, body_height: float, top_margin: float = None):
        """
        Initialize the overflow handler.

        Args:
            body_height: The available height in the slide's body zone
            top_margin: The actual top margin used by the slide configuration.
            If None, defaults to DEFAULT_MARGIN_TOP for backward compatibility.
        """
        self.body_height = body_height

        # CRITICAL FIX: Calculate the absolute body_end_y coordinate
        # This is needed for correct available_height calculations
        from markdowndeck.layout.constants import (
            DEFAULT_MARGIN_TOP,
            HEADER_HEIGHT,
            HEADER_TO_BODY_SPACING,
        )

        actual_top_margin = top_margin if top_margin is not None else DEFAULT_MARGIN_TOP
        self.body_start_y = actual_top_margin + HEADER_HEIGHT + HEADER_TO_BODY_SPACING
        self.body_end_y = self.body_start_y + body_height

        logger.debug(
            f"StandardOverflowHandler initialized with body_height={body_height}, "
            f"top_margin={actual_top_margin}, body_start_y={self.body_start_y}, body_end_y={self.body_end_y}"
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
            f"Handling overflow for section {overflowing_section.id} at position {overflowing_section.position}"
        )

        # Store original non-body elements to preserve them
        from markdowndeck.models import ElementType

        original_meta_elements = [
            e
            for e in slide.elements
            if e.element_type
            in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]

        # Calculate available height before the overflowing section
        (overflowing_section.position[1] if overflowing_section.position else 0)
        # FIXED: Pass absolute Y boundary instead of relative height
        # since partitioning methods now check absolute positions
        available_height = self.body_end_y
        logger.debug(
            f"Using absolute boundary for overflow section: {available_height} (body_end_y={self.body_end_y})"
        )

        # Partition the overflowing section using the specification algorithm
        fitted_part, overflowing_part = self._partition_section(
            overflowing_section, available_height, visited=set()
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

        # Handle section modification based on fitted part
        if fitted_part:
            # Replace overflowing section with fitted part
            modified_original.sections[section_index] = fitted_part
            # Keep sections up to and including the fitted section
            modified_original.sections = modified_original.sections[: section_index + 1]
        else:
            # Create empty version of the section to preserve structure
            empty_section = deepcopy(overflowing_section)
            empty_section.children = []
            modified_original.sections[section_index] = empty_section
            # Keep sections up to and including the empty section
            modified_original.sections = modified_original.sections[: section_index + 1]

        # Update elements list to match the modified sections
        self._rebuild_elements_from_sections(modified_original, original_meta_elements)

        logger.info(
            f"Created continuation slide with {len(continuation_sections)} sections"
        )
        return modified_original, continuation_slide

    def _partition_section(
        self, section: "Section", available_height: float, visited: set[str] = None
    ) -> tuple["Section | None", "Section | None"]:
        """
        Recursively partition a section to fit within available height.

        Args:
            section: The section to partition
            available_height: The height available for this section
            visited: Set of section IDs already visited to prevent circular references

        Returns:
            Tuple of (fitted_part, overflowing_part). Either can be None.
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

        # Separate elements and child sections from unified children list
        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]
        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]

        if section_elements:
            # Rule A: Section has elements - standard partitioning
            logger.debug(f"Section {section.id}: Applying Rule A (has elements)")
            return self._apply_rule_a(section, available_height, visited)

        if child_sections:
            if section.type == "row":
                # Rule B: Coordinated row of columns partitioning
                logger.debug(
                    f"Section {section.id}: Applying Rule B (row with child sections)"
                )
                return self._apply_rule_b_unanimous_consent(
                    section, available_height, visited
                )
            # Standard subsection partitioning
            logger.debug(f"Section {section.id}: Standard child section partitioning")
            return self._partition_section_with_subsections(
                section, available_height, visited
            )

        # Empty section
        logger.warning(f"Empty section {section.id} encountered during partitioning")
        return None, None

    def _apply_rule_a(
        self, section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule A: Standard section partitioning with elements.

        This method implements the corrected overflow partitioning logic:
        1. Find the overflowing element
        2. Call .split() on that element
        3. Construct fitted_elements and overflowing_elements lists
        4. Create and return new Section objects

        Args:
            section: Section containing elements
            available_height: Available height for this section (absolute Y boundary)
            visited: Set of section IDs already visited

        Returns:
            Tuple of (fitted_part, overflowing_part)
        """
        # Get elements from unified children list
        section_elements = [
            child for child in section.children if not hasattr(child, "children")
        ]

        logger.debug(
            f"Applying Rule A to section {section.id} with {len(section_elements)} elements"
        )

        if not section_elements:
            return None, None

        # Step 1: Find the overflowing element
        overflow_element_index = -1
        overflow_element = None

        for i, element in enumerate(section_elements):
            if element.position and element.size:
                element_bottom = element.position[1] + element.size[1]
                # Check if this element's bottom exceeds the slide boundary
                if element_bottom > available_height:
                    overflow_element_index = i
                    overflow_element = element
                    break

        # Special case: If no element overflows individually, but we're being called
        # for an overflowing section, move all content to continuation slide
        #
        # This edge case can occur when:
        # 1. User manually specifies section height larger than content height
        # 2. Section has fixed directives that create artificial overflow
        #
        # In real-world usage, section heights are calculated by the layout manager
        # based on their content, so this scenario is rare. When it does occur,
        # the most logical behavior is to preserve content integrity by moving
        # the entire section to the continuation slide rather than artificially
        # splitting content that would otherwise fit.
        #
        # Design rationale: Splitting content that fits within boundaries would
        # create poor UX and break logical content flow. It's better to maintain
        # content coherence at the cost of some wasted space.
        if overflow_element_index == -1:
            logger.debug(
                "No individual element overflows, but section does. "
                "Moving entire section content to continuation slide to preserve logical content flow. "
                "This typically occurs when section height > content height due to manual directives."
            )
            # Return no fitted section, and overflowing section with all content
            overflowing_section = deepcopy(section)
            overflowing_section.position = None
            overflowing_section.size = None
            return None, overflowing_section

        logger.debug(f"Found overflowing element at index {overflow_element_index}")

        # Step 2: Call .split() on the overflowing element
        element_top = overflow_element.position[1] if overflow_element.position else 0
        remaining_height = max(0.0, available_height - element_top)

        fitted_part, overflowing_part = overflow_element.split(remaining_height)

        # Set positions on split elements to preserve layout information
        if fitted_part and overflow_element.position:
            fitted_part.position = overflow_element.position

        if overflowing_part and overflow_element.position:
            # Overflowing part will be repositioned on continuation slide,
            # but preserve original position info for now
            overflowing_part.position = overflow_element.position

        # Step 3: Construct fitted_elements list
        fitted_elements = []
        # Add all elements before the overflow point
        if overflow_element_index > 0:
            fitted_elements.extend(deepcopy(section_elements[:overflow_element_index]))
        # Add the fitted_part from the split (if any)
        if fitted_part:
            fitted_elements.append(fitted_part)

        # Step 4: Construct overflowing_elements list
        overflowing_elements = []
        # Add the overflowing_part from the split (if any)
        if overflowing_part:
            overflowing_elements.append(overflowing_part)
        # Add all elements after the overflow point
        if overflow_element_index + 1 < len(section_elements):
            overflowing_elements.extend(
                deepcopy(section_elements[overflow_element_index + 1 :])
            )

        # Step 5: Create and return new Section objects
        fitted_section = None
        overflowing_section = None

        if fitted_elements:
            fitted_section = deepcopy(section)
            fitted_section.children = fitted_elements

        if overflowing_elements:
            overflowing_section = deepcopy(section)
            overflowing_section.children = overflowing_elements
            # Reset position and size for continuation slide
            overflowing_section.position = None
            overflowing_section.size = None

        logger.debug(
            f"Rule A result: fitted={len(fitted_elements)} elements, "
            f"overflowing={len(overflowing_elements)} elements"
        )

        return fitted_section, overflowing_section

    def _apply_rule_b_unanimous_consent(
        self, row_section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Rule B: Coordinated row of columns partitioning with unanimous consent model.

        Per the specification: A split of the row section is only valid if EVERY
        overflowing element in EVERY column can be successfully split. If even one
        element in one column fails its minimum requirement check, the entire
        coordinated split is aborted.

        Args:
            row_section: Section of type "row" containing column subsections
            available_height: Available height for this row
            visited: Set of section IDs already visited

        Returns:
            Tuple of (fitted_row, overflowing_row)
        """
        # Get child sections from unified children list
        child_sections = [
            child for child in row_section.children if hasattr(child, "children")
        ]

        logger.debug(
            f"Applying Rule B (unanimous consent) to row section {row_section.id} with {len(child_sections)} columns"
        )

        if not child_sections:
            return None, None

        # Step 1: Identify all overflowing elements across all columns
        overflowing_elements_by_column = []

        for i, column in enumerate(child_sections):
            overflowing_element = self._find_overflowing_element_in_column(
                column, available_height
            )
            overflowing_elements_by_column.append((i, column, overflowing_element))

            if overflowing_element:
                logger.debug(
                    f"Column {i} has overflowing element: {overflowing_element.element_type}"
                )

        # Step 2: Test unanimous consent - all overflowing elements must be splittable
        split_tests = []

        for column_index, column, overflowing_element in overflowing_elements_by_column:
            if overflowing_element:
                # Calculate remaining height for this element
                remaining_height = self._calculate_remaining_height_for_element(
                    column, overflowing_element, available_height
                )

                # Test if element can split with minimum requirements
                if self._is_element_splittable(overflowing_element):
                    fitted_part, overflowing_part = overflowing_element.split(
                        remaining_height
                    )
                    can_split = fitted_part is not None
                else:
                    can_split = False

                split_tests.append((column_index, overflowing_element, can_split))

                if not can_split:
                    logger.info(
                        f"Column {column_index} element {overflowing_element.element_type} "
                        f"REJECTS split - unanimous consent FAILED"
                    )

        # Step 3: Check unanimous consent
        all_consent = all(can_split for _, _, can_split in split_tests)

        if not all_consent:
            logger.info(
                f"Unanimous consent FAILED for row section {row_section.id} - promoting entire row to next slide"
            )
            return None, deepcopy(row_section)

        # Step 4: Execute coordinated split (all columns consent)
        logger.info(
            f"Unanimous consent ACHIEVED for row section {row_section.id} - executing coordinated split"
        )

        fitted_columns = []
        overflowing_columns = []

        # CRITICAL FIX: Maintain column structure in continuation row
        # We need to create placeholders for ALL columns to preserve structure
        for _i, column in enumerate(child_sections):
            fitted_col, overflowing_col = self._partition_section(
                column, available_height, visited.copy()
            )

            if fitted_col:
                fitted_columns.append(fitted_col)
            else:
                # Create empty version of the column to preserve structure
                empty_fitted_col = deepcopy(column)
                empty_fitted_col.children = []
                fitted_columns.append(empty_fitted_col)

            if overflowing_col:
                overflowing_columns.append(overflowing_col)
            else:
                # CRITICAL: Create empty version of the column to preserve row structure
                # This ensures continuation row maintains the same number of columns
                empty_overflowing_col = deepcopy(column)
                empty_overflowing_col.children = []
                # Reset position for continuation slide
                empty_overflowing_col.position = None
                empty_overflowing_col.size = None
                overflowing_columns.append(empty_overflowing_col)

        # Construct result rows
        fitted_row = None
        overflowing_row = None

        if fitted_columns:
            fitted_row = deepcopy(row_section)
            fitted_row.children = fitted_columns

        # Always create continuation row with all columns (some may be empty)
        if overflowing_columns:
            overflowing_row = deepcopy(row_section)
            overflowing_row.children = overflowing_columns
            # Reset position for continuation slide
            overflowing_row.position = None
            overflowing_row.size = None

        logger.debug(
            f"Rule B unanimous consent result: fitted={len(fitted_columns)} columns, "
            f"overflowing={len(overflowing_columns)} columns"
        )

        return fitted_row, overflowing_row

    def _find_overflowing_element_in_column(
        self, column: "Section", available_height: float
    ) -> "Element | None":
        """
        Find the first element in a column that causes overflow.

        FIXED: Now respects pre-calculated positions from LayoutManager instead of
        re-implementing layout calculations.

        Args:
            column: The column section to analyze
            available_height: Available height boundary (absolute Y coordinate)

        Returns:
            The first overflowing element, or None if no overflow
        """
        # Get elements from unified children list
        column_elements = [
            child for child in column.children if not hasattr(child, "children")
        ]

        if not column_elements:
            return None

        for element in column_elements:
            if element.position and element.size:
                element_bottom = element.position[1] + element.size[1]

                # Check if this element's bottom exceeds the slide boundary
                if element_bottom > available_height:
                    return element

        return None

    def _calculate_remaining_height_for_element(
        self, column: "Section", target_element: "Element", available_height: float
    ) -> float:
        """
        Calculate how much height remains for a specific element in a column.

        FIXED: Now uses pre-calculated positions from LayoutManager instead of
        re-implementing layout calculations.

        Args:
            column: The column containing the element
            target_element: The element to calculate remaining height for
            available_height: Total available height (absolute Y boundary)

        Returns:
            Remaining height available for the target element
        """
        # Get elements from unified children list
        column_elements = [
            child for child in column.children if not hasattr(child, "children")
        ]

        if not column_elements:
            return available_height

        # Find the target element and use its absolute position
        for element in column_elements:
            if element is target_element:
                if element.position:
                    element_top = element.position[1]
                    return max(0.0, available_height - element_top)
                # Fallback if position is not set
                return available_height

        # Target element not found in column
        return available_height

    def _partition_section_with_subsections(
        self, section: "Section", available_height: float, visited: set[str]
    ) -> tuple["Section | None", "Section | None"]:
        """
        Partition a section containing subsections (non-row).

        Args:
            section: Section containing subsections
            available_height: Available height for this section
            visited: Set of section IDs already visited

        Returns:
            Tuple of (fitted_part, overflowing_part)
        """
        # Get child sections from unified children list
        child_sections = [
            child for child in section.children if hasattr(child, "children")
        ]

        # Find first overflowing subsection
        overflowing_subsection_index = -1

        for i, subsection in enumerate(child_sections):
            if subsection.position and subsection.size:
                subsection_bottom = subsection.position[1] + subsection.size[1]
                if subsection_bottom > available_height:
                    overflowing_subsection_index = i
                    break

        if overflowing_subsection_index == -1:
            # No overflow in subsections
            return deepcopy(section), None

        # Recursively partition the overflowing subsection
        overflowing_subsection = child_sections[overflowing_subsection_index]
        subsection_available_height = available_height - (
            overflowing_subsection.position[1] if overflowing_subsection.position else 0
        )

        fitted_subsection, overflowing_subsection_part = self._partition_section(
            overflowing_subsection, subsection_available_height, visited.copy()
        )

        # Build result sections
        fitted_section = None
        overflowing_section = None

        # Fitted part includes subsections before overflow point plus fitted part
        fitted_subsections = deepcopy(child_sections[:overflowing_subsection_index])
        if fitted_subsection:
            fitted_subsections.append(fitted_subsection)

        if fitted_subsections:
            fitted_section = deepcopy(section)
            fitted_section.children = fitted_subsections

        # Overflowing part includes overflowing part plus subsequent subsections
        overflowing_subsections = []
        if overflowing_subsection_part:
            overflowing_subsections.append(overflowing_subsection_part)
        overflowing_subsections.extend(
            deepcopy(child_sections[overflowing_subsection_index + 1 :])
        )

        if overflowing_subsections:
            overflowing_section = deepcopy(section)
            overflowing_section.children = overflowing_subsections
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
        # All elements should have a split method per the new specification
        has_split_method = hasattr(element, "split") and callable(element.split)
        logger.debug(
            f"Element {element.element_type} splittable check: has_split={has_split_method}"
        )
        return has_split_method

    def _rebuild_elements_from_sections(
        self, slide: "Slide", meta_elements: list
    ) -> None:
        """
        Rebuild the slide's flat .elements list from its sections.

        CRITICAL FIX: Removed deepcopy of section.elements to preserve position/size data
        that was set by the LayoutManager. The elements in the fitted/overflowing sections
        are already copies from the partitioning process.

        Args:
            slide: The slide to rebuild elements for
            meta_elements: The original title, subtitle, and footer elements to preserve
        """
        new_elements = list(meta_elements)  # Direct reference instead of deepcopy

        # Recursively extract elements from the modified sections
        visited_sections = set()

        def extract_elements(sections):
            for section in sections:
                # Circular reference protection
                if section.id in visited_sections:
                    logger.warning(
                        f"Circular reference detected in section {section.id} during element extraction. Skipping."
                    )
                    continue

                visited_sections.add(section.id)

                # Get elements and child sections from unified children list
                section_elements = [
                    child
                    for child in section.children
                    if not hasattr(child, "children")
                ]
                child_sections = [
                    child for child in section.children if hasattr(child, "children")
                ]

                if section_elements:
                    # CRITICAL: Use direct references to preserve position/size data
                    new_elements.extend(section_elements)
                if child_sections:
                    extract_elements(child_sections)

                visited_sections.remove(section.id)

        extract_elements(slide.sections)
        slide.elements = new_elements
