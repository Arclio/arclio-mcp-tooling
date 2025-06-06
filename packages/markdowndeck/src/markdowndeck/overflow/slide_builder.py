"""Slide builder for creating continuation slides with proper formatting and position reset."""

import logging
import re
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdowndeck.models import Slide, TextElement
    from markdowndeck.models.slide import Section

from markdowndeck.overflow.constants import (
    CONTINUED_FOOTER_SUFFIX,
    CONTINUED_TITLE_SUFFIX,
)

logger = logging.getLogger(__name__)


class SlideBuilder:
    """
    Factory class for creating continuation slides with consistent formatting.

    This class handles the clerical work of creating new slides that maintain
    the same visual style and metadata as the original slide while clearly
    indicating they are continuations. It ensures proper position and size
    reset for all elements and sections in continuation slides.
    """

    def __init__(self, original_slide: "Slide"):
        """
        Initialize the slide builder with an original slide template.

        Args:
            original_slide: The slide to use as a template for continuation slides
        """
        self.original_slide = original_slide
        logger.debug(
            f"SlideBuilder initialized with original slide: {original_slide.object_id}"
        )

    def create_continuation_slide(
        self, new_sections: list["Section"], slide_number: int
    ) -> "Slide":
        """
        Create a continuation slide with the specified sections.

        This method creates a new slide that maintains the visual consistency
        of the original while clearly marking it as a continuation. All sections
        and elements have their positions reset to ensure proper layout calculation.

        Args:
            new_sections: List of sections to include in the continuation slide
            slide_number: The sequence number of this continuation slide (1, 2, 3...)

        Returns:
            A new Slide object configured as a continuation slide
        """
        logger.debug(
            f"Creating continuation slide {slide_number} with {len(new_sections)} sections"
        )

        # Generate unique ID for the continuation slide
        continuation_id = f"{self.original_slide.object_id}_cont_{slide_number}_{uuid.uuid4().hex[:6]}"

        # Create the base slide structure
        from markdowndeck.models import Slide, SlideLayout

        continuation_slide = Slide(
            object_id=continuation_id,
            layout=SlideLayout.TITLE_AND_BODY,  # Use standard layout for continuations
            sections=deepcopy(new_sections),
            elements=[],  # Will be populated from sections and metadata
            background=(
                deepcopy(self.original_slide.background)
                if self.original_slide.background
                else None
            ),
            notes=self.original_slide.notes,  # Keep original notes for reference
        )

        # CRITICAL: Reset all positions and sizes in sections for continuation slides
        self._reset_section_positions_recursively(continuation_slide.sections)

        # Create continuation title
        continuation_title = self._create_continuation_title(slide_number)
        if continuation_title:
            continuation_slide.elements.append(continuation_title)
            continuation_slide.title = continuation_title.text

        # Create continuation footer if original had footer
        continuation_footer = self._create_continuation_footer()
        if continuation_footer:
            continuation_slide.elements.append(continuation_footer)

        # Extract all elements from sections and add to slide
        self._extract_elements_from_sections_with_reset(continuation_slide)

        logger.info(
            f"Created continuation slide {continuation_id} with {len(continuation_slide.elements)} elements"
        )
        return continuation_slide

    def _reset_section_positions_recursively(self, sections: list["Section"]) -> None:
        """
        Recursively reset positions and sizes for all sections and their subsections.

        This is critical for continuation slides to ensure the layout calculator
        can properly reposition everything from scratch.

        Args:
            sections: List of sections to reset
        """
        for section in sections:
            # Reset section position and size
            section.position = None
            section.size = None

            logger.debug(f"Reset position/size for section {section.id}")

            # Reset element positions within this section
            if hasattr(section, "elements") and section.elements:
                for element in section.elements:
                    element.position = None
                    element.size = None

            # Recursively reset subsections
            if hasattr(section, "subsections") and section.subsections:
                self._reset_section_positions_recursively(section.subsections)

    def _create_continuation_title(self, slide_number: int) -> "TextElement | None":
        """
        Create a title element for the continuation slide with correct numbering.
        """
        from markdowndeck.models import ElementType, TextElement

        original_title_text = self._extract_original_title_text()
        base_title = original_title_text

        # Find and remove existing continuation markers for a clean base title
        match = re.search(r"\s*\(continued(?:\s\d+)?\)$", base_title)
        if match:
            base_title = base_title[: match.start()].strip()

        if not base_title:
            base_title = "Content"

        # Append new, correct continuation marker
        if slide_number > 1:
            continuation_text = (
                f"{base_title} {CONTINUED_TITLE_SUFFIX} ({slide_number})"
            )
        else:
            continuation_text = f"{base_title} {CONTINUED_TITLE_SUFFIX}"

        title_element = TextElement(
            element_type=ElementType.TITLE,
            text=continuation_text,
            object_id=f"title_{uuid.uuid4().hex[:8]}",
            position=None,  # Reset position for recalculation
            size=None,  # Reset size for recalculation
        )

        original_title_element = self._find_original_title_element()
        if original_title_element:
            title_element.directives = deepcopy(original_title_element.directives)
            title_element.horizontal_alignment = getattr(
                original_title_element,
                "horizontal_alignment",
                title_element.horizontal_alignment,
            )

        logger.debug(f"Created continuation title: '{continuation_text}'")
        return title_element

    def _create_continuation_footer(self) -> "TextElement | None":
        """
        Create a footer element for the continuation slide.

        Returns:
            A TextElement for the continuation footer, or None if original had no footer
        """
        original_footer_element = self._find_original_footer_element()

        if not original_footer_element:
            return None

        # Get original footer text
        original_footer_text = getattr(original_footer_element, "text", "")

        # Create continuation footer text
        if CONTINUED_FOOTER_SUFFIX not in original_footer_text:
            continuation_footer_text = (
                f"{original_footer_text} {CONTINUED_FOOTER_SUFFIX}"
            )
        else:
            continuation_footer_text = original_footer_text

        # Create footer element
        from markdowndeck.models import ElementType, TextElement

        footer_element = TextElement(
            element_type=ElementType.FOOTER,
            text=continuation_footer_text,
            object_id=f"footer_{uuid.uuid4().hex[:8]}",
            horizontal_alignment=getattr(
                original_footer_element, "horizontal_alignment", "left"
            ),
            directives=deepcopy(getattr(original_footer_element, "directives", {})),
            position=None,  # Reset position for recalculation
            size=None,  # Reset size for recalculation
        )

        logger.debug(f"Created continuation footer: '{continuation_footer_text}'")
        return footer_element

    def _extract_original_title_text(self) -> str:
        """Extract the title text from the original slide."""
        # First try the title attribute
        if hasattr(self.original_slide, "title") and self.original_slide.title:
            return self.original_slide.title

        # Then look for title element
        title_element = self._find_original_title_element()
        if title_element and hasattr(title_element, "text"):
            return title_element.text

        return ""

    def _find_original_title_element(self) -> "TextElement | None":
        """Find the title element in the original slide."""
        from markdowndeck.models import ElementType

        for element in self.original_slide.elements:
            if element.element_type == ElementType.TITLE:
                return element
        return None

    def _find_original_footer_element(self) -> "TextElement | None":
        """Find the footer element in the original slide."""
        from markdowndeck.models import ElementType

        for element in self.original_slide.elements:
            if element.element_type == ElementType.FOOTER:
                return element
        return None

    def _extract_elements_from_sections_with_reset(self, slide: "Slide") -> None:
        """
        Extract all elements from sections and add them to the slide's elements list.

        This recursively processes sections and their subsections to build a flat
        list of elements for the slide. All elements have their positions and sizes
        reset to ensure proper layout calculation.

        Args:
            slide: The slide to populate with elements from its sections
        """
        from markdowndeck.models.slide import Section

        def extract_from_section_list(sections: list[Section]):
            for section in sections:
                if section.elements:
                    # Add elements from this section
                    for element in section.elements:
                        # Generate unique object ID for each element to avoid conflicts
                        if hasattr(element, "object_id"):
                            element.object_id = (
                                f"{element.element_type}_{uuid.uuid4().hex[:8]}"
                            )

                        # CRITICAL: Reset element positions for continuation slides
                        # Elements in continuation slides must start with fresh positioning
                        element_copy = deepcopy(element)
                        element_copy.position = None
                        element_copy.size = None
                        slide.elements.append(element_copy)

                if section.subsections:
                    # Recursively process subsections
                    extract_from_section_list(section.subsections)

        extract_from_section_list(slide.sections)
        logger.debug(
            f"Extracted {len(slide.elements)} elements from {len(slide.sections)} sections "
            f"with positions reset for continuation slide"
        )

    def get_continuation_metadata(self, slide_number: int) -> dict:
        """
        Get metadata about the continuation slide being created.

        Args:
            slide_number: The sequence number of the continuation slide

        Returns:
            Dictionary with continuation metadata
        """
        original_title = self._extract_original_title_text()

        return {
            "original_slide_id": self.original_slide.object_id,
            "original_title": original_title,
            "continuation_number": slide_number,
            "has_original_footer": self._find_original_footer_element() is not None,
            "original_layout": (
                str(self.original_slide.layout)
                if hasattr(self.original_slide, "layout")
                else "unknown"
            ),
            "original_element_count": len(self.original_slide.elements),
            "original_section_count": (
                len(self.original_slide.sections)
                if hasattr(self.original_slide, "sections")
                and self.original_slide.sections
                else 0
            ),
        }

    def validate_continuation_slide(self, continuation_slide: "Slide") -> list[str]:
        """
        Validate a continuation slide for potential issues.

        Args:
            continuation_slide: The continuation slide to validate

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check that positions are properly reset
        for i, element in enumerate(continuation_slide.elements):
            if hasattr(element, "position") and element.position is not None:
                warnings.append(
                    f"Element {i} still has position set - should be None for layout recalculation"
                )
            if hasattr(element, "size") and element.size is not None:
                warnings.append(
                    f"Element {i} still has size set - should be None for layout recalculation"
                )

        # Check sections
        if hasattr(continuation_slide, "sections") and continuation_slide.sections:
            section_warnings = self._validate_section_reset(continuation_slide.sections)
            warnings.extend(section_warnings)

        # Check for continuation markers
        has_continuation_title = any(
            hasattr(elem, "text") and CONTINUED_TITLE_SUFFIX in elem.text
            for elem in continuation_slide.elements
            if hasattr(elem, "element_type") and elem.element_type.name == "TITLE"
        )

        if not has_continuation_title:
            warnings.append("Continuation slide missing continuation title marker")

        return warnings

    def _validate_section_reset(
        self, sections: list["Section"], level: int = 0
    ) -> list[str]:
        """
        Validate that sections have their positions properly reset.

        Args:
            sections: List of sections to validate
            level: Current nesting level

        Returns:
            List of validation warnings
        """
        warnings = []

        for i, section in enumerate(sections):
            if hasattr(section, "position") and section.position is not None:
                warnings.append(f"Section {i} at level {level} still has position set")
            if hasattr(section, "size") and section.size is not None:
                warnings.append(f"Section {i} at level {level} still has size set")

            # Check subsections recursively
            if hasattr(section, "subsections") and section.subsections:
                subsection_warnings = self._validate_section_reset(
                    section.subsections, level + 1
                )
                warnings.extend(subsection_warnings)

        return warnings
