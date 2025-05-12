"""Base position calculator class and core functionality."""

import logging
from copy import deepcopy

from markdowndeck.models import (
    Element,
    ElementType,
    Slide,
)

from markdowndeck.layout.calculator.zone_layout import (
    calculate_zone_based_positions,
)
from markdowndeck.layout.calculator.section_layout import (
    calculate_section_based_positions,
)
from markdowndeck.layout.calculator.element_utils import (
    apply_horizontal_alignment,
    mark_related_elements,
)

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

        # Optimized spacing constants
        self.vertical_spacing = 8.0  # Further reduced from 10.0
        self.horizontal_spacing = 8.0  # Further reduced from 10.0

        # Content area dimensions
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )

        # Fixed zone dimensions
        self.HEADER_HEIGHT = 90.0  # Reduced from 100.0 to address spacing issues
        self.FOOTER_HEIGHT = 30.0

        # Calculate fixed body zone dimensions
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

        # Default element sizes (width, height) in points - optimized for space
        self.default_sizes = {
            ElementType.TITLE: (self.max_content_width * 0.9, 38),
            ElementType.SUBTITLE: (self.max_content_width * 0.85, 32),
            ElementType.TEXT: (self.max_content_width, 55),
            ElementType.BULLET_LIST: (self.max_content_width, 120),
            ElementType.ORDERED_LIST: (self.max_content_width, 120),
            ElementType.IMAGE: (
                self.max_content_width * 0.6,
                self.max_content_height * 0.4,
            ),
            ElementType.TABLE: (self.max_content_width, 120),
            ElementType.CODE: (self.max_content_width, 90),
            ElementType.QUOTE: (self.max_content_width * 0.9, 65),
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
            return calculate_section_based_positions(self, updated_slide)

        logger.debug(f"Using zone-based layout for slide {updated_slide.object_id}")
        return calculate_zone_based_positions(self, updated_slide)

    def _position_header_elements(self, slide: Slide) -> float:
        """
        Position title and subtitle elements in the header zone.

        Args:
            slide: The slide to position header elements for

        Returns:
            The total height of the header zone
        """
        from markdowndeck.models import AlignmentType
        from markdowndeck.layout.metrics import calculate_element_height

        # Always use fixed header zone - more consistent positioning
        current_y = self.margins["top"]
        max_y = self.margins["top"] + self.HEADER_HEIGHT  # Don't exceed header zone

        # Position title if present
        title_el = slide.get_title_element()
        if title_el:
            if not hasattr(title_el, "size") or not title_el.size:
                title_el.size = self.default_sizes[ElementType.TITLE]

            # Calculate title height - reduced padding
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
                apply_horizontal_alignment(
                    title_el, self.margins["left"], self.max_content_width, current_y
                )

            # Update current y-position for subtitle (if any)
            current_y += title_height + self.vertical_spacing * 0.8  # Reduced spacing

            # Don't allow title to exceed header zone
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
            apply_horizontal_alignment(
                subtitle_el, self.margins["left"], self.max_content_width, current_y
            )

            # Warn if subtitle would exceed header zone
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

        # Always use a fixed size for footer to maintain consistency
        footer_width = self.max_content_width
        footer_el.size = (footer_width, self.FOOTER_HEIGHT)

        # Position at the exact bottom boundary of the slide
        footer_y = self.slide_height - self.margins["bottom"] - self.FOOTER_HEIGHT

        # Apply horizontal alignment from left margin
        apply_horizontal_alignment(
            footer_el, self.margins["left"], self.max_content_width, footer_y
        )

        logger.debug(f"Positioned footer {footer_el.object_id} at y={footer_y}")
        return self.FOOTER_HEIGHT

    def get_body_elements(self, slide: Slide) -> list[Element]:
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
