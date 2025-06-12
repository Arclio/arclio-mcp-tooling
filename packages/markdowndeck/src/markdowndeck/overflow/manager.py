import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide

from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler

logger = logging.getLogger(__name__)

MAX_OVERFLOW_ITERATIONS = 50
MAX_CONTINUATION_SLIDES = 25


class OverflowManager:
    """
    Main orchestrator for overflow detection and handling with strict jurisdictional boundaries.
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
    ):
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}
        self.detector = OverflowDetector(
            slide_height=self.slide_height, top_margin=self.margins["top"]
        )
        self.handler = StandardOverflowHandler(
            slide_height=self.slide_height, top_margin=self.margins["top"]
        )
        from markdowndeck.layout import LayoutManager

        self.layout_manager = LayoutManager(slide_width, slide_height, margins)
        logger.debug(
            f"OverflowManager initialized with slide_dimensions={slide_width}x{slide_height}, margins={self.margins}"
        )

    def process_slide(self, slide: "Slide") -> list["Slide"]:
        """
        Process a positioned slide and handle any external overflow using the main algorithm.
        """
        logger.debug(f"Processing slide {slide.object_id} for EXTERNAL overflow only")

        final_slides = []
        slides_to_process = [slide]
        iteration_count = 0
        continuation_count = 0
        original_slide_id = slide.object_id

        while slides_to_process:
            iteration_count += 1
            if iteration_count > MAX_OVERFLOW_ITERATIONS:
                logger.error(
                    f"Max overflow iterations ({MAX_OVERFLOW_ITERATIONS}) exceeded for {original_slide_id}"
                )
                for remaining_slide in slides_to_process:
                    self._finalize_slide(remaining_slide)
                final_slides.extend(slides_to_process)
                break

            current_slide = slides_to_process.pop(0)
            overflowing_section = self.detector.find_first_overflowing_section(
                current_slide
            )

            if overflowing_section is None:
                self._finalize_slide(current_slide)
                final_slides.append(current_slide)
                continue

            continuation_count += 1
            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_section, continuation_count
            )

            self._finalize_slide(fitted_slide)
            final_slides.append(fitted_slide)

            if continuation_slide:
                repositioned_continuation = self.layout_manager.calculate_positions(
                    continuation_slide
                )
                slides_to_process.append(repositioned_continuation)

        logger.info(
            f"Overflow processing complete: {len(final_slides)} slides created from 1 input slide"
        )
        return final_slides

    def _finalize_slide(self, slide: "Slide") -> None:
        """
        Finalize a slide by creating renderable_elements list from the root_section hierarchy.
        REFACTORED: To traverse the `root_section` per the new architecture.
        """
        logger.debug(f"Finalizing slide {slide.object_id}...")

        final_renderable_elements = list(getattr(slide, "renderable_elements", []))
        existing_object_ids = {
            el.object_id for el in final_renderable_elements if el.object_id
        }

        def extract_elements_from_section(section):
            if not section:
                return
            for child in section.children:
                if not hasattr(child, "children"):  # It's an Element
                    if (
                        child.position
                        and child.size
                        and child.object_id not in existing_object_ids
                    ):
                        final_renderable_elements.append(child)
                        if child.object_id:
                            existing_object_ids.add(child.object_id)
                else:  # It's a Section
                    extract_elements_from_section(child)

        # REFACTORED: Start traversal from the single root_section.
        if hasattr(slide, "root_section"):
            extract_elements_from_section(slide.root_section)

        slide.renderable_elements = final_renderable_elements
        # Per spec, section hierarchy is cleared after finalization.
        slide.root_section = None
        slide.elements = []

        logger.info(
            f"Finalized slide {slide.object_id}: {len(slide.renderable_elements)} renderable elements."
        )
