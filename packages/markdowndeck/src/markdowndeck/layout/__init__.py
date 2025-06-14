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
        Calculate positions for all elements and sections in a slide.

        This method is the single entry point for layout calculations and serves
        as the orchestrator for all spatial planning, including proactive image
        validation and scaling as required by LAYOUT_SPEC.md Rules #4 and #8.
        """
        logger.debug(
            f"--- LayoutManager: calculating positions for slide '{slide.object_id}' ---"
        )

        if not slide:
            logger.error("Cannot calculate positions for a None slide object.")
            raise ValueError("Slide cannot be None.")

        if not hasattr(slide, "elements"):
            logger.error("Slide object is malformed: missing 'elements' attribute.")
            raise ValueError("Slide must have an 'elements' attribute.")

        # The call to position_calculator.calculate_positions will trigger the
        # full recursive layout, including proactive image URL validation and scaling
        # deep within the metrics calculation, fulfilling LAYOUT_SPEC.md Rule #8.
        try:
            positioned_slide = self.position_calculator.calculate_positions(slide)
            self._log_positioning_summary(positioned_slide)
            return positioned_slide
        except Exception as e:
            logger.error(
                f"Fatal error during position calculation for slide {slide.object_id}: {e}",
                exc_info=True,
            )
            raise

    def _log_positioning_summary(self, slide: Slide) -> None:
        """
        Log a summary of positioning results.
        """
        element_count = len(slide.renderable_elements)
        positioned_count = sum(
            1
            for e in slide.renderable_elements
            if hasattr(e, "position") and e.position is not None
        )
        sized_count = sum(
            1
            for e in slide.renderable_elements
            if hasattr(e, "size") and e.size is not None
        )

        logger.debug(
            f"Positioning summary for slide {slide.object_id}: "
            f"{element_count} renderable elements generated. "
            f"Positioned: {positioned_count}/{element_count}, Sized: {sized_count}/{element_count}."
        )

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
