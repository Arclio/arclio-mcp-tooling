import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from markdowndeck.models import Section, Slide

from markdowndeck.models import Section as SectionModel
from markdowndeck.overflow.detector import OverflowDetector
from markdowndeck.overflow.handlers import StandardOverflowHandler

logger = logging.getLogger(__name__)

MAX_OVERFLOW_ITERATIONS = 50


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
            slide_height=self.slide_height,
            top_margin=self.margins["top"],
            bottom_margin=self.margins["bottom"],
        )
        self.handler = StandardOverflowHandler(
            slide_height=self.slide_height,
            top_margin=self.margins["top"],
            bottom_margin=self.margins["bottom"],
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
        final_slides = []
        current_slide = deepcopy(slide)
        iteration_count = 0

        while iteration_count < MAX_OVERFLOW_ITERATIONS:
            iteration_count += 1

            overflowing_element = self.detector.find_first_overflowing_element(
                current_slide
            )

            if not overflowing_element:
                self._finalize_slide(current_slide)
                final_slides.append(current_slide)
                break

            # FIXED: Correct implementation of the two-strike circuit breaker.
            if getattr(overflowing_element, "_overflow_moved", False):
                logger.debug(
                    f"Element {overflowing_element.object_id} has _overflow_moved=True, attempting final split before circuit breaker."
                )
                available_height = self.handler._calculate_available_height(
                    current_slide, overflowing_element
                )
                fitted_part, _ = self.handler._split_element_safely(
                    overflowing_element, available_height
                )

                if fitted_part is None:
                    # This is the second strike. The element is unsplittable and still overflowing.
                    logger.error(
                        f"OVERFLOW CIRCUIT BREAKER: Element {overflowing_element.object_id} "
                        f"of type {overflowing_element.element_type.value} is still overflowing on a new slide "
                        f"and cannot be split further. It will be placed as-is, potentially extending past slide boundaries."
                    )
                    self._finalize_slide(current_slide)
                    final_slides.append(current_slide)
                    break  # Terminate the loop.

            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_element, iteration_count
            )

            self._finalize_slide(fitted_slide)
            final_slides.append(fitted_slide)

            if not continuation_slide:
                break

            repositioned_continuation = self.layout_manager.calculate_positions(
                continuation_slide
            )
            current_slide = deepcopy(repositioned_continuation)

        if iteration_count >= MAX_OVERFLOW_ITERATIONS:
            logger.error(
                f"Max overflow iterations ({MAX_OVERFLOW_ITERATIONS}) reached. Finalizing remaining slide."
            )
            if current_slide:
                self._finalize_slide(current_slide)
                final_slides.append(current_slide)

        logger.info(
            f"Overflow processing complete: {len(final_slides)} slides created."
        )
        return final_slides

    def _finalize_slide(self, slide: "Slide") -> None:
        """
        Finalize a slide by populating renderable_elements from the root_section hierarchy.
        This must be called on EVERY slide before it is returned.
        """
        logger.debug(f"Finalizing slide {slide.object_id}...")

        final_renderable_elements = [
            e
            for e in slide.renderable_elements
            if e.element_type.value in ["title", "subtitle", "footer"]
        ]

        existing_object_ids = {
            el.object_id for el in final_renderable_elements if el.object_id
        }

        def extract_elements_from_section(section: Optional["Section"]):
            if not section:
                return
            for child in section.children:
                if isinstance(child, SectionModel):
                    extract_elements_from_section(child)
                else:
                    if (
                        child.object_id not in existing_object_ids
                        and child.position
                        and child.size
                    ):
                        final_renderable_elements.append(child)
                        if child.object_id:
                            existing_object_ids.add(child.object_id)

        if hasattr(slide, "root_section"):
            extract_elements_from_section(slide.root_section)

        slide.renderable_elements = final_renderable_elements
        slide.root_section = None
        slide.elements = []

        logger.info(
            f"Finalized slide {slide.object_id}: {len(slide.renderable_elements)} renderable elements."
        )
