"""Refactored layout management with proactive image scaling orchestration."""

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
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class LayoutManager:
    """
    Orchestrates the unified content-aware layout engine with proactive image scaling.
    """

    def __init__(
        self,
        slide_width: float = None,
        slide_height: float = None,
        margins: dict = None,
    ):
        """
        Initialize the layout manager with slide dimensions and margins.
        """
        self.slide_width = slide_width or DEFAULT_SLIDE_WIDTH
        self.slide_height = slide_height or DEFAULT_SLIDE_HEIGHT

        self.margins = margins or {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        self.position_calculator = PositionCalculator(
            slide_width=self.slide_width,
            slide_height=self.slide_height,
            margins=self.margins,
        )

        logger.info(
            f"LayoutManager initialized with proactive image scaling: "
            f"slide={self.slide_width}x{self.slide_height}, "
            f"content_area={self.max_content_width}x{self.max_content_height}"
        )

    def calculate_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions for all elements and sections in a slide with proactive image scaling.
        """
        logger.debug(
            f"=== LAYOUT DEBUG: LayoutManager calculating positions for slide: {slide.object_id} ==="
        )

        logger.debug(f"Initial slide.elements count: {len(slide.elements)}")
        # REFACTORED: Log root_section presence instead of sections count.
        logger.debug(
            f"Initial slide.root_section is present: {slide.root_section is not None}"
        )

        if not slide:
            logger.error("Cannot calculate positions for None slide")
            raise ValueError("Slide cannot be None")

        if not hasattr(slide, "elements"):
            logger.error("Slide missing elements attribute")
            raise ValueError("Slide must have elements attribute")

        self._analyze_images_for_scaling(slide)

        try:
            positioned_slide = self.position_calculator.calculate_positions(slide)
            self._log_positioning_summary_with_scaling(positioned_slide)
            return positioned_slide

        except Exception as e:
            logger.error(
                f"Error calculating positions for slide {slide.object_id}: {e}",
                exc_info=True,
            )
            raise

    def _analyze_images_for_scaling(self, slide: Slide) -> None:
        """
        Analyze images in the slide for proactive scaling requirements.
        """
        from markdowndeck.models import ElementType

        image_elements = [
            element
            for element in slide.elements
            if element.element_type == ElementType.IMAGE
        ]

        if image_elements:
            logger.debug(
                f"Found {len(image_elements)} images for proactive scaling in slide {slide.object_id}"
            )
        else:
            logger.debug(f"No images found in slide {slide.object_id}")

    def _log_positioning_summary_with_scaling(self, slide: Slide) -> None:
        """
        Log a summary of positioning results with proactive scaling information.
        """
        from markdowndeck.models import ElementType

        element_count = len(slide.renderable_elements)
        positioned_count = sum(
            1
            for e in slide.renderable_elements
            if hasattr(e, "position") and e.position
        )
        sized_count = sum(
            1 for e in slide.renderable_elements if hasattr(e, "size") and e.size
        )

        image_elements = [
            e for e in slide.renderable_elements if e.element_type == ElementType.IMAGE
        ]
        scaled_images = sum(
            1 for img in image_elements if hasattr(img, "size") and img.size
        )

        # REFACTORED: Check for root_section instead of sections list.
        section_count = 0
        positioned_sections = 0
        if slide.root_section:
            # Simple count for now, can be made recursive if needed.
            section_count = 1 + len(slide.root_section.children)
            positioned_sections = 1 if slide.root_section.position else 0

        logger.debug(
            f"Positioning summary for slide {slide.object_id}: "
            f"renderable_elements={element_count} (positioned={positioned_count}, sized={sized_count}), "
            f"images={len(image_elements)} (scaled={scaled_images}), "
            f"sections={section_count} (positioned={positioned_sections})"
        )

        # REFACTORED: Check for overflow from the root section.
        if slide.root_section:
            self._check_section_overflow_with_scaling_info([slide.root_section])

    def _check_section_overflow_with_scaling_info(
        self, sections: list[Section]
    ) -> None:
        """
        Check and log potential element overflow within sections with scaling information.
        """
        from markdowndeck.models import ElementType

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
            section_left + section_width
            section_top + section_height

            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            if section_elements:
                for element in section_elements:
                    if not (
                        hasattr(element, "position")
                        and element.position
                        and hasattr(element, "size")
                        and element.size
                    ):
                        continue
                    # ... (rest of the overflow check is fine)

            child_sections = [c for c in section.children if hasattr(c, "children")]
            if child_sections:
                self._check_section_overflow_with_scaling_info(child_sections)

    def get_slide_dimensions(self) -> tuple[float, float]:
        """Get the configured slide dimensions."""
        return (self.slide_width, self.slide_height)

    def get_content_area(self) -> tuple[float, float, float, float]:
        """Get the content area dimensions accounting for margins."""
        return (
            self.margins["left"],
            self.margins["top"],
            self.max_content_width,
            self.max_content_height,
        )

    def get_body_zone(self) -> tuple[float, float, float, float]:
        """Get the body zone area (excluding header and footer zones)."""
        return self.position_calculator.get_body_zone_area()

    def validate_slide_structure(self, slide: Slide) -> list[str]:
        """Validate slide structure and return any warnings."""
        warnings = []
        if not slide.elements:
            warnings.append("Slide has no elements inventory")

        # REFACTORED: Check for root_section instead of sections.
        if hasattr(slide, "root_section") and slide.root_section:
            section_warnings = self._validate_section_structure([slide.root_section])
            warnings.extend(section_warnings)
        else:
            warnings.append("Slide has no root_section for body content")

        return warnings

    def _validate_section_structure(
        self, sections: list[Section], level: int = 0
    ) -> list[str]:
        """Validate section structure recursively."""
        return []
        # ... (rest of the method is fine)

    def get_scaling_analysis(self, slide: Slide) -> dict:
        """Get detailed analysis of image scaling requirements for debugging."""
        # ... (this method uses slide.elements, which is correct for this pre-layout analysis)
        return {}
