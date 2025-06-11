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

    # REFACTORED: Removed static height calculation from __init__.
    # JUSTIFICATION: Body height is dynamic and depends on the presence of meta-elements on each slide.
    def __init__(self, slide_height: float, top_margin: float):
        """
        Initialize the overflow detector.

        Args:
            slide_height: The total height of the slide canvas.
            top_margin: The slide's top margin.
        """
        self.slide_height = slide_height
        self.top_margin = top_margin
        logger.debug(
            f"OverflowDetector initialized. Slide height: {self.slide_height}, Top margin: {self.top_margin}"
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

        # FIXED: Dynamically calculate body_end_y for this specific slide.
        body_start_y, body_end_y = self._calculate_body_boundaries(slide)
        logger.debug(
            f"Checking {len(slide.sections)} top-level sections for EXTERNAL overflow against body_end_y={body_end_y}"
        )

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
                f"Section {i}: external_top={section_top}, height={section_height}, "
                f"external_bottom={section_bottom}, body_end_y={body_end_y}"
            )

            if section_bottom > body_end_y:
                if self._is_overflow_acceptable(section):
                    logger.info(
                        f"Section {i} external overflow is ACCEPTABLE - skipping"
                    )
                    continue

                logger.info(
                    f"Found EXTERNAL overflowing section {i}: bottom={section_bottom} > body_end_y={body_end_y}"
                )
                return section

        logger.debug("No externally overflowing sections found")
        return None

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

    def _is_overflow_acceptable(self, section: "Section") -> bool:
        """
        Check if an externally overflowing section is in an acceptable state.
        """
        if section.directives and section.directives.get("height"):
            logger.debug(
                f"Section {section.id} overflow is acceptable: explicit [height] directive"
            )
            return True
        return False
