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
    VerticalAlignmentType,
)
from markdowndeck.models import Section as SectionModel

logger = logging.getLogger(__name__)


class PositionCalculator:
    """Calculates positions for slide elements using a zone-based layout model."""

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

        # Spacing constants
        self.vertical_spacing = 15.0
        self.horizontal_spacing = 15.0

        # Content area dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # Zone constants
        self.HEADER_MAX_HEIGHT = 100.0  # Maximum height for header zone
        self.FOOTER_HEIGHT = 30.0  # Fixed height for footer zone

        # Default element sizes (width, height) in points
        self.default_sizes = {
            ElementType.TITLE: (self.max_content_width * 0.9, 50),
            ElementType.SUBTITLE: (self.max_content_width * 0.85, 40),
            ElementType.TEXT: (self.max_content_width, 70),
            ElementType.BULLET_LIST: (self.max_content_width, 150),
            ElementType.ORDERED_LIST: (self.max_content_width, 150),
            ElementType.IMAGE: (
                self.max_content_width * 0.6,
                self.max_content_height * 0.5,
            ),
            ElementType.TABLE: (self.max_content_width, 150),
            ElementType.CODE: (self.max_content_width, 120),
            ElementType.QUOTE: (self.max_content_width * 0.9, 80),
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
        Calculate positions using a zone-based layout model (header, body, footer).
        """
        # Step 1: Position header elements (title, subtitle)
        header_height = self._position_header_elements(slide)

        # Step 2: Position footer element if present
        footer_height = self._position_footer_element(slide)

        # Step 3: Calculate body zone dimensions - clear boundary between zones
        body_top = self.margins["top"] + header_height
        body_bottom = self.slide_height - self.margins["bottom"] - footer_height
        body_height = max(10.0, body_bottom - body_top)  # Ensure minimum body height

        # Step 4: Position body elements within the body zone
        body_elements = self._get_body_elements(slide)

        # MODIFIED: Group elements by their section for better spacing
        current_y = body_top
        for element in body_elements:
            # Ensure element has a valid size
            if not hasattr(element, "size") or not element.size:
                element.size = self.default_sizes.get(
                    element.element_type, (self.max_content_width, 50)
                )

            # Calculate element width based on directives
            element_width = self.max_content_width
            if hasattr(element, "directives") and "width" in element.directives:
                width_dir = element.directives["width"]
                if isinstance(width_dir, float) and 0.0 < width_dir <= 1.0:
                    element_width = self.max_content_width * width_dir
                elif isinstance(width_dir, (int, float)) and width_dir > 1.0:
                    element_width = min(width_dir, self.max_content_width)

            # Calculate appropriate height
            element_height = calculate_element_height(element, element_width)
            element.size = (element_width, element_height)

            # Position element using horizontal alignment
            self._apply_horizontal_alignment(
                element, self.margins["left"], self.max_content_width, current_y
            )

            # MODIFIED: Add special handling for spacing after heading elements
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

        return slide

    def _position_header_elements(self, slide: Slide) -> float:
        """
        Position title and subtitle elements in the header zone.

        Args:
            slide: The slide to position header elements for

        Returns:
            The total height of the header zone
        """
        current_y = self.margins["top"]
        header_height = 0

        # Position title if present
        title_el = slide.get_title_element()
        if title_el:
            if not hasattr(title_el, "size") or not title_el.size:
                title_el.size = self.default_sizes[ElementType.TITLE]

            # Calculate title height
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

            # Update current y-position and header height
            current_y += title_height + self.vertical_spacing
            header_height += title_height + self.vertical_spacing

        # Position subtitle if present
        subtitle_el = slide.get_subtitle_element()
        if subtitle_el:
            if not hasattr(subtitle_el, "size") or not subtitle_el.size:
                subtitle_el.size = self.default_sizes[ElementType.SUBTITLE]

            # Calculate subtitle height
            subtitle_width = subtitle_el.size[0]
            subtitle_height = calculate_element_height(subtitle_el, subtitle_width)
            subtitle_el.size = (subtitle_width, subtitle_height)

            # Position consistently with other content
            self._apply_horizontal_alignment(
                subtitle_el, self.margins["left"], self.max_content_width, current_y
            )

            # Update header height
            header_height += subtitle_height + self.vertical_spacing

        # Apply maximum constraint to header height
        header_height = min(header_height, self.HEADER_MAX_HEIGHT)

        return header_height

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

        # Apply fixed size to footer
        footer_width = self.max_content_width
        footer_el.size = (footer_width, self.FOOTER_HEIGHT)

        # Position at bottom of slide
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
        Calculate positions for a section-based slide layout.

        Args:
            slide: The slide to calculate positions for

        Returns:
            The updated slide with positioned elements
        """
        # Step 1: Position header elements (title, subtitle)
        header_height = self._position_header_elements(slide)

        # Step 2: Position footer element if present
        footer_height = self._position_footer_element(slide)

        # Step 3: Calculate body zone dimensions
        body_top = self.margins["top"] + header_height
        body_height = (
            self.slide_height - self.margins["bottom"] - footer_height - body_top
        )

        body_area = (
            self.margins["left"],  # x
            body_top,  # y
            self.max_content_width,  # width
            body_height,  # height
        )

        # Step 4: Distribute space among sections within the body zone
        self._distribute_space_and_position_sections(
            slide.sections, body_area, is_vertical_split=True
        )

        # Step 5: Position elements within each section
        self._position_elements_in_sections(slide)

        return slide

    def _distribute_space_and_position_sections(
        self,
        sections: list[SectionModel],
        area: tuple[float, float, float, float],
        is_vertical_split: bool,
    ) -> None:
        """
        Distribute space among sections and position them within the given area.

        Args:
            sections: List of section models
            area: Tuple of (x, y, width, height) defining the available area
            is_vertical_split: True for vertical distribution, False for horizontal
        """
        if not sections:
            return

        # Extract area parameters
        area_left, area_top, area_width, area_height = area

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
                    # Percentage/fraction of total
                    explicit_sections[i] = main_dimension * dim_directive
                elif isinstance(dim_directive, (int, float)) and dim_directive > 1.0:
                    # Absolute dimension
                    explicit_sections[i] = float(dim_directive)
                else:
                    # Invalid directive, treat as implicit
                    implicit_section_indices.append(i)
            else:
                # No directive, treat as implicit
                implicit_section_indices.append(i)

        # Calculate total explicit dimension
        total_explicit_dim = sum(explicit_sections.values())

        # Ensure explicit dimensions don't exceed available space (with spacing)
        if total_explicit_dim > main_dimension - total_spacing:
            # Scale down explicit sections proportionally
            scale_factor = (main_dimension - total_spacing) / total_explicit_dim
            for i in explicit_sections:
                explicit_sections[i] *= scale_factor

        # Calculate remaining dimension for implicit sections
        remaining_dim = main_dimension - total_explicit_dim - total_spacing

        # Distribute remaining dimension among implicit sections
        if implicit_section_indices:
            dim_per_implicit = remaining_dim / len(implicit_section_indices)
            dim_per_implicit = max(min_section_dim, dim_per_implicit)
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
                f"Positioned section {section.id}: pos={section.position}, size={section.size}"
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

    def _position_elements_within_section(
        self,
        elements: list[Element],
        area: tuple[float, float, float, float],
        directives: dict[str, Any],
    ) -> None:
        """
        Position elements within a section.

        Args:
            elements: List of elements to position
            area: Tuple of (x, y, width, height) defining the section area
            directives: Section directives
        """
        if not elements:
            return

        area_x, area_y, area_width, area_height = area

        # Apply padding from directives
        padding = directives.get("padding", 0.0)
        if isinstance(padding, (int, float)) and padding > 0:
            area_x += padding
            area_y += padding
            area_width = max(10.0, area_width - (2 * padding))
            area_height = max(10.0, area_height - (2 * padding))

        # Calculate total content height and prepare elements
        elements_heights = []
        for element in elements:
            # Ensure element has a size
            if not hasattr(element, "size") or not element.size:
                element.size = self.default_sizes.get(
                    element.element_type, (area_width, 50)
                )

            # Calculate element width and height
            element_width = min(element.size[0], area_width)
            element_height = calculate_element_height(element, element_width)
            element.size = (element_width, element_height)
            elements_heights.append(element_height)

        # Calculate total content height with spacing
        total_spacing = self.vertical_spacing * (len(elements) - 1)
        total_content_height = sum(elements_heights) + total_spacing

        # Apply vertical alignment
        valign = directives.get("valign", "top").lower()

        if valign == "middle" and total_content_height < area_height:
            start_y = area_y + (area_height - total_content_height) / 2
        elif valign == "bottom" and total_content_height < area_height:
            start_y = area_y + area_height - total_content_height
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

            # Check if element would overflow section
            if current_y + element.size[1] > area_y + area_height:
                logger.warning(
                    f"Element {element.object_id} ({element.element_type}) would overflow "
                    f"section. y={current_y}, height={element.size[1]}, section_bottom={area_y + area_height}"
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
