"""Overflow management with strict jurisdictional boundaries."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide

from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler

logger = logging.getLogger(__name__)

# Constants for preventing infinite recursion
MAX_OVERFLOW_ITERATIONS = 50  # Maximum number of overflow processing iterations
MAX_CONTINUATION_SLIDES = 25  # Maximum number of continuation slides per original slide


class OverflowManager:
    """
    Main orchestrator for overflow detection and handling with strict jurisdictional boundaries.

    Per the specification: The Overflow Handler's logic is triggered ONLY when a section's
    external bounding box overflows the slide's available height. It MUST IGNORE internal
    content overflow within sections that have user-defined, fixed sizes.

    Architecture:
    - OverflowDetector: Identifies external section overflow only
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
        # Using constants from specification
        header_height = 90.0
        footer_height = 30.0
        header_to_body_spacing = 10.0
        body_to_footer_spacing = 10.0

        self.body_height = (
            slide_height
            - self.margins["top"]
            - self.margins["bottom"]
            - header_height
            - footer_height
            - header_to_body_spacing
            - body_to_footer_spacing
        )

        # Initialize components
        self.detector = OverflowDetector(body_height=self.body_height)
        self.handler = StandardOverflowHandler(body_height=self.body_height)

        # Layout manager for repositioning continuation slides
        from markdowndeck.layout import LayoutManager

        self.layout_manager = LayoutManager(slide_width, slide_height, margins)

        logger.debug(
            f"OverflowManager initialized with body_height={self.body_height}, "
            f"slide_dimensions={slide_width}x{slide_height}, margins={self.margins}"
        )

    def process_slide(self, slide: "Slide") -> list["Slide"]:
        """
        Process a positioned slide and handle any external overflow using the main algorithm.

        This method strictly enforces the jurisdictional boundary: it only processes
        external section overflow and ignores internal content overflow within sections
        that have user-defined sizes.

        Args:
            slide: Slide with all elements positioned by layout calculator

        Returns:
            List of slides (original slide if no overflow, or multiple slides if overflow handled)
        """
        logger.debug(f"Processing slide {slide.object_id} for EXTERNAL overflow only")

        # Main Algorithm Implementation with Strict Jurisdictional Boundaries
        final_slides = []
        slides_to_process = [slide]

        # Add safeguards against infinite recursion
        iteration_count = 0
        original_slide_id = slide.object_id

        while slides_to_process:
            # Check for infinite recursion protection
            iteration_count += 1
            if iteration_count > MAX_OVERFLOW_ITERATIONS:
                logger.error(
                    f"Maximum overflow iterations ({MAX_OVERFLOW_ITERATIONS}) exceeded for slide {original_slide_id}"
                )
                # Force-add remaining slides to prevent infinite loop
                final_slides.extend(slides_to_process)
                break

            if len(final_slides) > MAX_CONTINUATION_SLIDES:
                logger.error(
                    f"Maximum continuation slides ({MAX_CONTINUATION_SLIDES}) exceeded for slide {original_slide_id}"
                )
                # Force-add remaining slides to prevent infinite slides
                final_slides.extend(slides_to_process)
                break

            # Dequeue current slide
            current_slide = slides_to_process.pop(0)

            logger.debug(
                f"Processing slide {current_slide.object_id} from queue (iteration {iteration_count})"
            )

            # Step 1: Detect EXTERNAL overflow only
            overflowing_section = self.detector.find_first_overflowing_section(
                current_slide
            )

            if overflowing_section is None:
                # No external overflow - add to final slides
                final_slides.append(current_slide)
                logger.debug(
                    f"No EXTERNAL overflow detected in slide {current_slide.object_id}"
                )
                continue

            # Step 2: Handle external overflow
            logger.info(
                f"EXTERNAL overflow detected in slide {current_slide.object_id}, proceeding with handler."
            )

            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_section
            )

            # Step 3: Add fitted slide to final results
            final_slides.append(fitted_slide)
            logger.debug(
                f"Added fitted slide {fitted_slide.object_id} to final results"
            )

            # Step 4: Enqueue continuation slide for further processing
            # Note: Continuation slides already have correct positioning from slide builder
            slides_to_process.append(continuation_slide)
            logger.debug(
                f"Enqueued continuation slide {continuation_slide.object_id} for processing"
            )

        logger.info(
            f"Overflow processing complete: {len(final_slides)} slides created from 1 input slide"
        )
        return final_slides

    def get_overflow_analysis(self, slide: "Slide") -> dict:
        """
        Get detailed overflow analysis for debugging purposes.

        Args:
            slide: The slide to analyze

        Returns:
            Dictionary with detailed overflow analysis
        """
        analysis = self.detector.get_overflow_summary(slide)
        analysis["body_height"] = self.body_height
        analysis["slide_dimensions"] = {
            "width": self.slide_width,
            "height": self.slide_height,
        }
        analysis["margins"] = self.margins

        return analysis

    def has_external_overflow(self, slide: "Slide") -> bool:
        """
        Quick check if the slide has any external overflow requiring handling.

        Args:
            slide: The slide to check

        Returns:
            True if external overflow exists, False otherwise
        """
        return self.detector.has_any_overflow(slide)

    def validate_slide_structure(self, slide: "Slide") -> list[str]:
        """
        Validate slide structure for overflow processing.

        Args:
            slide: The slide to validate

        Returns:
            List of validation warnings
        """
        warnings = []

        if not slide.sections:
            warnings.append(
                "Slide has no sections - overflow processing may be limited"
            )

        for i, section in enumerate(slide.sections or []):
            if not section.position:
                warnings.append(f"Section {i} ({section.id}) missing position")
            if not section.size:
                warnings.append(f"Section {i} ({section.id}) missing size")

            # Check for potential infinite recursion in section structure
            if hasattr(section, "subsections") and section.subsections:
                visited = set()
                if self._has_circular_references(section, visited):
                    warnings.append(
                        f"Section {i} ({section.id}) has circular references"
                    )

        return warnings

    def _has_circular_references(self, section, visited: set) -> bool:
        """
        Check for circular references in section structure.

        Args:
            section: Section to check
            visited: Set of already visited section IDs

        Returns:
            True if circular references found
        """
        if section.id in visited:
            return True

        visited.add(section.id)

        if hasattr(section, "subsections") and section.subsections:
            for subsection in section.subsections:
                if self._has_circular_references(subsection, visited.copy()):
                    return True

        return False
