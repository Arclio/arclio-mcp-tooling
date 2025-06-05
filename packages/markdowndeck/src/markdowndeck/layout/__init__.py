"""Refactored layout management - Orchestrates the content-aware layout engine."""

import logging

from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.constants import (
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_SLIDE_HEIGHT,
    DEFAULT_SLIDE_WIDTH,
)
from markdowndeck.models import Slide

logger = logging.getLogger(__name__)


class LayoutManager:
    """
    Orchestrates the content-aware layout engine for slide positioning.

    The LayoutManager provides a high-level interface to the layout calculation
    system while maintaining the architectural separation between layout
    calculation and overflow handling.
    """

    def __init__(
        self,
        slide_width: float = None,
        slide_height: float = None,
        margins: dict = None,
    ):
        """
        Initialize the layout manager with slide dimensions and margins.

        Args:
            slide_width: Width of slides in points (defaults to Google Slides standard)
            slide_height: Height of slides in points (defaults to Google Slides standard)
            margins: Dictionary with margin values for top, right, bottom, left
        """
        # Use constants for defaults
        self.slide_width = slide_width or DEFAULT_SLIDE_WIDTH
        self.slide_height = slide_height or DEFAULT_SLIDE_HEIGHT

        self.margins = margins or {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

        # Calculate derived dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # Initialize the position calculator
        self.position_calculator = PositionCalculator(
            slide_width=self.slide_width,
            slide_height=self.slide_height,
            margins=self.margins,
        )

        logger.info(
            f"LayoutManager initialized: slide={self.slide_width}x{self.slide_height}, "
            f"content_area={self.max_content_width}x{self.max_content_height}"
        )

    def calculate_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions for all elements and sections in a slide.

        This is the main entry point for layout calculation. It delegates to
        the PositionCalculator which implements the Layout Calculation Contract.

        The returned slide will have all elements positioned according to their
        content needs. Elements may extend beyond their containers' boundaries
        (overflow), which is the expected and correct behavior for this component.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The slide with all elements and sections positioned
        """
        logger.debug(
            f"LayoutManager calculating positions for slide: {slide.object_id}"
        )

        # Validate input
        if not slide:
            logger.error("Cannot calculate positions for None slide")
            raise ValueError("Slide cannot be None")

        if not hasattr(slide, "elements"):
            logger.error("Slide missing elements attribute")
            raise ValueError("Slide must have elements attribute")

        # Delegate to position calculator
        try:
            positioned_slide = self.position_calculator.calculate_positions(slide)

            # Log summary of positioning results
            self._log_positioning_summary(positioned_slide)

            return positioned_slide

        except Exception as e:
            logger.error(
                f"Error calculating positions for slide {slide.object_id}: {e}"
            )
            raise

    def _log_positioning_summary(self, slide: Slide) -> None:
        """
        Log a summary of positioning results for debugging.

        Args:
            slide: The positioned slide to summarize
        """
        element_count = len(slide.elements)
        positioned_count = sum(
            1 for e in slide.elements if hasattr(e, "position") and e.position
        )
        sized_count = sum(1 for e in slide.elements if hasattr(e, "size") and e.size)

        section_count = (
            len(slide.sections) if hasattr(slide, "sections") and slide.sections else 0
        )
        positioned_sections = (
            sum(
                1
                for s in (slide.sections or [])
                if hasattr(s, "position") and s.position
            )
            if slide.sections
            else 0
        )

        logger.debug(
            f"Positioning summary for slide {slide.object_id}: "
            f"elements={element_count} (positioned={positioned_count}, sized={sized_count}), "
            f"sections={section_count} (positioned={positioned_sections})"
        )

        # Check for potential overflow situations (informational only)
        if slide.sections:
            self._check_section_overflow(slide.sections)

    def _check_section_overflow(self, sections: list) -> None:
        """
        Check and log potential element overflow within sections (informational only).

        This method does not modify anything - it only logs warnings about elements
        that extend beyond their section boundaries, which may be useful for debugging.

        Args:
            sections: List of sections to check
        """
        for section in sections:
            if not (
                hasattr(section, "position")
                and section.position
                and hasattr(section, "size")
                and section.size
            ):
                continue

            section_left, section_top = section.position
            section_width, section_height = section.size
            section_right = section_left + section_width
            section_bottom = section_top + section_height

            if hasattr(section, "elements") and section.elements:
                for element in section.elements:
                    if not (
                        hasattr(element, "position")
                        and element.position
                        and hasattr(element, "size")
                        and element.size
                    ):
                        continue

                    elem_left, elem_top = element.position
                    elem_width, elem_height = element.size
                    elem_right = elem_left + elem_width
                    elem_bottom = elem_top + elem_height

                    # Check for overflow (informational logging only)
                    if (
                        elem_left < section_left
                        or elem_right > section_right
                        or elem_top < section_top
                        or elem_bottom > section_bottom
                    ):
                        logger.debug(
                            f"Element {getattr(element, 'object_id', 'unknown')} extends beyond "
                            f"section {section.id} boundaries (this is expected for content overflow)"
                        )

            # Recursively check subsections
            if hasattr(section, "subsections") and section.subsections:
                self._check_section_overflow(section.subsections)

    def get_slide_dimensions(self) -> tuple[float, float]:
        """
        Get the configured slide dimensions.

        Returns:
            (width, height) tuple in points
        """
        return (self.slide_width, self.slide_height)

    def get_content_area(self) -> tuple[float, float, float, float]:
        """
        Get the content area dimensions accounting for margins.

        Returns:
            (left, top, width, height) tuple defining the content area
        """
        return (
            self.margins["left"],
            self.margins["top"],
            self.max_content_width,
            self.max_content_height,
        )

    def get_body_zone(self) -> tuple[float, float, float, float]:
        """
        Get the body zone area (excluding header and footer zones).

        Returns:
            (left, top, width, height) tuple defining the body zone
        """
        return self.position_calculator.get_body_zone_area()

    def validate_slide_structure(self, slide: Slide) -> list[str]:
        """
        Validate slide structure and return any warnings.

        This performs basic structural validation to help identify potential
        issues before layout calculation.

        Args:
            slide: The slide to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        if not slide.elements:
            warnings.append("Slide has no elements")

        # Check for elements without required attributes
        for i, element in enumerate(slide.elements):
            if not hasattr(element, "element_type"):
                warnings.append(f"Element {i} missing element_type")

            if hasattr(element, "element_type") and element.element_type:
                # Type-specific validation
                if element.element_type.name in ("TEXT", "TITLE", "SUBTITLE", "QUOTE"):
                    if not hasattr(element, "text") or not element.text:
                        warnings.append(f"Text element {i} has no content")

                elif element.element_type.name in ("BULLET_LIST", "ORDERED_LIST"):
                    if not hasattr(element, "items") or not element.items:
                        warnings.append(f"List element {i} has no items")

                elif element.element_type.name == "TABLE":
                    if not hasattr(element, "rows") or not element.rows:
                        warnings.append(f"Table element {i} has no rows")

                elif element.element_type.name == "IMAGE" and (
                    not hasattr(element, "url") or not element.url
                ):
                    warnings.append(f"Image element {i} has no URL")

        # Check section structure if present
        if hasattr(slide, "sections") and slide.sections:
            section_warnings = self._validate_section_structure(slide.sections)
            warnings.extend(section_warnings)

        return warnings

    def _validate_section_structure(self, sections: list, level: int = 0) -> list[str]:
        """
        Validate section structure recursively.

        Args:
            sections: List of sections to validate
            level: Current nesting level

        Returns:
            List of warning messages
        """
        warnings = []

        for section in sections:
            if not hasattr(section, "id") or not section.id:
                warnings.append(f"Section at level {level} missing ID")

            # Check for both elements and subsections (unusual but not invalid)
            has_elements = hasattr(section, "elements") and section.elements
            has_subsections = hasattr(section, "subsections") and section.subsections

            if has_elements and has_subsections:
                warnings.append(
                    f"Section {getattr(section, 'id', 'unknown')} has both elements and subsections"
                )

            if not has_elements and not has_subsections:
                warnings.append(f"Section {getattr(section, 'id', 'unknown')} is empty")

            # Recursively validate subsections
            if has_subsections:
                subsection_warnings = self._validate_section_structure(
                    section.subsections, level + 1
                )
                warnings.extend(subsection_warnings)

        return warnings
