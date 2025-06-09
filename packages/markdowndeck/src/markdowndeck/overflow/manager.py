"""Overflow management with strict jurisdictional boundaries."""

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

            fitted_slide, continuation_slide = self.handler.handle_overflow(
                current_slide, overflowing_section
            )

            # Step 3: Finalize and add fitted slide to final results
            self._finalize_slide(fitted_slide)
            final_slides.append(fitted_slide)
            logger.debug(
                f"Added finalized fitted slide {fitted_slide.object_id} to final results"
            )

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
                f"Repositioned and enqueued continuation slide {continuation_slide.object_id} for processing"
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

        Per OVERFLOW_SPEC.md Section 3: This method transforms a slide from "Positioned" state
        to "Finalized" state by rigorously following the data flow specification:
        1. Initialize empty renderable_elements list
        2. First: Add positioned meta-elements (TITLE, SUBTITLE, FOOTER) from slide.elements
        3. Then: Traverse slide.sections hierarchy to collect all positioned elements
        4. Assign complete list to slide.renderable_elements and clear slide.sections

        Args:
            slide: The slide to finalize
        """

        logger.debug(
            f"=== FINALIZING SLIDE: Starting finalization for slide {slide.object_id} ==="
        )
        logger.debug(f"Initial slide.elements count: {len(slide.elements)}")
        logger.debug(
            f"Initial slide.renderable_elements count: {len(slide.renderable_elements)}"
        )
        logger.debug(f"Slide.sections count: {len(slide.sections)}")

        # Preserve existing renderable_elements (meta-elements from LayoutManager)
        # and append positioned elements from sections hierarchy per updated OVERFLOW_SPEC.md
        if (
            not hasattr(slide, "renderable_elements")
            or slide.renderable_elements is None
        ):
            slide.renderable_elements = []

        # Start with existing meta-elements from LayoutManager
        renderable_elements = list(slide.renderable_elements)  # Copy existing list
        logger.debug(
            f"STEP 1: Preserving {len(renderable_elements)} existing meta-elements from LayoutManager"
        )

        # Keep track of existing object_ids and meta-element types to prevent duplicates
        existing_object_ids = {
            elem.object_id for elem in renderable_elements if elem.object_id
        }
        existing_meta_types = {
            elem.element_type
            for elem in renderable_elements
            if elem.element_type
            in [ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER]
        }
        logger.debug(f"Existing object_ids: {existing_object_ids}")
        logger.debug(f"Existing meta-element types: {existing_meta_types}")

        for i, element in enumerate(renderable_elements):
            logger.debug(
                f"  Preserved element {i}: {element.element_type} at {element.position} size {element.size}"
            )

        # STEP 2: Append positioned elements from slide.sections hierarchy
        logger.debug(
            "STEP 2: Traversing slide.sections hierarchy to append positioned elements..."
        )
        visited_sections = set()

        def extract_positioned_elements(sections, depth=0):
            indent = "  " * depth
            logger.debug(
                f"{indent}Extracting from {len(sections)} sections at depth {depth}"
            )

            for section_idx, section in enumerate(sections):
                # Separate elements and child sections from unified children list
                section_elements = [
                    child
                    for child in section.children
                    if not hasattr(child, "children")
                ]
                child_sections = [
                    child for child in section.children if hasattr(child, "children")
                ]

                logger.debug(
                    f"{indent}Section {section_idx}: {section.id}, elements_count={len(section_elements)}"
                )
                logger.debug(
                    f"{indent}  Section position={section.position}, size={section.size}"
                )

                # Circular reference protection
                if section.id in visited_sections:
                    logger.warning(
                        f"Circular reference detected in section {section.id} during finalization. Skipping."
                    )
                    continue

                visited_sections.add(section.id)

                if section_elements:
                    logger.debug(
                        f"{indent}  Processing {len(section_elements)} elements in section {section.id}"
                    )
                    # Only include elements that have proper position/size data
                    for elem_idx, element in enumerate(section_elements):
                        logger.debug(
                            f"{indent}    Element {elem_idx}: {element.element_type}, position={element.position}, size={element.size}"
                        )

                        if element.position is not None and element.size is not None:
                            # Check for duplicates using object_id or meta-element type
                            is_duplicate = False

                            # Check object_id duplication
                            if (
                                element.object_id
                                and element.object_id in existing_object_ids
                            ):
                                is_duplicate = True
                                logger.debug(
                                    f"{indent}      -> Skipped duplicate element {element.element_type} with object_id={element.object_id}"
                                )

                            # Check meta-element type duplication (only one TITLE, SUBTITLE, FOOTER allowed)
                            elif element.element_type in [
                                ElementType.TITLE,
                                ElementType.SUBTITLE,
                                ElementType.FOOTER,
                            ]:
                                if element.element_type in existing_meta_types:
                                    is_duplicate = True
                                    logger.debug(
                                        f"{indent}      -> Skipped duplicate meta-element {element.element_type} (already have one)"
                                    )

                            if not is_duplicate:
                                renderable_elements.append(element)
                                if element.object_id:
                                    existing_object_ids.add(element.object_id)
                                if element.element_type in [
                                    ElementType.TITLE,
                                    ElementType.SUBTITLE,
                                    ElementType.FOOTER,
                                ]:
                                    existing_meta_types.add(element.element_type)
                                logger.debug(
                                    f"{indent}      -> Added positioned section element {element.element_type}"
                                )
                        else:
                            logger.warning(
                                f"Section element {element.element_type} in section {section.id} missing position/size data - skipping"
                            )
                else:
                    logger.debug(f"{indent}  Section {section.id} has no elements")

                if child_sections:
                    logger.debug(
                        f"{indent}  Processing {len(child_sections)} child sections in section {section.id}"
                    )
                    extract_positioned_elements(child_sections, depth + 1)
                else:
                    logger.debug(
                        f"{indent}  Section {section.id} has no child sections"
                    )

                visited_sections.remove(section.id)

        extract_positioned_elements(slide.sections)

        # STEP 3: Update slide.renderable_elements with complete list (preserving + appending) and clear sections
        slide.renderable_elements = renderable_elements
        slide.sections = []

        logger.debug(f"=== FINALIZATION COMPLETE: slide {slide.object_id} ===")
        logger.debug(f"Final renderable_elements count: {len(renderable_elements)}")
        logger.debug(f"Sections cleared: {len(slide.sections)}")

        for i, elem in enumerate(renderable_elements):
            logger.debug(
                f"  Renderable element {i}: {elem.element_type} at {elem.position} size {elem.size}"
            )

        logger.info(
            f"Finalized slide {slide.object_id}: {len(renderable_elements)} elements, sections cleared"
        )
