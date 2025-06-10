"""Refactored base position calculator with proactive image scaling."""

import logging

from markdowndeck.layout.constants import (
    BODY_TO_FOOTER_SPACING,
    CODE_WIDTH_FRACTION,
    DEFAULT_MARGIN_BOTTOM,
    DEFAULT_MARGIN_LEFT,
    DEFAULT_MARGIN_RIGHT,
    DEFAULT_MARGIN_TOP,
    DEFAULT_SLIDE_HEIGHT,
    # Default dimensions
    DEFAULT_SLIDE_WIDTH,
    FOOTER_HEIGHT,
    # Zone dimensions
    HEADER_HEIGHT,
    # Inter-zone spacing
    HEADER_TO_BODY_SPACING,
    HORIZONTAL_SPACING,
    IMAGE_WIDTH_FRACTION,
    LIST_WIDTH_FRACTION,
    QUOTE_WIDTH_FRACTION,
    SUBTITLE_WIDTH_FRACTION,
    TABLE_WIDTH_FRACTION,
    # Element proportions
    TITLE_WIDTH_FRACTION,
    VERTICAL_SPACING,
)
from markdowndeck.models import ElementType, Slide
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class PositionCalculator:
    """
    Unified layout calculator implementing proactive image scaling.

    Per Rule #5 of the specification: ImageElements are handled proactively during
    the layout phase. An ImageElement's size is always calculated to fit within its
    parent section's available width, while maintaining its aspect ratio. This ensures
    an image will never, by itself, cause its parent section's dimensions to expand
    beyond what was calculated based on other content or directives.
    """

    def __init__(
        self,
        slide_width: float = None,
        slide_height: float = None,
        margins: dict = None,
    ):
        """
        Initialize the position calculator with slide dimensions and margins.

        Args:
            slide_width: Width of the slide in points (defaults to Google Slides standard)
            slide_height: Height of the slide in points (defaults to Google Slides standard)
            margins: Dictionary with margin values for top, right, bottom, left
        """
        # Use defaults if not provided
        self.slide_width = slide_width or DEFAULT_SLIDE_WIDTH
        self.slide_height = slide_height or DEFAULT_SLIDE_HEIGHT

        self.margins = margins or {
            "top": DEFAULT_MARGIN_TOP,
            "right": DEFAULT_MARGIN_RIGHT,
            "bottom": DEFAULT_MARGIN_BOTTOM,
            "left": DEFAULT_MARGIN_LEFT,
        }

        # Calculate content area dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # Define fixed slide zones with clear spacing
        self._define_slide_zones()

        # Make spacing constants available as attributes for other modules to access
        self.HORIZONTAL_SPACING = HORIZONTAL_SPACING
        self.VERTICAL_SPACING = VERTICAL_SPACING

        logger.debug(
            f"PositionCalculator initialized: slide={self.slide_width}x{self.slide_height}, "
            f"content_area={self.max_content_width}x{self.max_content_height}, "
            f"body_zone=({self.body_left}, {self.body_top}, {self.body_width}, {self.body_height})"
        )

    def _define_slide_zones(self):
        """Define the fixed zones of the slide with clear spacing."""
        # Header zone
        self.header_top = self.margins["top"]
        self.header_left = self.margins["left"]
        self.header_width = self.max_content_width
        self.header_height = HEADER_HEIGHT
        self.header_bottom = self.header_top + self.header_height

        # Body zone (with clear spacing from header and footer)
        self.body_top = self.header_bottom + HEADER_TO_BODY_SPACING
        self.body_left = self.margins["left"]
        self.body_width = self.max_content_width

        # Footer zone
        self.footer_height = FOOTER_HEIGHT
        self.footer_bottom = self.slide_height - self.margins["bottom"]
        self.footer_top = self.footer_bottom - self.footer_height
        self.footer_left = self.margins["left"]
        self.footer_width = self.max_content_width

        # Body height is what's left between body_top and footer space
        body_bottom_limit = self.footer_top - BODY_TO_FOOTER_SPACING
        self.body_height = body_bottom_limit - self.body_top

        logger.debug(
            f"Slide zones defined: "
            f"header=({self.header_left}, {self.header_top}, {self.header_width}, {self.header_height}), "
            f"body=({self.body_left}, {self.body_top}, {self.body_width}, {self.body_height}), "
            f"footer=({self.footer_left}, {self.footer_top}, {self.footer_width}, {self.footer_height})"
        )

    def calculate_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions for all elements using the Universal Section Model with proactive image scaling.

        This is the main entry point that implements the unified architecture.
        All slides are treated as section-based layouts. If no sections are defined,
        a single root section is created to contain all body elements.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The slide with all elements and sections positioned
        """
        logger.debug(
            f"=== POSITION CALC DEBUG: Calculating positions for slide: {slide.object_id} ==="
        )

        # Log initial state before any processing
        logger.debug(f"Before processing - slide.elements: {len(slide.elements)}")
        logger.debug(
            f"Before processing - slide.sections: {len(slide.sections) if hasattr(slide, 'sections') and slide.sections else 0}"
        )

        if hasattr(slide, "sections") and slide.sections:
            for i, section in enumerate(slide.sections):
                logger.debug(
                    f"  Before section {i}: {section.id}, position={section.position}, size={section.size}"
                )

        # Always position header and footer elements first (they use fixed zones)
        logger.debug("=== POSITION CALC DEBUG: Positioning header/footer elements ===")
        self._position_header_elements(slide)
        self._position_footer_elements(slide)

        # Implement Universal Section Model
        logger.debug("=== POSITION CALC DEBUG: Ensuring section-based layout ===")
        sections_to_process = self._ensure_section_based_layout(slide)

        logger.debug(
            f"After _ensure_section_based_layout - sections_to_process: {len(sections_to_process)}"
        )
        for i, section in enumerate(sections_to_process):
            logger.debug(
                f"  Section to process {i}: {section.id}, position={section.position}, size={section.size}"
            )
            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            if section_elements:
                logger.debug(f"    Has {len(section_elements)} elements")

        # Apply section-based layout to all slides
        logger.debug(
            f"=== POSITION CALC DEBUG: Using unified section-based layout for slide {slide.object_id} ==="
        )
        from markdowndeck.layout.calculator.section_layout import (
            calculate_section_based_positions,
        )

        # Update the slide's sections with the processed sections
        slide.sections = sections_to_process

        logger.debug(
            "=== POSITION CALC DEBUG: Calling calculate_section_based_positions ==="
        )
        final_slide = calculate_section_based_positions(self, slide)
        logger.debug(
            "=== POSITION CALC DEBUG: calculate_section_based_positions completed ==="
        )

        # Log final state
        logger.debug(
            f"After section layout - final_slide.elements: {len(final_slide.elements)}"
        )
        logger.debug(
            f"After section layout - final_slide.sections: {len(final_slide.sections) if hasattr(final_slide, 'sections') and final_slide.sections else 0}"
        )

        if hasattr(final_slide, "sections") and final_slide.sections:
            for i, section in enumerate(final_slide.sections):
                logger.debug(
                    f"  After section {i}: {section.id}, position={section.position}, size={section.size}"
                )
                section_elements = [
                    c for c in section.children if not hasattr(c, "children")
                ]
                if section_elements:
                    logger.debug(
                        f"    Has {len(section_elements)} elements with positions:"
                    )
                    for j, elem in enumerate(section_elements):
                        logger.debug(
                            f"      Element {j}: {elem.element_type}, position={elem.position}, size={elem.size}"
                        )

        # Populate slide.renderable_elements with positioned meta-elements per updated LAYOUT_SPEC.md
        # These are meta-elements (TITLE, SUBTITLE, FOOTER) positioned directly on the slide
        if (
            not hasattr(final_slide, "renderable_elements")
            or final_slide.renderable_elements is None
        ):
            final_slide.renderable_elements = []

        # Add positioned meta-elements that are positioned directly on slide
        for element in final_slide.elements:
            if (
                element.element_type
                in [ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER]
                and element.position is not None
                and element.size is not None
            ):
                final_slide.renderable_elements.append(element)
                logger.debug(
                    f"Added positioned meta-element to renderable_elements: {element.element_type}"
                )

        # Clear the stale inventory list per LAYOUT_SPEC.md Rule #3 and DATA_FLOW.md
        # The slide.sections hierarchy is now the authoritative source for structural/spatial data
        final_slide.elements = []
        logger.debug(
            f"Populated slide.renderable_elements with {len(final_slide.renderable_elements)} meta-elements and cleared slide.elements inventory list"
        )

        return final_slide

    def _ensure_section_based_layout(self, slide: Slide) -> list[Section]:
        """
        Ensure the slide has a section-based layout.

        If no sections exist, creates a single root section containing all body elements.
        This implements the Universal Section Model from the specification.

        Args:
            slide: The slide to process

        Returns:
            List of sections ready for section-based layout processing
        """
        if slide.sections:
            # Slide already has sections, use them as-is
            logger.debug(
                f"Slide {slide.object_id} has {len(slide.sections)} existing sections"
            )
            return slide.sections

        # Create a root section for body elements
        body_elements = self.get_body_elements(slide)

        if not body_elements:
            logger.debug(
                f"Slide {slide.object_id} has no body elements, creating empty root section"
            )
            # Still create a root section for consistency
            root_section = Section(
                id="root",
                content="",
                children=[],
                position=(self.body_left, self.body_top),
                size=None,  # Allow intrinsic height calculation
                directives={},  # No pre-set height directive
            )
            return [root_section]

        # Create root section with all body elements
        root_section = Section(
            id="root",
            content="Auto-generated root section",
            children=body_elements,
            position=(self.body_left, self.body_top),
            size=None,  # Allow intrinsic height calculation
            directives={},  # No pre-set height directive
        )

        logger.debug(
            f"Created root section for slide {slide.object_id} with {len(body_elements)} elements"
        )

        return [root_section]

    def _position_header_elements(self, slide: Slide):
        """Position title and subtitle elements within the fixed header zone."""
        title_elements = [
            e for e in slide.elements if e.element_type == ElementType.TITLE
        ]
        subtitle_elements = [
            e for e in slide.elements if e.element_type == ElementType.SUBTITLE
        ]

        current_y = self.header_top

        # Position title
        if title_elements:
            title = title_elements[0]
            title_width = self._calculate_element_width(title, self.header_width)

            # Use content-aware metrics to calculate proper height
            from markdowndeck.layout.metrics import calculate_element_height

            title_height = calculate_element_height(title, title_width)

            title.size = (title_width, title_height)

            # Center horizontally in header zone
            title_x = self.header_left + (self.header_width - title_width) / 2
            title.position = (title_x, current_y)

            current_y += title_height + 8  # Small spacing between title and subtitle

            logger.debug(
                f"Positioned title at ({title_x:.1f}, {title.position[1]:.1f}) with size {title.size}"
            )

        # Position subtitle
        if subtitle_elements:
            subtitle = subtitle_elements[0]
            subtitle_width = self._calculate_element_width(subtitle, self.header_width)

            # Use content-aware metrics to calculate proper height
            from markdowndeck.layout.metrics import calculate_element_height

            subtitle_height = calculate_element_height(subtitle, subtitle_width)

            subtitle.size = (subtitle_width, subtitle_height)

            # Center horizontally in header zone
            subtitle_x = self.header_left + (self.header_width - subtitle_width) / 2
            subtitle.position = (subtitle_x, current_y)

            logger.debug(
                f"Positioned subtitle at ({subtitle_x:.1f}, {subtitle.position[1]:.1f}) with size {subtitle.size}"
            )

    def _position_footer_elements(self, slide: Slide):
        """Position footer elements within the fixed footer zone."""
        footer_elements = [
            e for e in slide.elements if e.element_type == ElementType.FOOTER
        ]

        if footer_elements:
            footer = footer_elements[0]
            footer_width = self.footer_width

            # Use content-aware metrics to calculate footer height based on content
            from markdowndeck.layout.metrics import calculate_element_height

            footer_height = calculate_element_height(footer, footer_width)

            footer.size = (footer_width, footer_height)

            # Position at bottom of footer zone
            footer.position = (self.footer_left, self.footer_top)

            logger.debug(
                f"Positioned footer at {footer.position} with size {footer.size}"
            )

    def _calculate_element_width(self, element, container_width: float) -> float:
        """
        Calculate the width for an element based on its type and directives.

        Args:
            element: The element to calculate width for
            container_width: Width of the container

        Returns:
            Calculated width for the element
        """
        # Check for explicit width directive
        if hasattr(element, "directives") and element.directives:
            width_directive = element.directives.get("width")
            if width_directive is not None:
                try:
                    if isinstance(width_directive, float) and 0 < width_directive <= 1:
                        return container_width * width_directive
                    if isinstance(width_directive, int | float) and width_directive > 1:
                        return min(float(width_directive), container_width)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid width directive: {width_directive}")

        # PROACTIVE IMAGE SCALING: For images, apply width fraction but ensure they fit
        if element.element_type == ElementType.IMAGE:
            # Images get their width based on the container and width fraction
            base_width = container_width * IMAGE_WIDTH_FRACTION

            # Check for explicit width override
            if hasattr(element, "directives") and element.directives:
                width_directive = element.directives.get("width")
                if width_directive is not None:
                    try:
                        if (
                            isinstance(width_directive, float)
                            and 0 < width_directive <= 1
                        ):
                            base_width = container_width * width_directive
                        elif (
                            isinstance(width_directive, int | float)
                            and width_directive > 1
                        ):
                            base_width = min(float(width_directive), container_width)
                    except (ValueError, TypeError):
                        pass

            # Ensure image width never exceeds container
            image_width = min(base_width, container_width)
            logger.debug(
                f"Proactively scaled image width: {image_width:.1f} (container: {container_width:.1f})"
            )
            return image_width

        # Use default width fractions based on element type
        width_fractions = {
            ElementType.TITLE: TITLE_WIDTH_FRACTION,
            ElementType.SUBTITLE: SUBTITLE_WIDTH_FRACTION,
            ElementType.QUOTE: QUOTE_WIDTH_FRACTION,
            ElementType.TABLE: TABLE_WIDTH_FRACTION,
            ElementType.CODE: CODE_WIDTH_FRACTION,
            ElementType.BULLET_LIST: LIST_WIDTH_FRACTION,
            ElementType.ORDERED_LIST: LIST_WIDTH_FRACTION,
        }

        fraction = width_fractions.get(
            element.element_type, 1.0
        )  # Default to full width
        return container_width * fraction

    def calculate_element_height_with_proactive_scaling(
        self, element, available_width: float, available_height: float = 0
    ) -> float:
        """
        Calculate element height with proactive image scaling applied.

        For images, this ensures they are scaled to fit within the container constraints.
        For other elements, this delegates to the standard metrics calculation.

        Args:
            element: The element to calculate height for
            available_width: Available width for the element
            available_height: Available height for the element (for images)

        Returns:
            Calculated height that respects container constraints
        """
        if element.element_type == ElementType.IMAGE:
            # For images, use the proactive scaling image metrics
            from markdowndeck.layout.metrics.image import calculate_image_element_height

            return calculate_image_element_height(
                element, available_width, available_height
            )
        # For other elements, use standard metrics
        from markdowndeck.layout.metrics import calculate_element_height

        return calculate_element_height(element, available_width)

    def get_body_elements(self, slide: Slide) -> list:
        """
        Get all elements that belong in the body zone (not title, subtitle, or footer).

        Args:
            slide: The slide to get body elements from

        Returns:
            List of body elements
        """
        return [
            element
            for element in slide.elements
            if element.element_type
            not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]

    def get_body_zone_area(self) -> tuple[float, float, float, float]:
        """
        Get the body zone area coordinates.

        Returns:
            Tuple of (left, top, width, height) for the body zone
        """
        return (self.body_left, self.body_top, self.body_width, self.body_height)
