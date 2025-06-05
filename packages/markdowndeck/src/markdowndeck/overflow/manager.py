"""Overflow management for handling content that exceeds slide boundaries."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide

from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler

logger = logging.getLogger(__name__)


class OverflowManager:
    """
    Main orchestrator for overflow detection and handling.

    Takes positioned slides from the layout calculator and intelligently
    distributes content across multiple slides when overflow is detected.

    Architecture:
    - OverflowDetector: Identifies overflow conditions
    - OverflowHandler: Applies overflow resolution strategies
    - Clean separation of detection from handling logic
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
    ):
        """
        Initialize the overflow manager.

        Args:
            slide_width: Width of slides in points
            slide_height: Height of slides in points
            margins: Slide margins (top, right, bottom, left)
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Calculate body height (available space for content)
        # Assuming header height of 90 and footer height of 30
        header_height = 90.0
        footer_height = 30.0
        self.body_height = (
            slide_height
            - self.margins["top"]
            - self.margins["bottom"]
            - header_height
            - footer_height
        )

        # Initialize components
        self.detector = OverflowDetector(body_height=self.body_height)
        self.handler = StandardOverflowHandler(body_height=self.body_height)

        logger.debug(
            f"OverflowManager initialized with body_height={self.body_height}, "
            f"slide_dimensions={slide_width}x{slide_height}, margins={self.margins}"
        )

    def process_slide(self, slide: "Slide") -> list["Slide"]:
        """
        Process a positioned slide and handle any overflow using the main algorithm.

        Args:
            positioned_slide: Slide with all elements positioned by layout calculator

        Returns:
            List of slides (original slide if no overflow, or multiple slides if overflow handled)
        """
        logger.debug(f"Processing slide {slide.object_id} for overflow")

        # Main Algorithm Implementation
        final_slides = []
        slides_to_process = [slide]

        while slides_to_process:
            # Dequeue current slide
            current_slide = slides_to_process.pop(0)

            logger.debug(f"Processing slide {current_slide.object_id} from queue")

            # Step 1: Detect overflow
            overflowing_section = self.detector.find_first_overflowing_section(
                current_slide
            )

            if overflowing_section is None:
                # No overflow - add to final slides
                final_slides.append(current_slide)
                logger.debug(f"No overflow detected in slide {current_slide.object_id}")
                continue

            # Step 2: Handle overflow
            logger.info(f"Overflow detected in slide {current_slide.object_id}")

            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_section
            )

            # Step 3: Add fitted slide to final results
            final_slides.append(fitted_slide)
            logger.debug(
                f"Added fitted slide {fitted_slide.object_id} to final results"
            )

            # Step 4: Enqueue continuation slide for further processing
            slides_to_process.append(continuation_slide)
            logger.debug(
                f"Enqueued continuation slide {continuation_slide.object_id} for processing"
            )

        logger.info(
            f"Overflow processing complete: {len(final_slides)} slides created from 1 input slide"
        )
        return final_slides
