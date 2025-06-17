import logging

from markdowndeck.layout.constants import (
    DEFAULT_SLIDE_HEIGHT,
    DEFAULT_SLIDE_WIDTH,
    HORIZONTAL_SPACING,
    VERTICAL_SPACING,
)
from markdowndeck.models import ElementType, Slide

logger = logging.getLogger(__name__)


class PositionCalculator:
    """
    Unified layout calculator implementing the new two-pass algorithm.
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
        """
        Calculate positions for all elements and sections in a slide using the new two-pass algorithm.
        """
        # Phase 1: Position meta-elements (title, subtitle, footer)
        header_height = self._position_header_elements(slide)
        footer_height = self._position_footer_elements(slide)

        # Calculate body area after accounting for meta-elements
        self.body_top = self.margins["top"] + header_height
        self.body_height = (
            self.slide_height - self.margins["bottom"] - footer_height - self.body_top
        )
        body_area = (self.body_left, self.body_top, self.body_width, self.body_height)

        # Phase 2: Layout body content using the new two-pass algorithm
        if slide.root_section:
            from markdowndeck.layout.calculator.section_layout import (
                calculate_recursive_layout,
            )

            calculate_recursive_layout(self, slide.root_section, body_area)

        # Phase 3: Finalize renderable elements list
        meta_elements = []

        # Add positioned meta-elements with proper directive merging
        if slide.get_title_element() and slide.get_title_element().position:
            title_element = slide.get_title_element()
            # REFACTORED: Use `slide.base_directives` for meta-elements per PRINCIPLES.md Sec 8.2
            merged_directives = self._merge_directives_with_precedence(
                slide.base_directives,
                title_element.directives,
                getattr(slide, "title_directives", {}),
            )
            title_element.directives = merged_directives
            meta_elements.append(title_element)

        if slide.get_subtitle_element() and slide.get_subtitle_element().position:
            subtitle_element = slide.get_subtitle_element()
            # REFACTORED: Use `slide.base_directives` for meta-elements per PRINCIPLES.md Sec 8.2
            merged_directives = self._merge_directives_with_precedence(
                slide.base_directives,
                subtitle_element.directives,
                getattr(slide, "subtitle_directives", {}),
            )
            subtitle_element.directives = merged_directives
            meta_elements.append(subtitle_element)

        if slide.get_footer_element() and slide.get_footer_element().position:
            footer_element = slide.get_footer_element()
            # REFACTORED: Use `slide.base_directives` for meta-elements per PRINCIPLES.md Sec 8.2
            merged_directives = self._merge_directives_with_precedence(
                slide.base_directives,
                footer_element.directives,
                getattr(slide, "footer_directives", {}),
            )
            footer_element.directives = merged_directives
            meta_elements.append(footer_element)

        slide.renderable_elements.extend(meta_elements)
        slide.elements = []  # Clear the inventory list as per spec

        return slide

    def calculate_element_height_with_proactive_scaling(
        self, element, available_width: float, available_height: float = 0
    ) -> float:
        """
        Calculate element height with proactive image scaling applied.

        ENHANCED: Now properly handles both width and height constraints for images,
        implementing Law #2 (Proactive Image Scaling) correctly.
        """
        if element.element_type == ElementType.IMAGE:
            from markdowndeck.layout.metrics.image import calculate_image_display_size

            _, height = calculate_image_display_size(
                element, available_width, available_height
            )
            logger.debug(
                f"Image element proactively scaled to {height:.1f}px height "
                f"with constraints: width={available_width:.1f}, height={available_height:.1f}"
            )
            return height

        # For non-image elements, use standard height calculation
        from markdowndeck.layout.metrics import calculate_element_height

        return calculate_element_height(element, available_width)

    def _position_header_elements(self, slide: Slide) -> float:
        """Position title and subtitle elements, returning total height used."""
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
        """Position footer element, returning total height used."""
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
        """
        Calculate element width, respecting zero-size elements and width directives.
        """
        # If an element has its size explicitly set to (0, 0), its width is 0
        if hasattr(element, "size") and element.size == (0, 0):
            return 0.0

        # Check for width directive on the element
        if hasattr(element, "directives") and "width" in element.directives:
            width_directive = element.directives["width"]
            try:
                if isinstance(width_directive, str) and "%" in width_directive:
                    percentage = float(width_directive.strip("%")) / 100.0
                    return container_width * percentage
                if isinstance(width_directive, float) and 0 < width_directive <= 1:
                    return container_width * width_directive
                if isinstance(width_directive, int | float) and width_directive > 1:
                    return min(float(width_directive), container_width)
            except (ValueError, TypeError):
                logger.warning(f"Invalid width directive: {width_directive}")

        return container_width

    def _merge_directives_with_precedence(
        self,
        base_directives: dict,
        element_directives: dict,
        override_directives: dict,
    ) -> dict:
        """
        Merge directives according to precedence hierarchy:
        Base -> Inherited -> Element-Specific -> Override

        The most specific directive always wins.
        """
        # Define inheritable directives
        inheritable_directives = {
            "align",
            "color",
            "fontsize",
            "font-family",
            "bold",
            "italic",
            "line-spacing",
            "valign",
        }

        merged = {}

        # 1. Apply inheritable directives from base (lowest priority)
        for key, value in base_directives.items():
            if key in inheritable_directives:
                merged[key] = value

        # 2. Apply element-specific directives (higher priority than base/inherited)
        # Element directives should override inherited ones
        merged.update(element_directives)

        # 3. Apply override directives (highest priority)
        merged.update(override_directives)

        logger.debug(
            f"Merged directives: base={base_directives} + "
            f"element={element_directives} + override={override_directives} = {merged}"
        )

        return merged

    def _merge_section_directives_to_element(self, element, parent_section):
        """
        Merge section directives into element directives during layout.
        This applies section-level visual directives to elements within that section.
        """
        if not parent_section or not parent_section.directives:
            return

        # Define inheritable directives that cascade from section to elements
        # FIXED: Added 'background' to this set to allow row backgrounds to propagate to child elements.
        inheritable_directives = {
            "align",
            "color",
            "fontsize",
            "font-family",
            "bold",
            "italic",
            "line-spacing",
            "valign",
            "background",
        }

        # Only merge inheritable directives, element directives take precedence
        for key, value in parent_section.directives.items():
            if key in inheritable_directives and key not in element.directives:
                element.directives[key] = value

        logger.debug(
            f"Applied section directives to element: section={parent_section.directives} -> element={element.directives}"
        )
