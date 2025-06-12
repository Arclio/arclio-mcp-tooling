import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide
    from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class OverflowDetector:
    """
    Overflow detector that enforces strict jurisdictional boundaries.
    """

    def __init__(self, slide_height: float, top_margin: float):
        self.slide_height = slide_height
        self.top_margin = top_margin
        logger.debug(
            f"OverflowDetector initialized. Slide height: {self.slide_height}, Top margin: {self.top_margin}"
        )

    def find_first_overflowing_section(self, slide: "Slide") -> "Section | None":
        """
        Finds if the root section's EXTERNAL BOUNDING BOX overflows the slide's body height.
        REFACTORED: To check only the single slide.root_section per the new architecture.
        """
        # REFACTORED: Check for root_section, not a list of sections.
        if not slide.root_section:
            logger.debug("No root_section in slide - no overflow possible")
            return None

        body_start_y, body_end_y = self._calculate_body_boundaries(slide)
        logger.debug(
            f"Checking root_section for EXTERNAL overflow against body_end_y={body_end_y}"
        )

        section = slide.root_section
        if not section.position or not section.size:
            logger.warning(
                f"Root section {section.id} missing position or size - skipping overflow check"
            )
            return None

        section_top = section.position[1]
        section_height = section.size[1]
        section_bottom = section_top + section_height

        logger.debug(
            f"Root section: external_top={section_top}, height={section_height}, "
            f"external_bottom={section_bottom}, body_end_y={body_end_y}"
        )

        if section_bottom > body_end_y:
            if self._is_overflow_acceptable(section):
                logger.info(
                    f"Root section {section.id} external overflow is ACCEPTABLE - skipping"
                )
                return None

            logger.info(
                f"Found EXTERNAL overflowing root_section {section.id}: bottom={section_bottom} > body_end_y={body_end_y}"
            )
            return section

        logger.debug("No externally overflowing section found")
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
            title_bottom = title.position[1] + title.size[1]
            top_offset = title_bottom + HEADER_TO_BODY_SPACING

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
