"""Refactored base position calculator with flexible body area calculation."""

import logging

from markdowndeck.layout.constants import (
    DEFAULT_SLIDE_HEIGHT,
    DEFAULT_SLIDE_WIDTH,
    HORIZONTAL_SPACING,
    VERTICAL_SPACING,
)
from markdowndeck.models import ElementType, Slide
from markdowndeck.models.slide import Section

logger = logging.getLogger(__name__)


class PositionCalculator:
    """
    Unified layout calculator implementing flexible body area calculation.
    """

    def __init__(
        self,
        slide_width: float = None,
        slide_height: float = None,
        margins: dict = None,
    ):
        self.slide_width = slide_width or DEFAULT_SLIDE_WIDTH
        self.slide_height = slide_height or DEFAULT_SLIDE_HEIGHT
        self.margins = margins or {"top": 0.0, "right": 0.0, "bottom": 0.0, "left": 0.0}
        self.max_content_width = (
            self.slide_width - self.margins["left"] - self.margins["right"]
        )
        self.max_content_height = (
            self.slide_height - self.margins["top"] - self.margins["bottom"]
        )
        self.HORIZONTAL_SPACING = HORIZONTAL_SPACING
        self.VERTICAL_SPACING = VERTICAL_SPACING
        self.body_left = self.margins["left"]
        self.body_width = self.max_content_width
        self.body_top = self.margins["top"]
        self.body_height = self.max_content_height

    def calculate_positions(self, slide: Slide) -> Slide:
        """Calculate positions for all elements and sections in a slide."""
        # CRITICAL FIX: Process meta-elements for ALL slides, including continuation slides
        header_height = self._position_header_elements(slide)
        footer_height = self._position_footer_elements(slide)
        self.body_top = self.margins["top"] + header_height
        self.body_height = (
            self.slide_height - self.margins["bottom"] - footer_height - self.body_top
        )

        # REFACTORED: The layout process now starts from the single root_section.
        slide.root_section = self._ensure_section_based_layout(slide)

        from markdowndeck.layout.calculator.section_layout import (
            calculate_section_based_positions,
        )

        final_slide = calculate_section_based_positions(self, slide)

        # Populate renderable_elements with positioned meta-elements.
        # This must happen for ALL slides, not just the first one
        meta_elements = []
        if slide.get_title_element():
            title_elem = slide.get_title_element()
            if title_elem.position:
                meta_elements.append(title_elem)
        if slide.get_subtitle_element():
            subtitle_elem = slide.get_subtitle_element()
            if subtitle_elem.position:
                meta_elements.append(subtitle_elem)
        if slide.get_footer_element():
            footer_elem = slide.get_footer_element()
            if footer_elem.position:
                meta_elements.append(footer_elem)

        final_slide.renderable_elements.extend(meta_elements)

        # Clear the original element inventory list as it's now stale.
        final_slide.elements = []
        return final_slide

    def calculate_element_height_with_proactive_scaling(
        self, element, available_width: float, available_height: float = 0
    ) -> float:
        """Calculate element height with proactive image scaling applied."""
        if element.element_type == ElementType.IMAGE:
            from markdowndeck.layout.metrics.image import calculate_image_element_height

            return calculate_image_element_height(
                element, available_width, available_height
            )
        from markdowndeck.layout.metrics import calculate_element_height

        return calculate_element_height(element, available_width)

    def _ensure_section_based_layout(self, slide: Slide) -> Section:
        """
        Ensures a root section exists for the slide's body content.
        REFACTORED: To work with slide.root_section instead of slide.sections.
        """
        if slide.root_section:
            return slide.root_section

        # If no root_section, create one from the body elements.
        logger.warning(
            f"Slide {slide.object_id} has no root_section. Creating a default one."
        )
        body_elements = self.get_body_elements(slide)
        return Section(
            id="root", children=body_elements, position=(self.body_left, self.body_top)
        )

    def _position_header_elements(self, slide: Slide) -> float:
        total_height = 0
        title = slide.get_title_element()
        if title:
            from markdowndeck.layout.metrics import calculate_element_height

            title_height = calculate_element_height(title, self.max_content_width)
            title.size = (self.max_content_width, title_height)
            title.position = (self.margins["left"], self.margins["top"])
            total_height += title_height

        subtitle = slide.get_subtitle_element()
        if subtitle:
            from markdowndeck.layout.metrics import calculate_element_height

            subtitle_height = calculate_element_height(subtitle, self.max_content_width)
            subtitle.size = (self.max_content_width, subtitle_height)
            subtitle_y = self.margins["top"] + total_height
            subtitle.position = (self.margins["left"], subtitle_y)
            total_height += subtitle_height

        return total_height

    def _position_footer_elements(self, slide: Slide) -> float:
        total_height = 0
        footer = slide.get_footer_element()
        if footer:
            from markdowndeck.layout.metrics import calculate_element_height

            footer_height = calculate_element_height(footer, self.max_content_width)
            footer.size = (self.max_content_width, footer_height)
            footer_top = self.slide_height - self.margins["bottom"] - footer_height
            footer.position = (self.margins["left"], footer_top)
            total_height += footer_height
        return total_height

    def _calculate_element_width(self, element, container_width: float) -> float:
        return container_width

    def get_body_elements(self, slide: Slide) -> list:
        return slide.get_content_elements()

    def get_body_zone_area(self) -> tuple[float, float, float, float]:
        return (self.body_left, self.body_top, self.body_width, self.body_height)
