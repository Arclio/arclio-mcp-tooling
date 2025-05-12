"""Layout management for slides and elements."""

import logging

from markdowndeck.layout.calculator.base import PositionCalculator
from markdowndeck.layout.overflow import OverflowHandler
from markdowndeck.models import Slide

logger = logging.getLogger(__name__)


class LayoutManager:
    """Manages the layout of slides and elements with zone-based positioning."""

    def __init__(self):
        """Initialize the layout manager with standard slide dimensions."""
        # Default margins
        self.margins = {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Default slide dimensions (in points - Google Slides standard)
        self.slide_width = 720  # 10 inches at 72 points per inch
        self.slide_height = 405  # 5.625 inches at 72 points per inch (16:9 aspect ratio)

        # Maximum content dimensions
        self.max_content_width = self.slide_width - self.margins["left"] - self.margins["right"]
        self.max_content_height = self.slide_height - self.margins["top"] - self.margins["bottom"]

        # Initialize component classes
        self.position_calculator = PositionCalculator(
            slide_width=self.slide_width,
            slide_height=self.slide_height,
            margins=self.margins,
        )

        self.overflow_handler = OverflowHandler(
            slide_width=self.slide_width,
            slide_height=self.slide_height,
            margins=self.margins,
        )

    def calculate_positions(self, slide: Slide) -> Slide | list[Slide]:
        """
        Calculate positions for elements in a slide and handle overflow if needed.

        Args:
            slide: The slide to calculate positions for

        Returns:
            Either the slide with updated positions or a list of slides if overflow occurred
        """
        logger.debug(f"Calculating positions for slide: {slide.object_id}")

        # Step 1: Calculate positions for elements using zone-based layout
        updated_slide = self.position_calculator.calculate_positions(slide)

        # Step 2: Check for overflow
        if self.overflow_handler.has_overflow(updated_slide):
            logger.debug(f"Overflow detected for slide: {updated_slide.object_id}")
            # Create continuation slides for overflow
            slides = self.overflow_handler.handle_overflow(updated_slide)
            logger.debug(f"Created {len(slides)} slides after handling overflow")
            return slides

        logger.debug(f"Position calculation completed for slide: {updated_slide.object_id}")
        return updated_slide
