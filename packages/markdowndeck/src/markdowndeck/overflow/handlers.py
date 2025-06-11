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
        self, slide: "Slide", overflowing_section: "Section", continuation_number: int
    ) -> tuple["Slide", "Slide | None"]:
        """
        Handle overflow by partitioning the overflowing section and creating a continuation slide.

        Args:
            slide: The original slide with overflow
            overflowing_section: The first section that overflows
            continuation_number: The sequence number for this continuation.

        Returns:
            Tuple of (modified_original_slide, continuation_slide | None)
        """
        logger.info(
            f"Handling overflow for section {overflowing_section.id} at position {overflowing_section.position}"
        )

        available_height = self.body_end_y
        logger.debug(
            f"Using absolute boundary for overflow section: {available_height} (body_end_y={self.body_end_y})"
        )

        fitted_part, overflowing_part = self._partition_section(
            overflowing_section, available_height, visited=set()
        )

        section_index = -1
        for i, section in enumerate(slide.sections):
            if section is overflowing_section:
                section_index = i
                break

        if section_index == -1:
            logger.error("Could not find overflowing section in slide sections list")
            return slide, None

        subsequent_sections = slide.sections[section_index + 1 :]
        continuation_sections = []
        if overflowing_part:
            continuation_sections.append(overflowing_part)
        continuation_sections.extend(deepcopy(subsequent_sections))

        # Check if continuation slide should be created per OVERFLOW_SPEC.md Rule #6.3
        # A continuation slide must not be created if there's no actual content to move
        has_content = self._has_actual_content(continuation_sections)
        logger.debug(
            f"Content check: continuation_sections={len(continuation_sections)}, has_content={has_content}"
        )

        if not has_content:
            logger.info(
                "No overflowing content found; no continuation slide will be created."
            )
            modified_original = deepcopy(slide)
            if fitted_part:
                modified_original.sections = slide.sections[:section_index] + [
                    fitted_part
                ]
            else:
                modified_original.sections = slide.sections[:section_index]
            return modified_original, None

        slide_builder = SlideBuilder(slide)
        continuation_slide = slide_builder.create_continuation_slide(
            continuation_sections, continuation_number
        )

        modified_original = deepcopy(slide)
        if fitted_part:
            modified_original.sections = slide.sections[:section_index] + [fitted_part]
        else:
            modified_original.sections = slide.sections[:section_index]

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

        if overflow_element_index == -1:
            logger.debug(
                "No individual element overflows, but section does. "
                "Testing if any element would actually produce overflow content when split."
            )
            # Test each element to see if splitting would actually create overflow content
            has_actual_overflow = False
            for element in section_elements:
                if hasattr(element, "split"):
                    try:
                        # Calculate available height for this element
                        if element.position:
                            element_top = element.position[1]
                            remaining_height = max(0.0, available_height - element_top)
                        else:
                            remaining_height = available_height

                        fitted_part, overflowing_part = element.split(remaining_height)
                        if overflowing_part is not None:
                            has_actual_overflow = True
                            break
                    except Exception:
                        # If split fails, assume it can't be split
                        pass

            if not has_actual_overflow:
                logger.debug(
                    "No elements would actually produce overflow content when split. "
                    "Section dimensions may be wrong - keeping content on current slide."
                )
                return section, None

            logger.debug(
                "Elements would produce overflow content - applying progressive element reduction."
            )

            # Apply progressive element reduction algorithm
            # Find first element that produces overflow content when split
            fitted_elements = []
            overflowing_elements = []

            for i, element in enumerate(section_elements):
                if hasattr(element, "split"):
                    try:
                        # Calculate available height for this element
                        if element.position:
                            element_top = element.position[1]
                            remaining_height = max(0.0, available_height - element_top)
                        else:
                            remaining_height = available_height

                        fitted_part, overflowing_part = element.split(remaining_height)

                        if overflowing_part is not None:
                            # This element produces overflow - stop here
                            if fitted_part:
                                fitted_elements.append(fitted_part)

                            # Build the overflowing elements list
                            # The overflow starts from the overflowing_part and includes elements after current
                            # Check if overflowing_part is one of the remaining elements (next progression)
                            remaining_elements = section_elements[i + 1 :]

                            # If the overflowing_part matches the next element, this is a progression
                            if (
                                remaining_elements
                                and overflowing_part is remaining_elements[0]
                            ):
                                # Progression case: continue from the next element onwards
                                overflowing_elements.extend(
                                    deepcopy(remaining_elements)
                                )
                            else:
                                # Standard case: add overflowing_part + remaining elements
                                if overflowing_part:
                                    overflowing_elements.append(overflowing_part)
                                overflowing_elements.extend(
                                    deepcopy(remaining_elements)
                                )
                            break
                        # This element fits completely
                        fitted_elements.append(deepcopy(element))
                    except Exception:
                        # If split fails, assume it can't be split - add to fitted
                        fitted_elements.append(deepcopy(element))
                else:
                    # No split method - add to fitted
                    fitted_elements.append(deepcopy(element))

            # Create result sections
            fitted_section = None
            overflowing_section = None

            if fitted_elements:
                fitted_section = deepcopy(section)
                fitted_section.children = fitted_elements

            if overflowing_elements:
                overflowing_section = deepcopy(section)
                overflowing_section.children = overflowing_elements
                overflowing_section.position = None
                overflowing_section.size = None

            logger.debug(
                f"Progressive reduction result: fitted={len(fitted_elements)} elements, "
                f"overflowing={len(overflowing_elements)} elements"
            )

            return fitted_section, overflowing_section

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
        fitted_elements = deepcopy(section_elements[:overflow_element_index])
        if fitted_part:
            fitted_elements.append(fitted_part)

        # Step 4: Construct overflowing_elements list
        # THIS IS THE CRITICAL FIX: The overflowing_part from the split
        # represents the remainder of the element being split. All subsequent
        # elements must also be moved to the overflow.
        overflowing_elements = []
        if overflowing_part:
            overflowing_elements.append(overflowing_part)

        # Add all elements that came _after_ the one that was split.
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

        for _i, column in enumerate(child_sections):
            fitted_col, overflowing_col = self._partition_section(
                column, available_height, visited.copy()
            )

            if fitted_col:
                fitted_columns.append(fitted_col)
            else:
                empty_fitted_col = deepcopy(column)
                empty_fitted_col.children = []
                fitted_columns.append(empty_fitted_col)

            if overflowing_col:
                overflowing_columns.append(overflowing_col)
            else:
                empty_overflowing_col = deepcopy(column)
                empty_overflowing_col.children = []
                empty_overflowing_col.position = None
                empty_overflowing_col.size = None
                overflowing_columns.append(empty_overflowing_col)

        # Construct result rows
        fitted_row = None
        overflowing_row = None

        if fitted_columns:
            fitted_row = deepcopy(row_section)
            fitted_row.children = fitted_columns

        if overflowing_columns:
            overflowing_row = deepcopy(row_section)
            overflowing_row.children = overflowing_columns
            overflowing_row.position = None
            overflowing_row.size = None

        logger.debug(
            f"Rule B unanimous consent result: fitted={len(fitted_columns)} columns, "
            f"overflowing={len(overflowing_columns)} columns"
        )

        return fitted_row, overflowing_row

    def _has_actual_content(self, sections: list["Section"]) -> bool:
        """
        Check if a list of sections contains any actual elements.

        Per OVERFLOW_SPEC.md Rule #6.3: Empty continuation slides must not be created.
        This method recursively checks for any Element objects within the section hierarchy.

        Args:
            sections: List of sections to check

        Returns:
            True if any section contains at least one element, False otherwise
        """
        if not sections:
            logger.debug("_has_actual_content: No sections provided")
            return False

        for i, section in enumerate(sections):
            logger.debug(
                f"_has_actual_content: Checking section {i} ({section.id}) with {len(section.children)} children"
            )
            if not section.children:
                continue

            # Check for direct elements (children that are not sections)
            element_count = 0
            for child in section.children:
                if not hasattr(child, "children"):  # It's an element
                    element_count += 1
                    logger.debug(
                        f"_has_actual_content: Found element {child.element_type}"
                    )
                    return True

            logger.debug(
                f"_has_actual_content: Section {i} has {element_count} direct elements"
            )

            # Check nested sections recursively
            nested_sections = [
                child for child in section.children if hasattr(child, "children")
            ]
            if nested_sections:
                logger.debug(
                    f"_has_actual_content: Checking {len(nested_sections)} nested sections"
                )
                if self._has_actual_content(nested_sections):
                    return True

        logger.debug("_has_actual_content: No content found in any section")
        return False

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
