import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from markdowndeck.models import Element, Section, Slide

from markdowndeck.models import Section as SectionModel

logger = logging.getLogger(__name__)


class OverflowDetector:
    """
    Detects overflow in slides while enforcing strict jurisdictional boundaries.
    """

    def __init__(self, slide_height: float, top_margin: float, bottom_margin: float):
        self.slide_height = slide_height
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin

    def find_first_overflowing_element(self, slide: "Slide") -> Optional["Element"]:
        """
        Find the first leaf element that overflows the slide's body boundaries.
        """
        if not slide.root_section:
            return None

        _body_start_y, body_end_y = self._calculate_body_boundaries(slide)

        return self._find_overflowing_element_recursive(slide.root_section, body_end_y)

    def _find_overflowing_element_recursive(
        self, section: "Section", body_end_y: float
    ) -> Optional["Element"]:
        """
        Recursively search for the first element that overflows the boundary.
        """
        if not hasattr(section, "children") or not section.children:
            return None

        has_fixed_height = "height" in section.directives
        if has_fixed_height and section.position and section.size:
            section_bottom = section.position[1] + section.size[1]
            if section_bottom > body_end_y:
                return self._find_first_leaf_element(section)
            return None

        for child in section.children:
            if isinstance(child, SectionModel):
                overflowing = self._find_overflowing_element_recursive(
                    child, body_end_y
                )
                if overflowing:
                    return overflowing
            elif child.position and child.size:
                child_bottom = child.position[1] + child.size[1]
                if child_bottom > body_end_y:
                    return child
        return None

    def _find_first_leaf_element(self, section: "Section") -> Optional["Element"]:
        """
        Find the first leaf element within a section hierarchy.
        """
        if not hasattr(section, "children") or not section.children:
            return None
        for child in section.children:
            if not isinstance(child, SectionModel):
                return child
            leaf = self._find_first_leaf_element(child)
            if leaf:
                return leaf
        return None

    def _calculate_body_boundaries(self, slide: "Slide") -> tuple[float, float]:
        """
        Calculate the available body area for a slide, accounting for meta-elements.
        """
        from markdowndeck.layout.constants import HEADER_TO_BODY_SPACING

        body_start_y = self.top_margin
        body_end_y = self.slide_height - self.bottom_margin

        header_bottom = self.top_margin
        title = slide.get_title_element()
        if title and title.position and title.size:
            header_bottom = max(header_bottom, title.position[1] + title.size[1])
        subtitle = slide.get_subtitle_element()
        if subtitle and subtitle.position and subtitle.size:
            header_bottom = max(header_bottom, subtitle.position[1] + subtitle.size[1])

        if header_bottom > self.top_margin:
            body_start_y = header_bottom + HEADER_TO_BODY_SPACING

        footer = slide.get_footer_element()
        if footer and footer.position and footer.size:
            body_end_y = footer.position[1]

        return body_start_y, body_end_y
