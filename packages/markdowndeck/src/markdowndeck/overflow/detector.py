"""Overflow detection utility with strict jurisdictional boundaries."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class OverflowDetector:
    """
    Overflow detector that enforces strict jurisdictional boundaries.

    Per the specification: The Overflow Handler's logic is triggered ONLY when a section's
    external bounding box overflows the slide's available height. It MUST IGNORE internal
    content overflow within a section whose bounding box fits on the slide.
    """

    def __init__(self, body_height: float, top_margin: float = None):
        """
        Initialize the overflow detector.

        Args:
            body_height: The available height in the slide's body zone
            top_margin: The actual top margin used by the slide configuration.
                       If None, defaults to DEFAULT_MARGIN_TOP for backward compatibility.
        """
        self.body_height = body_height

        # Calculate the actual Y coordinate where content area ends
        from markdowndeck.layout.constants import (
            DEFAULT_MARGIN_TOP,
            HEADER_HEIGHT,
            HEADER_TO_BODY_SPACING,
        )

        # FIXED: Use actual top margin instead of hardcoded default
        actual_top_margin = top_margin if top_margin is not None else DEFAULT_MARGIN_TOP
        self.body_start_y = actual_top_margin + HEADER_HEIGHT + HEADER_TO_BODY_SPACING
        self.body_end_y = self.body_start_y + body_height

        logger.debug(
            f"OverflowDetector initialized with body_height={body_height}, "
            f"top_margin={actual_top_margin}, body_start_y={self.body_start_y}, body_end_y={self.body_end_y}"
        )

    def find_first_overflowing_section(self, slide: "Slide") -> "Section | None":
        """
        Find the first section whose EXTERNAL BOUNDING BOX overflows the slide's body height.

        This method strictly enforces the jurisdictional boundary: it only considers
        external section overflow, completely ignoring any internal content overflow
        within sections that have user-defined, fixed sizes.

        Args:
            slide: The slide to analyze for overflow

        Returns:
            The first externally overflowing Section, or None if no external overflow
        """
        if not slide.sections:
            logger.debug("No sections in slide - no overflow possible")
            return None

        logger.debug(
            f"Checking {len(slide.sections)} top-level sections for EXTERNAL overflow"
        )

        for i, section in enumerate(slide.sections):
            if not section.position or not section.size:
                logger.warning(
                    f"Section {i} missing position or size - skipping overflow check"
                )
                continue

            # Calculate section's external bounding box
            section_top = section.position[1]
            section_height = section.size[1]
            section_bottom = section_top + section_height

            logger.debug(
                f"Section {i}: external_top={section_top}, height={section_height}, "
                f"external_bottom={section_bottom}, body_end_y={self.body_end_y}"
            )

            # Check if section's EXTERNAL bounding box overflows
            if section_bottom > self.body_end_y:
                # Before declaring overflow, check if this is acceptable
                if self._is_overflow_acceptable(section):
                    logger.info(
                        f"Section {i} external overflow is ACCEPTABLE - skipping"
                    )
                    continue

                logger.info(
                    f"Found EXTERNAL overflowing section {i}: bottom={section_bottom} > body_end_y={self.body_end_y}"
                )
                return section

        logger.debug("No externally overflowing sections found")
        return None

    def _is_overflow_acceptable(self, section: "Section") -> bool:
        """
        Check if an externally overflowing section is in an acceptable state.

        Per the specification, overflow is acceptable if:
        1. The section has an explicit height directive (user-intended fixed size)
        2. The section contains only a single, unsplittable element causing the overflow

        Args:
            section: The section to check

        Returns:
            True if overflow is acceptable, False if it needs handling
        """
        # Rule 1: Section has an explicit height directive
        if section.directives and section.directives.get("height"):
            logger.debug(
                f"Section {section.id} overflow is acceptable: explicit [height] directive"
            )
            return True

        # Rule 2: Single unsplittable element causing overflow
        section_elements = [c for c in section.children if not hasattr(c, "children")]
        if section_elements and len(section_elements) == 1:
            element = section_elements[0]
            # Check if element is unsplittable by testing its split method
            if hasattr(element, "split") and callable(element.split):
                # For images, they're pre-scaled so should never cause external overflow
                # For other elements, we'd need to test splittability
                from markdowndeck.models import ElementType

                if element.element_type == ElementType.IMAGE:
                    logger.debug(
                        f"Section {section.id} overflow is acceptable: single pre-scaled image"
                    )
                    return True

                # For other single elements, we could test their split behavior
                # but this is a complex check that might be better handled by the handler

        return False

    def has_any_overflow(self, slide: "Slide") -> bool:
        """
        Quick check if the slide has any external overflow.

        Args:
            slide: The slide to check

        Returns:
            True if any external overflow exists, False otherwise
        """
        return self.find_first_overflowing_section(slide) is not None

    def get_overflow_summary(self, slide: "Slide") -> dict:
        """
        Get a summary of overflow conditions for debugging.

        Args:
            slide: The slide to analyze

        Returns:
            Dictionary with overflow analysis details
        """
        summary = {
            "has_overflow": False,
            "overflowing_section_index": None,
            "total_sections": len(slide.sections) if slide.sections else 0,
            "body_height": self.body_height,
            "sections_analysis": [],
        }

        if not slide.sections:
            return summary

        for i, section in enumerate(slide.sections):
            section_info = {
                "index": i,
                "id": section.id,
                "has_position": section.position is not None,
                "has_size": section.size is not None,
                "overflows": False,
                "is_acceptable": False,
            }

            if section.position and section.size:
                section_bottom = section.position[1] + section.size[1]
                section_info["bottom"] = section_bottom
                section_info["overflows"] = section_bottom > self.body_end_y

                if section_info["overflows"]:
                    section_info["is_acceptable"] = self._is_overflow_acceptable(
                        section
                    )

                    if (
                        not section_info["is_acceptable"]
                        and not summary["has_overflow"]
                    ):
                        summary["has_overflow"] = True
                        summary["overflowing_section_index"] = i

            summary["sections_analysis"].append(section_info)

        return summary
