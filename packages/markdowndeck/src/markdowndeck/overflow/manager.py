import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide

from markdowndeck.models import ElementType
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
        self.detector = OverflowDetector(
            body_height=self.body_height, top_margin=self.margins["top"]
        )
        self.handler = StandardOverflowHandler(
            body_height=self.body_height, top_margin=self.margins["top"]
        )

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

        Per OVERFLOW_SPEC.md: This method is responsible for orchestrating continuation slide
        layout and producing final renderable_elements lists while clearing sections hierarchy.

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
        continuation_count = 0  # FIXED: Track continuation count for unique IDs
        original_slide_id = slide.object_id

        while slides_to_process:
            # Check for infinite recursion protection
            iteration_count += 1
            if iteration_count > MAX_OVERFLOW_ITERATIONS:
                logger.error(
                    f"Maximum overflow iterations ({MAX_OVERFLOW_ITERATIONS}) exceeded for slide {original_slide_id}"
                )
                # Force-add remaining slides to prevent infinite loop - but finalize them first
                for remaining_slide in slides_to_process:
                    self._finalize_slide(remaining_slide)
                final_slides.extend(slides_to_process)
                break

            if len(final_slides) > MAX_CONTINUATION_SLIDES:
                logger.error(
                    f"Maximum continuation slides ({MAX_CONTINUATION_SLIDES}) exceeded for slide {original_slide_id}"
                )
                # Force-add remaining slides to prevent infinite slides - but finalize them first
                for remaining_slide in slides_to_process:
                    self._finalize_slide(remaining_slide)
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
                # No external overflow - finalize the slide per OVERFLOW_SPEC.md Rule #4
                self._finalize_slide(current_slide)
                final_slides.append(current_slide)
                logger.debug(
                    f"No EXTERNAL overflow detected in slide {current_slide.object_id} - slide finalized"
                )
                continue

            # Step 2: Handle external overflow
            logger.info(
                f"EXTERNAL overflow detected in slide {current_slide.object_id}, proceeding with handler."
            )
            continuation_count += 1  # Increment before creating the slide

            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_section, continuation_count
            )

            # Step 3: Finalize and add fitted slide to final results
            self._finalize_slide(fitted_slide)
            final_slides.append(fitted_slide)
            logger.debug(
                f"Added finalized fitted slide {fitted_slide.object_id} to final results"
            )

            # FIXED: Only process a continuation slide if one was actually created
            if continuation_slide:
                # Step 4: Calculate positions for continuation slide and enqueue for processing
                # Per OVERFLOW_SPEC.md Rule #3: OverflowManager orchestrates continuation slide layout
                logger.debug(
                    f"Positioning continuation slide {continuation_slide.object_id}"
                )
                repositioned_continuation = self.layout_manager.calculate_positions(
                    continuation_slide
                )
                slides_to_process.append(repositioned_continuation)
                logger.debug(
                    f"Enqueued repositioned continuation slide {continuation_slide.object_id} for processing"
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
            child_sections = [
                child for child in section.children if hasattr(child, "id")
            ]
            if child_sections:
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

        child_sections = [child for child in section.children if hasattr(child, "id")]
        return any(
            self._has_circular_references(subsection, visited.copy())
            for subsection in child_sections
        )

    def _finalize_slide(self, slide: "Slide") -> None:
        """
        Finalize a slide by creating renderable_elements list and clearing sections hierarchy.

        This is a critical fix to align with `DATA_FLOW.md` and `OVERFLOW_SPEC.md`. It resolves
        the brittle test issue by ensuring the `renderable_elements` list is built correctly.
        """
        logger.debug(f"Finalizing slide {slide.object_id}...")

        # Per spec, start with any meta-elements populated by LayoutManager
        final_renderable_elements = list(getattr(slide, "renderable_elements", []))

        # FIXED: Track both object IDs and meta element types to prevent duplicates
        existing_object_ids = {
            el.object_id for el in final_renderable_elements if el.object_id
        }
        meta_element_types = {
            ElementType.TITLE,
            ElementType.SUBTITLE,
            ElementType.FOOTER,
        }
        existing_meta_types = {
            el.element_type
            for el in final_renderable_elements
            if el.element_type in meta_element_types
        }

        # Recursively traverse the sections hierarchy to collect all positioned elements
        def extract_elements_from_sections(sections):
            for section in sections:
                # Process elements and subsections from the unified children list
                for child in section.children:
                    if not hasattr(child, "children"):  # It's an Element
                        if child.position and child.size:
                            is_duplicate = False
                            # Check for duplicate by object_id
                            if (
                                child.object_id
                                and child.object_id in existing_object_ids
                            ) or (
                                child.element_type in meta_element_types
                                and child.element_type in existing_meta_types
                            ):
                                is_duplicate = True

                            if not is_duplicate:
                                final_renderable_elements.append(child)
                                if child.object_id:
                                    existing_object_ids.add(child.object_id)
                                if child.element_type in meta_element_types:
                                    existing_meta_types.add(child.element_type)
                    else:  # It's a Section
                        extract_elements_from_sections([child])

        if hasattr(slide, "sections"):
            extract_elements_from_sections(slide.sections)

        # Update slide to the "Finalized" state
        slide.renderable_elements = final_renderable_elements
        slide.sections = []  # Per spec, sections are cleared after finalization
        slide.elements = []  # Clear the stale inventory list as well

        logger.info(
            f"Finalized slide {slide.object_id}: {len(slide.renderable_elements)} renderable elements."
        )
