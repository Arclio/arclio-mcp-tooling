"""Overflow detection for positioned slide elements."""

import logging

from markdowndeck.models import Element, ElementType
from markdowndeck.overflow.models import (
    ContentGroup,
    OverflowElement,
    OverflowInfo,
    OverflowType,
    SlideCapacity,
)

logger = logging.getLogger(__name__)


class OverflowDetector:
    """
    Detects overflow conditions in positioned slides.

    Analyzes elements positioned by the layout calculator to identify:
    - Elements that extend beyond slide boundaries
    - Content relationships that should be preserved
    - Optimal break points for content distribution
    """

    def __init__(
        self,
        slide_width: float = 720,
        slide_height: float = 405,
        margins: dict[str, float] = None,
    ):
        """
        Initialize overflow detector with slide dimensions.

        Args:
            slide_width: Width of slides in points
            slide_height: Height of slides in points
            margins: Slide margins
        """
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.margins = margins or {"top": 50, "right": 50, "bottom": 50, "left": 50}

        # Calculate slide capacity and zones
        self.capacity = self._calculate_slide_capacity()

        logger.debug(f"OverflowDetector initialized - body zone: {self.capacity.body_height}pt height")

    def detect_overflow(self, slide) -> OverflowInfo:
        """
        Detect overflow conditions in a positioned slide.

        Args:
            slide: Slide with positioned elements

        Returns:
            OverflowInfo with complete analysis
        """
        logger.debug(f"Analyzing slide {slide.object_id} for overflow")

        # Get body elements (exclude header/footer from overflow analysis)
        body_elements = self._get_body_elements(slide)

        if not body_elements:
            return OverflowInfo(has_overflow=False, summary="No body elements to analyze")

        # Analyze each element for overflow
        overflow_elements = []
        total_content_height = 0.0

        for element in body_elements:
            if not element.position or not element.size:
                logger.warning(f"Element {getattr(element, 'object_id', 'unknown')} missing position/size")
                continue

            # Calculate element boundaries
            element_bottom = element.position[1] + element.size[1]
            total_content_height = max(total_content_height, element_bottom)

            # Check for overflow
            overflow_amount = self.capacity.get_overflow_amount(element)

            if overflow_amount > 0:
                overflow_elem = OverflowElement(
                    element=element,
                    overflow_amount=overflow_amount,
                    overflow_type=OverflowType.VERTICAL,
                    can_split=self._can_element_split(element),
                    related_elements=self._find_related_elements(element, body_elements),
                )
                overflow_elements.append(overflow_elem)

        # Calculate overflow metrics
        has_overflow = len(overflow_elements) > 0
        total_overflow = max(0, total_content_height - self.capacity.body_bottom)

        # Create summary
        summary = self._create_overflow_summary(overflow_elements, total_overflow)

        return OverflowInfo(
            has_overflow=has_overflow,
            overflow_elements=overflow_elements,
            total_content_height=total_content_height,
            available_height=self.capacity.body_height,
            overflow_amount=total_overflow,
            affected_zones=["body"] if has_overflow else [],
            summary=summary,
        )

    def analyze_content_groups(self, slide) -> list[ContentGroup]:
        """
        Analyze slide content and group related elements.

        Args:
            slide: Slide to analyze

        Returns:
            List of content groups that should be kept together
        """
        body_elements = self._get_body_elements(slide)

        if not body_elements:
            return []

        groups = []
        processed_elements = set()

        for element in body_elements:
            if id(element) in processed_elements:
                continue

            # Find all elements related to this one
            related = self._find_element_group(element, body_elements)

            # Create content group
            group_type = self._determine_group_type(related)
            total_height = self._calculate_group_height(related)

            group = ContentGroup(
                elements=related,
                total_height=total_height,
                group_type=group_type,
                priority=self._calculate_group_priority(related),
                can_break_after=self._can_break_after_group(related),
            )

            groups.append(group)

            # Mark elements as processed
            for elem in related:
                processed_elements.add(id(elem))

        logger.debug(f"Created {len(groups)} content groups from {len(body_elements)} elements")
        return groups

    def _calculate_slide_capacity(self) -> SlideCapacity:
        """Calculate slide capacity and zone boundaries."""
        # Zone heights (matching layout calculator constants)
        header_height = 90.0
        footer_height = 30.0

        # Zone boundaries
        header_top = self.margins["top"]
        header_bottom = header_top + header_height
        body_top = header_bottom
        body_bottom = self.slide_height - footer_height - self.margins["bottom"]
        footer_top = body_bottom
        footer_bottom = self.slide_height - self.margins["bottom"]

        # Available dimensions
        content_width = self.slide_width - self.margins["left"] - self.margins["right"]
        body_height = body_bottom - body_top

        return SlideCapacity(
            total_height=self.slide_height,
            total_width=self.slide_width,
            header_top=header_top,
            header_bottom=header_bottom,
            body_top=body_top,
            body_bottom=body_bottom,
            footer_top=footer_top,
            footer_bottom=footer_bottom,
            header_height=header_height,
            body_height=body_height,
            footer_height=footer_height,
            content_width=content_width,
            margins=self.margins,
        )

    def _get_body_elements(self, slide) -> list[Element]:
        """Get elements that belong in the body zone."""
        return [
            element
            for element in slide.elements
            if element.element_type not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]

    def _can_element_split(self, element: Element) -> bool:
        """Determine if an element can be split across slides."""
        # Most elements cannot be split, but some could be in future implementations
        splittable_types = {
            # ElementType.TEXT,  # Could split long paragraphs
            # ElementType.BULLET_LIST,  # Could split lists
            # ElementType.TABLE,  # Could split large tables
        }
        return element.element_type in splittable_types

    def _find_related_elements(self, element: Element, all_elements: list[Element]) -> list[Element]:
        """Find elements related to the given element."""
        related = []

        # Check for explicit relationship markers
        if hasattr(element, "related_to_next") and element.related_to_next:
            # Find the next element
            try:
                current_index = all_elements.index(element)
                if current_index + 1 < len(all_elements):
                    related.append(all_elements[current_index + 1])
            except ValueError:
                pass

        if hasattr(element, "related_to_prev") and element.related_to_prev:
            # Find the previous element
            try:
                current_index = all_elements.index(element)
                if current_index > 0:
                    related.append(all_elements[current_index - 1])
            except ValueError:
                pass

        return related

    def _find_element_group(self, start_element: Element, all_elements: list[Element]) -> list[Element]:
        """Find all elements in the same logical group as the start element."""
        group = [start_element]
        processed = {id(start_element)}

        # Follow relationship chains
        queue = [start_element]

        while queue:
            current = queue.pop(0)

            # Find related elements
            related = self._find_related_elements(current, all_elements)

            for related_elem in related:
                if id(related_elem) not in processed:
                    group.append(related_elem)
                    processed.add(id(related_elem))
                    queue.append(related_elem)

        # Sort group by position
        group.sort(key=lambda e: e.position[1] if e.position else 0)

        return group

    def _determine_group_type(self, elements: list[Element]) -> str:
        """Determine the type of content group."""
        if len(elements) == 1:
            return "single"

        # Check for heading + content pattern
        if len(elements) >= 2:
            first = elements[0]
            if first.element_type == ElementType.TEXT and hasattr(first, "text") and first.text.strip().startswith("#"):
                return "header_with_content"

        # Check for list of similar elements
        types = {elem.element_type for elem in elements}
        if len(types) == 1:
            return f"homogeneous_{list(types)[0]}"

        return "mixed"

    def _calculate_group_height(self, elements: list[Element]) -> float:
        """Calculate total height of a group including spacing."""
        if not elements:
            return 0.0

        # Find the span from top of first to bottom of last element
        positions = [elem.position[1] for elem in elements if elem.position]
        sizes = [elem.size[1] for elem in elements if elem.size]

        if not positions or not sizes:
            return 0.0

        min_top = min(positions)
        max_bottom = max(
            pos + size for pos, size in zip(positions, sizes, strict=False) if pos is not None and size is not None
        )

        return max_bottom - min_top

    def _calculate_group_priority(self, elements: list[Element]) -> int:
        """Calculate priority for keeping group together."""
        # Higher priority = more important to keep together
        if len(elements) == 1:
            return 1

        # Headers with content get high priority
        if self._determine_group_type(elements) == "header_with_content":
            return 10

        # Related elements get medium priority
        has_relationships = any(hasattr(elem, "related_to_next") or hasattr(elem, "related_to_prev") for elem in elements)

        if has_relationships:
            return 5

        return 3

    def _can_break_after_group(self, elements: list[Element]) -> bool:
        """Determine if a slide break is acceptable after this group."""
        if not elements:
            return True

        last_element = elements[-1]

        # Don't break after elements that are related to the next element
        return not (hasattr(last_element, "related_to_next") and last_element.related_to_next)

    def _create_overflow_summary(self, overflow_elements: list[OverflowElement], total_overflow: float) -> str:
        """Create human-readable overflow summary."""
        if not overflow_elements:
            return "No overflow detected"

        element_count = len(overflow_elements)
        return f"{element_count} element(s) overflow by {total_overflow:.1f}pt total"
