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

    The LayoutManager provides a high-level interface to the layout calculation
    system, implementing the Universal Section Model with Rule #5 (proactive image scaling)
    where all slides use section-based layout for consistency and predictability.

    Per the specification: ImageElements are handled proactively during the layout phase.
    An ImageElement's size is always calculated to fit within its parent section's
    available width, while maintaining its aspect ratio. This ensures an image will
    never, by itself, cause its parent section's dimensions to expand beyond what was
    calculated based on other content or directives.
    """

    def __init__(
        self,
        slide_width: float = None,
        slide_height: float = None,
        margins: dict = None,
    ):
        """
        Initialize the layout manager with slide dimensions and margins.

        Args:
            slide_width: Width of slides in points (defaults to Google Slides standard)
            slide_height: Height of slides in points (defaults to Google Slides standard)
            margins: Dictionary with margin values for top, right, bottom, left
        """
        # Use constants for defaults
        self.slide_width = slide_width or DEFAULT_SLIDE_WIDTH
        self.slide_height = slide_height or DEFAULT_SLIDE_HEIGHT

        self.margins = margins or {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

        # Calculate derived dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # Initialize the position calculator with proactive scaling capabilities
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
        Calculate positions for all elements and sections in a slide with proactive image scaling.

        This is the main entry point for layout calculation using the unified
        Universal Section Model with Rule #5 (proactive image scaling). All slides now
        use section-based layout for consistency and predictability, with images
        proactively scaled to prevent layout shifts and overflow scenarios.

        The returned slide will have all elements positioned according to their
        content needs, with images scaled to fit their containers. Elements may extend
        beyond their containers' boundaries (overflow) only when explicitly intended
        through user directives, which is the expected behavior for this component.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The slide with all elements and sections positioned, images proactively scaled
        """
        logger.debug(
            f"=== LAYOUT DEBUG: LayoutManager calculating positions for slide: {slide.object_id} ==="
        )

        # Log initial state
        logger.debug(f"Initial slide.elements count: {len(slide.elements)}")
        logger.debug(
            f"Initial slide.sections count: {len(slide.sections) if hasattr(slide, 'sections') and slide.sections else 0}"
        )

        # Log initial section states
        if hasattr(slide, "sections") and slide.sections:
            for i, section in enumerate(slide.sections):
                logger.debug(
                    f"  Initial section {i}: {section.id}, position={section.position}, size={section.size}"
                )
                section_elements = [
                    c for c in section.children if not hasattr(c, "children")
                ]
                if section_elements:
                    logger.debug(f"    Section has {len(section_elements)} elements")
                    for j, elem in enumerate(section_elements):
                        logger.debug(
                            f"      Element {j}: {elem.element_type}, position={elem.position}, size={elem.size}"
                        )

        # Validate input
        if not slide:
            logger.error("Cannot calculate positions for None slide")
            raise ValueError("Slide cannot be None")

        if not hasattr(slide, "elements"):
            logger.error("Slide missing elements attribute")
            raise ValueError("Slide must have elements attribute")

        # Pre-process images for proactive scaling analysis
        self._analyze_images_for_scaling(slide)

        # Delegate to unified position calculator with proactive scaling
        try:
            logger.debug(
                "=== LAYOUT DEBUG: Calling position_calculator.calculate_positions ==="
            )
            positioned_slide = self.position_calculator.calculate_positions(slide)
            logger.debug(
                "=== LAYOUT DEBUG: position_calculator.calculate_positions completed ==="
            )

            # Log final state
            logger.debug(
                f"Final slide.elements count: {len(positioned_slide.elements)}"
            )
            logger.debug(
                f"Final slide.sections count: {len(positioned_slide.sections) if hasattr(positioned_slide, 'sections') and positioned_slide.sections else 0}"
            )

            # Log final section states
            if hasattr(positioned_slide, "sections") and positioned_slide.sections:
                for i, section in enumerate(positioned_slide.sections):
                    logger.debug(
                        f"  Final section {i}: {section.id}, position={section.position}, size={section.size}"
                    )
                    section_elements = [
                        c for c in section.children if not hasattr(c, "children")
                    ]
                    if section_elements:
                        logger.debug(
                            f"    Section has {len(section_elements)} elements"
                        )
                        for j, elem in enumerate(section_elements):
                            logger.debug(
                                f"      Element {j}: {elem.element_type}, position={elem.position}, size={elem.size}"
                            )

            # Log summary of positioning results with scaling information
            self._log_positioning_summary_with_scaling(positioned_slide)

            return positioned_slide

        except Exception as e:
            logger.error(
                f"Error calculating positions for slide {slide.object_id}: {e}",
                exc_info=True,
            )
            raise

    def _analyze_images_for_scaling(self, slide: Slide) -> None:
        """
        Analyze images in the slide for proactive scaling requirements.

        This method identifies all ImageElements and logs their scaling requirements
        for debugging purposes.

        Args:
            slide: The slide to analyze
        """
        from markdowndeck.models import ElementType

        image_elements = [
            element
            for element in slide.elements
            if element.element_type == ElementType.IMAGE
        ]

        if image_elements:
            logger.debug(
                f"Found {len(image_elements)} images for proactive scaling in slide {slide.object_id}"
            )

            for i, image in enumerate(image_elements):
                image_url = getattr(image, "url", "unknown")
                logger.debug(
                    f"Image {i}: url={image_url[:50]}{'...' if len(image_url) > 50 else ''}, "
                    f"has_size_directive={'width' in (image.directives or {}) or 'height' in (image.directives or {})}"
                )
        else:
            logger.debug(f"No images found in slide {slide.object_id}")

    def _log_positioning_summary_with_scaling(self, slide: Slide) -> None:
        """
        Log a summary of positioning results with proactive scaling information.

        Args:
            slide: The positioned slide to summarize
        """
        from markdowndeck.models import ElementType

        element_count = len(slide.elements)
        positioned_count = sum(
            1 for e in slide.elements if hasattr(e, "position") and e.position
        )
        sized_count = sum(1 for e in slide.elements if hasattr(e, "size") and e.size)

        # Count images that were proactively scaled
        image_elements = [
            e for e in slide.elements if e.element_type == ElementType.IMAGE
        ]
        scaled_images = sum(
            1 for img in image_elements if hasattr(img, "size") and img.size
        )

        section_count = (
            len(slide.sections) if hasattr(slide, "sections") and slide.sections else 0
        )
        positioned_sections = (
            sum(
                1
                for s in (slide.sections or [])
                if hasattr(s, "position") and s.position
            )
            if slide.sections
            else 0
        )

        logger.debug(
            f"Positioning summary for slide {slide.object_id}: "
            f"elements={element_count} (positioned={positioned_count}, sized={sized_count}), "
            f"images={len(image_elements)} (scaled={scaled_images}), "
            f"sections={section_count} (positioned={positioned_sections})"
        )

        # Check for potential overflow situations (informational only)
        if slide.sections:
            self._check_section_overflow_with_scaling_info(slide.sections)

    def _check_section_overflow_with_scaling_info(self, sections: list) -> None:
        """
        Check and log potential element overflow within sections with scaling information.

        This method does not modify anything - it only logs warnings about elements
        that extend beyond their section boundaries, with special attention to images
        that should have been proactively scaled.

        Args:
            sections: List of sections to check
        """
        from markdowndeck.models import ElementType

        for section in sections:
            if not (
                hasattr(section, "position")
                and section.position
                and hasattr(section, "size")
                and section.size
            ):
                continue

            section_left, section_top = section.position
            section_width, section_height = section.size
            section_right = section_left + section_width
            section_bottom = section_top + section_height

            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            if section_elements:
                for element in section_elements:
                    if not (
                        hasattr(element, "position")
                        and element.position
                        and hasattr(element, "size")
                        and element.size
                    ):
                        continue

                    elem_left, elem_top = element.position
                    elem_width, elem_height = element.size
                    elem_right = elem_left + elem_width
                    elem_bottom = elem_top + elem_height

                    # Check for overflow
                    has_overflow = (
                        elem_left < section_left
                        or elem_right > section_right
                        or elem_top < section_top
                        or elem_bottom > section_bottom
                    )

                    if has_overflow:
                        if element.element_type == ElementType.IMAGE:
                            # Images should never overflow due to proactive scaling
                            logger.warning(
                                f"UNEXPECTED: Image element {getattr(element, 'object_id', 'unknown')} "
                                f"overflows section {section.id} despite proactive scaling. "
                                f"This may indicate a scaling bug."
                            )
                        else:
                            # Other elements may overflow, which is acceptable
                            logger.debug(
                                f"Element {getattr(element, 'object_id', 'unknown')} "
                                f"({element.element_type}) extends beyond section {section.id} "
                                f"boundaries (this is expected for content overflow)"
                            )

            # Recursively check child sections
            child_sections = [c for c in section.children if hasattr(c, "children")]
            if child_sections:
                self._check_section_overflow_with_scaling_info(child_sections)

    def get_slide_dimensions(self) -> tuple[float, float]:
        """
        Get the configured slide dimensions.

        Returns:
            (width, height) tuple in points
        """
        return (self.slide_width, self.slide_height)

    def get_content_area(self) -> tuple[float, float, float, float]:
        """
        Get the content area dimensions accounting for margins.

        Returns:
            (left, top, width, height) tuple defining the content area
        """
        return (
            self.margins["left"],
            self.margins["top"],
            self.max_content_width,
            self.max_content_height,
        )

    def get_body_zone(self) -> tuple[float, float, float, float]:
        """
        Get the body zone area (excluding header and footer zones).

        Returns:
            (left, top, width, height) tuple defining the body zone
        """
        return self.position_calculator.get_body_zone_area()

    def validate_slide_structure(self, slide: Slide) -> list[str]:
        """
        Validate slide structure and return any warnings, with special attention to image scaling.

        This performs basic structural validation to help identify potential
        issues before layout calculation, including image scaling requirements.

        Args:
            slide: The slide to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        if not slide.elements:
            warnings.append("Slide has no elements")

        # Check for elements without required attributes
        image_count = 0
        for i, element in enumerate(slide.elements):
            if not hasattr(element, "element_type"):
                warnings.append(f"Element {i} missing element_type")
                continue

            if hasattr(element, "element_type") and element.element_type:
                # Type-specific validation
                if element.element_type.name in ("TEXT", "TITLE", "SUBTITLE", "QUOTE"):
                    if not hasattr(element, "text") or not element.text:
                        warnings.append(f"Text element {i} has no content")

                elif element.element_type.name in ("BULLET_LIST", "ORDERED_LIST"):
                    if not hasattr(element, "items") or not element.items:
                        warnings.append(f"List element {i} has no items")

                elif element.element_type.name == "TABLE":
                    if not hasattr(element, "rows") or not element.rows:
                        warnings.append(f"Table element {i} has no rows")

                elif element.element_type.name == "IMAGE":
                    image_count += 1
                    if not hasattr(element, "url") or not element.url:
                        warnings.append(f"Image element {i} has no URL")
                    else:
                        # Check for potentially problematic image directives
                        if hasattr(element, "directives") and element.directives:
                            width_dir = element.directives.get("width")
                            height_dir = element.directives.get("height")

                            if width_dir and height_dir:
                                warnings.append(
                                    f"Image element {i} has both width and height directives - "
                                    f"this may conflict with proactive aspect ratio scaling"
                                )

        if image_count > 0:
            logger.debug(
                f"Slide has {image_count} images that will be proactively scaled"
            )

        # Check section structure if present
        if hasattr(slide, "sections") and slide.sections:
            section_warnings = self._validate_section_structure(slide.sections)
            warnings.extend(section_warnings)

        return warnings

    def _validate_section_structure(self, sections: list, level: int = 0) -> list[str]:
        """
        Validate section structure recursively.

        Args:
            sections: List of sections to validate
            level: Current nesting level

        Returns:
            List of warning messages
        """
        warnings = []

        for section in sections:
            if not hasattr(section, "id") or not section.id:
                warnings.append(f"Section at level {level} missing ID")

            # Check for both elements and child sections (unusual but not invalid)
            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            child_sections = [c for c in section.children if hasattr(c, "children")]
            has_elements = bool(section_elements)
            has_subsections = bool(child_sections)

            if has_elements and has_subsections:
                warnings.append(
                    f"Section {getattr(section, 'id', 'unknown')} has both elements and subsections"
                )

            if not has_elements and not has_subsections:
                warnings.append(f"Section {getattr(section, 'id', 'unknown')} is empty")

            # Check for directive conflicts that might affect scaling
            if hasattr(section, "directives") and section.directives:
                height_dir = section.directives.get("height")
                if height_dir and has_elements:
                    # Check if section contains images
                    from markdowndeck.models import ElementType

                    has_images = any(
                        e.element_type == ElementType.IMAGE
                        for e in section_elements
                        if hasattr(e, "element_type")
                    )

                    if has_images:
                        logger.debug(
                            f"Section {getattr(section, 'id', 'unknown')} has fixed height "
                            f"with images - images will be scaled to fit available space"
                        )

            # Recursively validate child sections
            if has_subsections:
                subsection_warnings = self._validate_section_structure(
                    child_sections, level + 1
                )
                warnings.extend(subsection_warnings)

        return warnings

    def get_scaling_analysis(self, slide: Slide) -> dict:
        """
        Get detailed analysis of image scaling requirements for debugging.

        Args:
            slide: The slide to analyze

        Returns:
            Dictionary with scaling analysis details
        """
        from markdowndeck.models import ElementType

        analysis = {
            "slide_id": slide.object_id,
            "total_elements": len(slide.elements),
            "images": [],
            "scaling_summary": {
                "total_images": 0,
                "images_with_url": 0,
                "images_with_directives": 0,
                "potential_scaling_conflicts": 0,
            },
        }

        for i, element in enumerate(slide.elements):
            if element.element_type == ElementType.IMAGE:
                image_info = {
                    "index": i,
                    "has_url": bool(getattr(element, "url", "")),
                    "url_preview": (
                        (getattr(element, "url", "")[:50] + "...")
                        if getattr(element, "url", "")
                        else ""
                    ),
                    "has_directives": bool(getattr(element, "directives", {})),
                    "directives": getattr(element, "directives", {}),
                    "has_scaling_conflict": False,
                }

                # Check for potential scaling conflicts
                directives = getattr(element, "directives", {})
                if directives.get("width") and directives.get("height"):
                    image_info["has_scaling_conflict"] = True
                    analysis["scaling_summary"]["potential_scaling_conflicts"] += 1

                analysis["images"].append(image_info)
                analysis["scaling_summary"]["total_images"] += 1

                if image_info["has_url"]:
                    analysis["scaling_summary"]["images_with_url"] += 1
                if image_info["has_directives"]:
                    analysis["scaling_summary"]["images_with_directives"] += 1

        return analysis
