"""Base position calculator class and core functionality."""

import logging
from copy import deepcopy

from markdowndeck.layout.calculator.element_layout import (
    position_footer_element,
    position_header_elements,
)
from markdowndeck.layout.calculator.section_layout import (
    calculate_section_based_positions,
)
from markdowndeck.layout.calculator.zone_layout import (
    calculate_zone_based_positions,
)
from markdowndeck.layout.constants import (
    FOOTER_HEIGHT,
    HEADER_HEIGHT,
    HORIZONTAL_SPACING,
    IMAGE_WIDTH_FRACTION,
    QUOTE_WIDTH_FRACTION,
    SUBTITLE_WIDTH_FRACTION,
    TITLE_WIDTH_FRACTION,
    VERTICAL_SPACING,
)
from markdowndeck.models import (
    ElementType,
    Slide,
)

logger = logging.getLogger(__name__)


class PositionCalculator:
    """Calculates positions for slide elements using a zone-based layout model with a fixed body zone."""

    def __init__(self, slide_width: float, slide_height: float, margins: dict[str, float]):
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
        self.vertical_spacing = VERTICAL_SPACING
        self.horizontal_spacing = HORIZONTAL_SPACING

        # Content area dimensions
        self.max_content_width = self.slide_width - self.margins["left"] - self.margins["right"]
        self.max_content_height = self.slide_height - self.margins["top"] - self.margins["bottom"]

        # Fixed zone dimensions
        self.HEADER_HEIGHT = HEADER_HEIGHT
        self.FOOTER_HEIGHT = FOOTER_HEIGHT

        # Calculate fixed body zone dimensions
        self.body_top = self.margins["top"] + self.HEADER_HEIGHT
        self.body_left = self.margins["left"]
        self.body_width = self.max_content_width
        self.body_height = (
            self.slide_height - self.body_top - self.FOOTER_HEIGHT - self.margins["bottom"]
        )
        self.body_bottom = self.body_top + self.body_height

        # Log the fixed body zone dimensions for debugging
        logger.debug(
            f"Fixed body zone: top={self.body_top}, left={self.body_left}, "
            f"width={self.body_width}, height={self.body_height}, bottom={self.body_bottom}"
        )

        # Default element sizes (width, height) in points
        self.default_sizes = {
            ElementType.TITLE: (self.max_content_width * TITLE_WIDTH_FRACTION, 40),
            ElementType.SUBTITLE: (
                self.max_content_width * SUBTITLE_WIDTH_FRACTION,
                35,
            ),
            ElementType.TEXT: (self.max_content_width, 60),
            ElementType.BULLET_LIST: (self.max_content_width, 130),
            ElementType.ORDERED_LIST: (self.max_content_width, 130),
            ElementType.IMAGE: (
                self.max_content_width * IMAGE_WIDTH_FRACTION,
                self.max_content_height * 0.4,
            ),
            ElementType.TABLE: (self.max_content_width, 130),
            ElementType.CODE: (self.max_content_width, 100),
            ElementType.QUOTE: (self.max_content_width * QUOTE_WIDTH_FRACTION, 70),
            ElementType.FOOTER: (self.max_content_width, self.FOOTER_HEIGHT),
        }

    # Add methods as instance methods that delegate to the imported functions
    def _position_header_elements(self, slide):
        """Position header elements on the slide."""
        return position_header_elements(self, slide)

    def _position_footer_element(self, slide):
        """Position footer element on the slide."""
        return position_footer_element(self, slide)

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
            logger.debug(f"Using section-based layout for slide {updated_slide.object_id}")
            return calculate_section_based_positions(self, updated_slide)

        logger.debug(f"Using zone-based layout for slide {updated_slide.object_id}")
        return calculate_zone_based_positions(self, updated_slide)

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
