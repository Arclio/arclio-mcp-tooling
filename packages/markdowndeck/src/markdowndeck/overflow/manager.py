"""Overflow management for handling content that exceeds slide boundaries."""

import logging
from typing import Protocol

from markdowndeck.models import Slide
from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler
from markdowndeck.overflow.models import OverflowStrategy

logger = logging.getLogger(__name__)


class OverflowHandler(Protocol):
    """Protocol for overflow handling strategies."""

    def handle_overflow(self, slide: Slide, overflow_info: dict) -> list[Slide]:
        """Handle overflow for a slide with detected overflow."""
        ...


class OverflowManager:
    """
    Main orchestrator for overflow detection and handling.

    Takes positioned slides from the layout calculator and intelligently
    distributes content across multiple slides when overflow is detected.

    Architecture:
    - OverflowDetector: Identifies overflow conditions
    - OverflowHandler: Applies overflow resolution strategies
    - Clean separation of detection from handling logic
    - Extensible strategy pattern for different overflow approaches
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
        strategy: OverflowStrategy = OverflowStrategy.STANDARD,
    ):
        """
        Initialize the overflow manager.

        Args:
            slide_width: Width of slides in points
            slide_height: Height of slides in points
            margins: Slide margins (top, right, bottom, left)
            strategy: Overflow handling strategy to use
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Initialize components
        self.detector = OverflowDetector(slide_width=slide_width, slide_height=slide_height, margins=self.margins)

        # Strategy pattern for different overflow handling approaches
        self.handlers = {
            OverflowStrategy.STANDARD: StandardOverflowHandler(
                slide_width=slide_width, slide_height=slide_height, margins=self.margins
            ),
            # Future strategies can be added here:
            # OverflowStrategy.AGGRESSIVE: AggressiveOverflowHandler(...),
            # OverflowStrategy.CONSERVATIVE: ConservativeOverflowHandler(...),
        }

        self.current_strategy = strategy
        logger.debug(f"OverflowManager initialized with strategy: {strategy}")

    def process_slide(self, positioned_slide: Slide) -> list[Slide]:
        """
        Process a positioned slide and handle any overflow.

        Args:
            positioned_slide: Slide with all elements positioned by layout calculator

        Returns:
            List of slides (original slide if no overflow, or multiple slides if overflow handled)
        """
        logger.debug(f"Processing slide {positioned_slide.object_id} for overflow")

        # Step 1: Detect overflow
        overflow_info = self.detector.detect_overflow(positioned_slide)

        if not overflow_info["has_overflow"]:
            logger.debug(f"No overflow detected in slide {positioned_slide.object_id}")
            return [positioned_slide]

        logger.info(f"Overflow detected in slide {positioned_slide.object_id}: {overflow_info['summary']}")

        # Step 2: Handle overflow using selected strategy
        handler = self.handlers[self.current_strategy]
        result_slides = handler.handle_overflow(positioned_slide, overflow_info)

        logger.info(f"Overflow handling complete: {len(result_slides)} slides created")
        return result_slides

    def set_strategy(self, strategy: OverflowStrategy) -> None:
        """
        Change the overflow handling strategy.

        Args:
            strategy: New strategy to use
        """
        if strategy not in self.handlers:
            raise ValueError(f"Unsupported overflow strategy: {strategy}")

        self.current_strategy = strategy
        logger.debug(f"Overflow strategy changed to: {strategy}")

    def add_custom_handler(self, strategy: OverflowStrategy, handler: OverflowHandler) -> None:
        """
        Add a custom overflow handling strategy.

        Args:
            strategy: Strategy identifier
            handler: Handler implementation
        """
        self.handlers[strategy] = handler
        logger.debug(f"Custom overflow handler registered for strategy: {strategy}")

    def get_overflow_summary(self, positioned_slide: Slide) -> dict:
        """
        Get overflow analysis without handling it.

        Args:
            positioned_slide: Slide to analyze

        Returns:
            Dictionary with overflow analysis details
        """
        return self.detector.detect_overflow(positioned_slide)
