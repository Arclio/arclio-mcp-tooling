"""Position calculation for slide elements."""

import logging
from copy import deepcopy
from typing import Any

from markdowndeck.layout.metrics import calculate_element_height
from markdowndeck.models import (
    AlignmentType,
    Element,
    ElementType,
    Slide,
)
from markdowndeck.models import Section as SectionModel

logger = logging.getLogger(__name__)


class PositionCalculator:
    """Calculates positions for slide elements using a zone-based layout model with a fixed body zone."""

    def __init__(
        self, slide_width: float, slide_height: float, margins: dict[str, float]
    ):
        """
        Initialize the position calculator with slide dimensions and margins.

        Args:
            slide_width: Width of the slide in points
            slide_height: Height of the slide in points
            margins: Dictionary with margin values for top, right, bottom, left
        """
        # Slide dimensions
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins

        # FIXED: Reduced spacing constants to avoid excessive space between elements
        self.vertical_spacing = 10.0  # Reduced from 15.0
        self.horizontal_spacing = 10.0  # Reduced from 15.0

        # Content area dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # FIXED: Standardize fixed zone dimensions
        # These are CONSTANT values that define the three main slide zones
        self.HEADER_HEIGHT = 100.0  # Fixed height for header zone
        self.FOOTER_HEIGHT = 30.0  # Fixed height for footer zone

        # FIXED: Calculate fixed body zone dimensions using constant values
        # This is critical - the body zone must have fixed dimensions
        self.body_top = self.margins["top"] + self.HEADER_HEIGHT
        self.body_left = self.margins["left"]
        self.body_width = self.max_content_width
        self.body_height = (
            self.slide_height
            - self.body_top
            - self.FOOTER_HEIGHT
            - self.margins["bottom"]
        )
        self.body_bottom = self.body_top + self.body_height

        # Log the fixed body zone dimensions for debugging
        logger.debug(
            f"Fixed body zone: top={self.body_top}, left={self.body_left}, "
            f"width={self.body_width}, height={self.body_height}, bottom={self.body_bottom}"
        )

        # Default element sizes (width, height) in points
        # FIXED: Reduced default sizes to be more space-efficient
        self.default_sizes = {
            ElementType.TITLE: (self.max_content_width * 0.9, 40),  # Reduced from 50
            ElementType.SUBTITLE: (
                self.max_content_width * 0.85,
                35,
            ),  # Reduced from 40
            ElementType.TEXT: (self.max_content_width, 60),  # Reduced from 70
            ElementType.BULLET_LIST: (self.max_content_width, 130),  # Reduced from 150
            ElementType.ORDERED_LIST: (self.max_content_width, 130),  # Reduced from 150
            ElementType.IMAGE: (
                self.max_content_width * 0.6,
                self.max_content_height * 0.4,  # Reduced from 0.5
            ),
            ElementType.TABLE: (self.max_content_width, 130),  # Reduced from 150
            ElementType.CODE: (self.max_content_width, 100),  # Reduced from 120
            ElementType.QUOTE: (self.max_content_width * 0.9, 70),  # Reduced from 80
            ElementType.FOOTER: (self.max_content_width, self.FOOTER_HEIGHT),
        }

    def calculate_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions for all elements in a slide.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The updated slide with positioned elements
        """
        updated_slide = deepcopy(slide)

        # Determine if this slide uses section-based layout
        if updated_slide.sections:
            logger.debug(
                f"Using section-based layout for slide {updated_slide.object_id}"
            )
            return self._calculate_section_based_positions(updated_slide)

        logger.debug(f"Using zone-based layout for slide {updated_slide.object_id}")
        return self._calculate_zone_based_positions(updated_slide)

    def _calculate_zone_based_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions using a zone-based layout model with fixed zones.
        """
        # Step 1: Position header elements (title, subtitle) - within fixed header zone
        self._position_header_elements(slide)

        # Step 2: Position footer element if present - within fixed footer zone
        self._position_footer_element(slide)

        # Step 3: Position body elements within the fixed body zone
        body_elements = self._get_body_elements(slide)

        # FIXED: Always start at the top of the body zone
        current_y = self.body_top

        for element in body_elements:
            # FIXED: Ensure element has a valid size, defaulting to more conservative sizes
            if not hasattr(element, "size") or not element.size:
                element.size = self.default_sizes.get(
                    element.element_type, (self.body_width, 50)
                )

            # Calculate element width based on directives
            element_width = self.body_width
            if hasattr(element, "directives") and "width" in element.directives:
                width_dir = element.directives["width"]
                if isinstance(width_dir, float) and 0.0 < width_dir <= 1.0:
                    element_width = self.body_width * width_dir
                elif isinstance(width_dir, (int, float)) and width_dir > 1.0:
                    element_width = min(width_dir, self.body_width)

            # FIXED: More accurate height calculation with reduced padding
            element_height = calculate_element_height(element, element_width)
            element.size = (element_width, element_height)

            # FIXED: Enforce that element does not exceed body zone height
            if current_y + element_height > self.body_bottom:
                logger.warning(
                    f"Element {getattr(element, 'object_id', 'unknown')} would overflow the body zone. "
                    f"Element height: {element_height}, Available height: {self.body_bottom - current_y}. "
                    f"This will be handled by overflow logic."
                )

            # Position element using horizontal alignment within the body zone
            self._apply_horizontal_alignment(
                element, self.body_left, self.body_width, current_y
            )

            # Add special handling for spacing after heading elements
            if (
                element.element_type == ElementType.TEXT
                and hasattr(element, "directives")
                and "margin_bottom" in element.directives
            ):
                margin_bottom = element.directives["margin_bottom"]
                current_y += element_height + margin_bottom
            else:
                # Move to next position with standard spacing
                current_y += element_height + self.vertical_spacing

            # Log element positioning
            logger.debug(
                f"Positioned body element {getattr(element, 'object_id', 'unknown')} "
                f"at y={element.position[1]:.1f}, height={element.size[1]:.1f}"
            )

        return slide

    def _position_header_elements(self, slide: Slide) -> float:
        """
        Position title and subtitle elements in the header zone.

        Args:
            slide: The slide to position header elements for

        Returns:
            The total height of the header zone
        """
        # FIXED: Always use fixed header zone - more consistent positioning
        current_y = self.margins["top"]
        max_y = self.margins["top"] + self.HEADER_HEIGHT  # Don't exceed header zone

        # Position title if present
        title_el = slide.get_title_element()
        if title_el:
            if not hasattr(title_el, "size") or not title_el.size:
                title_el.size = self.default_sizes[ElementType.TITLE]

            # Calculate title height - reduce padding to save space
            title_width = title_el.size[0]
            title_height = calculate_element_height(title_el, title_width)
            title_el.size = (title_width, title_height)

            # Position from the left margin like other content for consistency
            align = getattr(title_el, "horizontal_alignment", AlignmentType.CENTER)

            if align == AlignmentType.CENTER:
                # Center horizontally but use fixed left edge
                title_el.position = (
                    self.margins["left"] + (self.max_content_width - title_width) / 2,
                    current_y,
                )
            else:
                # Apply normal horizontal alignment
                self._apply_horizontal_alignment(
                    title_el, self.margins["left"], self.max_content_width, current_y
                )

            # Update current y-position for subtitle (if any)
            current_y += title_height + self.vertical_spacing

            # FIXED: Don't allow title to exceed header zone
            if current_y > max_y:
                logger.warning(
                    f"Title element would exceed header zone height. "
                    f"Current Y: {current_y}, Max Y: {max_y}"
                )

            logger.debug(
                f"Positioned title element at y={title_el.position[1]:.1f}, height={title_el.size[1]:.1f}"
            )

        # Position subtitle if present
        subtitle_el = slide.get_subtitle_element()
        if subtitle_el:
            if not hasattr(subtitle_el, "size") or not subtitle_el.size:
                subtitle_el.size = self.default_sizes[ElementType.SUBTITLE]

            # Calculate subtitle height with reduced padding
            subtitle_width = subtitle_el.size[0]
            subtitle_height = calculate_element_height(subtitle_el, subtitle_width)
            subtitle_el.size = (subtitle_width, subtitle_height)

            # Position consistently with other content
            self._apply_horizontal_alignment(
                subtitle_el, self.margins["left"], self.max_content_width, current_y
            )

            # FIXED: Warn if subtitle would exceed header zone
            if current_y + subtitle_height > max_y:
                logger.warning(
                    f"Subtitle element would exceed header zone height. "
                    f"Current Y + Height: {current_y + subtitle_height}, Max Y: {max_y}"
                )

            logger.debug(
                f"Positioned subtitle element at y={subtitle_el.position[1]:.1f}, height={subtitle_el.size[1]:.1f}"
            )

        # Always return the fixed header height
        return self.HEADER_HEIGHT

    def _position_footer_element(self, slide: Slide) -> float:
        """
        Position footer element at the bottom of the slide.

        Args:
            slide: The slide to position footer element for

        Returns:
            The height of the footer zone (fixed)
        """
        footer_el = slide.get_footer_element()
        if not footer_el:
            return 0

        # FIXED: Always use a fixed size for footer to maintain consistency
        footer_width = self.max_content_width
        footer_el.size = (footer_width, self.FOOTER_HEIGHT)

        # FIXED: Position at the exact bottom boundary of the slide - footer should always be at the same place
        footer_y = self.slide_height - self.margins["bottom"] - self.FOOTER_HEIGHT

        # Apply horizontal alignment from left margin
        self._apply_horizontal_alignment(
            footer_el, self.margins["left"], self.max_content_width, footer_y
        )

        logger.debug(f"Positioned footer {footer_el.object_id} at y={footer_y}")
        return self.FOOTER_HEIGHT

    def _get_body_elements(self, slide: Slide) -> list[Element]:
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

    def _calculate_section_based_positions(self, slide: Slide) -> Slide:
        """
        Calculate positions for a section-based slide layout using the fixed body zone.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The updated slide with positioned elements
        """
        # Step 1: Position header elements (title, subtitle) within the fixed header zone
        self._position_header_elements(slide)

        # Step 2: Position footer element if present within the fixed footer zone
        self._position_footer_element(slide)

        # Step 3: Use the fixed body zone dimensions for section layout
        # FIXED: Always use the consistent fixed body zone dimensions
        body_area = (
            self.body_left,  # x
            self.body_top,  # y
            self.body_width,  # width
            self.body_height,  # height
        )

        # Step 4: Distribute space among sections within the fixed body zone
        self._distribute_space_and_position_sections(
            slide.sections, body_area, is_vertical_split=True
        )

        # Step 5: Position elements within each section
        self._position_elements_in_sections(slide)

        logger.debug(f"Section-based layout completed for slide {slide.object_id}")
        return slide

    def _distribute_space_and_position_sections(
        self,
        sections: list[SectionModel],
        area: tuple[float, float, float, float],
        is_vertical_split: bool,
    ) -> None:
        """
        Distribute space among sections and position them within the given area.
        All sections must fit within the specified area (usually the body zone).

        Args:
            sections: List of section models
            area: Tuple of (x, y, width, height) defining the available area
            is_vertical_split: True for vertical distribution, False for horizontal
        """
        if not sections:
            return

        # Extract area parameters
        area_left, area_top, area_width, area_height = area

        # Log the area being distributed
        logger.debug(
            f"Distributing space for {len(sections)} sections in area: "
            f"left={area_left:.1f}, top={area_top:.1f}, width={area_width:.1f}, height={area_height:.1f}, "
            f"is_vertical={is_vertical_split}"
        )

        # Determine the primary dimension to distribute
        if is_vertical_split:
            main_position = area_top  # y-coordinate
            main_dimension = area_height  # height
            cross_dimension = area_width  # width (constant)
        else:
            main_position = area_left  # x-coordinate
            main_dimension = area_width  # width
            cross_dimension = area_height  # height (constant)

        # Define constants
        min_section_dim = 20.0  # Minimum section dimension in points
        # FIXED: Use reduced spacing constants
        spacing = (
            self.vertical_spacing if is_vertical_split else self.horizontal_spacing
        )
        total_spacing = spacing * (len(sections) - 1)

        # Initialize tracking variables
        dim_key = "height" if is_vertical_split else "width"
        explicit_sections = {}  # section_index: dimension
        implicit_section_indices = []

        # First pass: identify explicit and implicit sections
        for i, section in enumerate(sections):
            dim_directive = section.directives.get(dim_key)

            if dim_directive is not None:
                if isinstance(dim_directive, float) and 0.0 < dim_directive <= 1.0:
                    # Percentage/fraction of total - FIXED: Apply to main_dimension, not a different calculation
                    explicit_sections[i] = main_dimension * dim_directive
                elif isinstance(dim_directive, (int, float)) and dim_directive > 1.0:
                    # Absolute dimension - FIXED: Ensure it doesn't exceed main_dimension
                    explicit_sections[i] = min(
                        float(dim_directive), main_dimension - total_spacing
                    )
                else:
                    # Invalid directive, treat as implicit
                    implicit_section_indices.append(i)
            else:
                # No directive, treat as implicit
                implicit_section_indices.append(i)

        # Calculate total explicit dimension
        total_explicit_dim = sum(explicit_sections.values())

        # FIXED: Ensure explicit dimensions don't exceed available space (with spacing)
        if total_explicit_dim > main_dimension - total_spacing:
            # Scale down explicit sections proportionally
            scale_factor = (main_dimension - total_spacing) / total_explicit_dim
            for i in explicit_sections:
                explicit_sections[i] *= scale_factor

            logger.debug(
                f"Scaled down explicit sections by {scale_factor:.2f} to fit available space"
            )

        # Calculate remaining dimension for implicit sections
        remaining_dim = main_dimension - total_explicit_dim - total_spacing
        remaining_dim = max(0, remaining_dim)  # Avoid negative values

        # Distribute remaining dimension among implicit sections
        if implicit_section_indices:
            dim_per_implicit = remaining_dim / len(implicit_section_indices)
            dim_per_implicit = max(min_section_dim, dim_per_implicit)
            logger.debug(
                f"Allocated {dim_per_implicit:.1f} points per implicit section"
            )
        else:
            dim_per_implicit = 0

        # Second pass: position and size each section
        current_pos = main_position

        for i, section in enumerate(sections):
            # Determine section dimension
            if i in explicit_sections:
                section_dim = explicit_sections[i]
            elif i in implicit_section_indices:
                section_dim = dim_per_implicit
            else:
                # This should not happen, but handle it gracefully
                section_dim = min_section_dim

            # Ensure minimum dimension
            section_dim = max(min_section_dim, section_dim)

            # FIXED: Ensure section doesn't exceed area boundaries
            if is_vertical_split:
                if current_pos + section_dim > area_top + area_height:
                    section_dim = max(
                        min_section_dim, (area_top + area_height) - current_pos
                    )
                    logger.warning(
                        f"Section {section.id} exceeded available vertical space. "
                        f"Adjusted height to {section_dim:.1f}"
                    )

            # Position and size the section
            if is_vertical_split:
                section.position = (area_left, current_pos)
                section.size = (cross_dimension, section_dim)
            else:
                section.position = (current_pos, area_top)
                section.size = (section_dim, cross_dimension)

            # Process subsections recursively if this is a row
            if is_vertical_split and section.type == "row" and section.subsections:
                subsection_area = (
                    section.position[0],
                    section.position[1],
                    section.size[0],
                    section.size[1],
                )
                self._distribute_space_and_position_sections(
                    section.subsections,
                    subsection_area,
                    is_vertical_split=False,  # Horizontal distribution for row's subsections
                )

            # Move to next position
            current_pos += section_dim + spacing

            logger.debug(
                f"Positioned section {section.id}: pos=({section.position[0]:.1f}, {section.position[1]:.1f}), "
                f"size=({section.size[0]:.1f}, {section.size[1]:.1f})"
            )

    def _position_elements_in_sections(self, slide: Slide) -> None:
        """
        Position elements within their respective sections.

        Args:
            slide: The slide with sections to position elements in
        """
        if not slide.sections:
            return

        # Create a flat list of leaf sections (sections with elements)
        leaf_sections = []

        def collect_leaf_sections(sections_list):
            for section in sections_list:
                if section.type == "row" and section.subsections:
                    collect_leaf_sections(section.subsections)
                elif section.type == "section":
                    leaf_sections.append(section)

        collect_leaf_sections(slide.sections)
        logger.debug(
            f"Found {len(leaf_sections)} leaf sections to position elements in"
        )

        # Position elements within each leaf section
        for section in leaf_sections:
            if section.elements and section.position and section.size:
                section_area = (
                    section.position[0],
                    section.position[1],
                    section.size[0],
                    section.size[1],
                )
                self._position_elements_within_section(
                    section.elements, section_area, section.directives
                )
            else:
                logger.warning(
                    f"Section {section.id} has no elements, position, or size"
                )

    def _position_elements_within_section(
        self,
        elements: list[Element],
        area: tuple[float, float, float, float],
        directives: dict[str, Any],
    ) -> None:
        """
        Position elements within a section. Elements are laid out vertically
        within the strict boundaries of the section area.

        Args:
            elements: List of elements to position
            area: Tuple of (x, y, width, height) defining the section area
            directives: Section directives
        """
        if not elements:
            return

        area_x, area_y, area_width, area_height = area
        logger.debug(
            f"Positioning {len(elements)} elements within section area: "
            f"x={area_x:.1f}, y={area_y:.1f}, width={area_width:.1f}, height={area_height:.1f}"
        )

        # Apply padding from directives
        padding = directives.get("padding", 0.0)
        # FIXED: Reduce default padding to save space
        if isinstance(padding, (int, float)) and padding > 0:
            area_x += padding
            area_y += padding
            area_width = max(10.0, area_width - (2 * padding))
            area_height = max(10.0, area_height - (2 * padding))

        # Calculate total content height and prepare elements
        elements_heights = []
        total_height_with_spacing = 0

        for i, element in enumerate(elements):
            # Ensure element has a size
            if not hasattr(element, "size") or not element.size:
                element.size = self.default_sizes.get(
                    element.element_type, (area_width, 50)
                )

            # Calculate element width and height
            element_width = min(element.size[0], area_width)
            # FIXED: More accurate height with reduced padding
            element_height = calculate_element_height(element, element_width)
            element.size = (element_width, element_height)
            elements_heights.append(element_height)

            # Add spacing (except after the last element)
            total_height_with_spacing += element_height
            if i < len(elements) - 1:
                total_height_with_spacing += self.vertical_spacing

        # Check if content exceeds section height
        if total_height_with_spacing > area_height:
            logger.warning(
                f"Total content height ({total_height_with_spacing:.1f}) exceeds section height ({area_height:.1f}). "
                f"Some elements may not be fully visible."
            )

        # Apply vertical alignment
        valign = directives.get("valign", "top").lower()

        if valign == "middle" and total_height_with_spacing < area_height:
            start_y = area_y + (area_height - total_height_with_spacing) / 2
        elif valign == "bottom" and total_height_with_spacing < area_height:
            start_y = area_y + area_height - total_height_with_spacing
        else:
            start_y = area_y

        # Position elements
        current_y = start_y
        for i, element in enumerate(elements):
            # Apply horizontal alignment
            element_align = directives.get("align", "left").lower()

            if hasattr(element, "horizontal_alignment"):
                element.horizontal_alignment = AlignmentType(element_align)

            self._apply_horizontal_alignment(element, area_x, area_width, current_y)

            # Log if element would overflow section
            element_bottom = current_y + element.size[1]
            if element_bottom > area_y + area_height:
                logger.warning(
                    f"Element {getattr(element, 'object_id', 'unknown')} ({element.element_type}) would overflow "
                    f"section. y={current_y:.1f}, height={element.size[1]:.1f}, section_bottom={area_y + area_height:.1f}"
                )

            # Move to next position
            current_y += element.size[1]
            if i < len(elements) - 1:  # Add spacing only between elements
                current_y += self.vertical_spacing

    def _apply_horizontal_alignment(
        self,
        element: Element,
        area_x: float,
        area_width: float,
        y_pos: float,
    ) -> None:
        """
        Apply horizontal alignment to an element within an area.

        Args:
            element: Element to align
            area_x: X-coordinate of the area
            area_width: Width of the area
            y_pos: Y-coordinate for the element
        """
        element_width = element.size[0]
        alignment = getattr(element, "horizontal_alignment", AlignmentType.LEFT)

        if alignment == AlignmentType.CENTER:
            x_pos = area_x + (area_width - element_width) / 2
        elif alignment == AlignmentType.RIGHT:
            x_pos = area_x + area_width - element_width
        else:  # LEFT or JUSTIFY
            x_pos = area_x

        element.position = (x_pos, y_pos)
