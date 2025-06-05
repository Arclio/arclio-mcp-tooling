"""Overflow detection utility for identifying overflowing sections."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class OverflowDetector:
    """
    Simple utility class to detect the first overflowing section in a slide.

    This detector identifies sections whose content extends beyond the slide's
    vertical boundaries by comparing section positions and sizes against the
    available body height.
    """

    def __init__(self, body_height: float):
        """
        Initialize the overflow detector.

        Args:
            body_height: The available height in the slide's body zone
        """
        self.body_height = body_height
        logger.debug(f"OverflowDetector initialized with body_height={body_height}")

    def find_first_overflowing_section(self, slide: "Slide") -> "Section | None":
        """
        Find the first section that overflows the slide's body height.

        This method iterates through the top-level sections in the slide and
        identifies the first one whose bottom edge extends beyond the body height.

        Args:
            slide: The slide to analyze for overflow

        Returns:
            The first overflowing Section, or None if no overflow is detected
        """
        if not slide.sections:
            logger.debug("No sections in slide - no overflow possible")
            return None

        logger.debug(f"Checking {len(slide.sections)} top-level sections for overflow")

        for i, section in enumerate(slide.sections):
            if not section.position or not section.size:
                logger.warning(
                    f"Section {i} missing position or size - skipping overflow check"
                )
                continue

            section_top = section.position[1]
            section_height = section.size[1]
            section_bottom = section_top + section_height

            logger.debug(
                f"Section {i}: top={section_top}, height={section_height}, bottom={section_bottom}"
            )

            if section_bottom > self.body_height:
                logger.info(
                    f"Found overflowing section {i}: bottom={section_bottom} > body_height={self.body_height}"
                )
                return section

        logger.debug("No overflowing sections found")
        return None
