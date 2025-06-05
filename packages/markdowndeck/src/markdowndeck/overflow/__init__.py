"""
Overflow handling for MarkdownDeck slides.

This package provides intelligent overflow detection and handling for slides
where content exceeds slide boundaries. It operates independently of the
layout calculator, taking positioned slides as input and producing optimally
distributed content across multiple slides.

Architecture:
- OverflowManager: Main orchestrator with pluggable strategies
- OverflowDetector: Analyzes positioned slides for overflow conditions
- OverflowHandlers: Implements different distribution strategies
- SlideBuilder: Creates continuation slides with proper formatting

Usage:
    from markdowndeck.overflow import OverflowManager

    # Create overflow manager
    overflow_manager = OverflowManager()

    # Process positioned slide from layout calculator
    positioned_slide = layout_manager.calculate_positions(slide)
    final_slides = overflow_manager.process_slide(positioned_slide)
"""

import logging

from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler
from markdowndeck.overflow.manager import OverflowManager
from markdowndeck.overflow.models import OverflowStrategy, OverflowType
from markdowndeck.overflow.slide_builder import SlideBuilder

logger = logging.getLogger(__name__)

# Public API exports
__all__ = [
    "OverflowManager",
    "OverflowStrategy",
    "OverflowType",
    "OverflowDetector",
    "StandardOverflowHandler",
    "SlideBuilder",
    "create_overflow_manager",
    "process_positioned_slide",
]


def create_overflow_manager(
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
    strategy: OverflowStrategy = OverflowStrategy.STANDARD,
) -> OverflowManager:
    """
    Create a configured overflow manager.

    Args:
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins (top, right, bottom, left)
        strategy: Overflow handling strategy

    Returns:
        Configured OverflowManager instance

    Example:
        >>> manager = create_overflow_manager()
        >>> slides = manager.process_slide(positioned_slide)
    """
    return OverflowManager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
        strategy=strategy,
    )


def process_positioned_slide(
    positioned_slide,
    slide_width: float = 720,
    slide_height: float = 405,
    margins: dict[str, float] = None,
    strategy: OverflowStrategy = OverflowStrategy.STANDARD,
) -> list:
    """
    Convenience function to process a single positioned slide.

    Args:
        positioned_slide: Slide with positioned elements from layout calculator
        slide_width: Width of slides in points
        slide_height: Height of slides in points
        margins: Slide margins
        strategy: Overflow handling strategy

    Returns:
        List of slides with content properly distributed

    Example:
        >>> from markdowndeck.layout import LayoutManager
        >>> from markdowndeck.overflow import process_positioned_slide
        >>>
        >>> layout_manager = LayoutManager()
        >>> positioned_slide = layout_manager.calculate_positions(slide)
        >>> final_slides = process_positioned_slide(positioned_slide)
    """
    manager = create_overflow_manager(
        slide_width=slide_width,
        slide_height=slide_height,
        margins=margins,
        strategy=strategy,
    )

    return manager.process_slide(positioned_slide)


# Configuration defaults
DEFAULT_SLIDE_WIDTH = 720
DEFAULT_SLIDE_HEIGHT = 405
DEFAULT_MARGINS = {"top": 50, "right": 50, "bottom": 50, "left": 50}

logger.debug("MarkdownDeck overflow package initialized")
