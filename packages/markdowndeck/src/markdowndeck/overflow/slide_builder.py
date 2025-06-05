"""Slide builder for creating continuation slides with proper formatting."""

import logging
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
    indicating they are continuations.
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
        self._extract_elements_from_sections(continuation_slide)

        logger.info(
            f"Created continuation slide {continuation_id} with {len(continuation_slide.elements)} elements"
        )
        return continuation_slide

    def _create_continuation_title(self, slide_number: int) -> "TextElement | None":
        """
        Create a title element for the continuation slide.

        Args:
            slide_number: The sequence number of this continuation slide

        Returns:
            A TextElement for the continuation title, or None if original had no title
        """
        original_title = self._extract_original_title_text()

        if not original_title:
            # If no original title, create a generic continuation title
            original_title = "Content"

        # Create continuation title text
        if slide_number == 1:
            continuation_text = f"{original_title} {CONTINUED_TITLE_SUFFIX}"
        else:
            continuation_text = (
                f"{original_title} {CONTINUED_TITLE_SUFFIX} ({slide_number})"
            )

        # Create title element with original styling if available
        from markdowndeck.models import ElementType, TextElement

        title_element = TextElement(
            element_type=ElementType.TITLE,
            text=continuation_text,
            object_id=f"title_{uuid.uuid4().hex[:8]}",
            horizontal_alignment="center",  # Titles are typically centered
        )

        # Copy title directives from original if available
        original_title_element = self._find_original_title_element()
        if original_title_element and hasattr(original_title_element, "directives"):
            title_element.directives = deepcopy(original_title_element.directives)

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

    def _extract_elements_from_sections(self, slide: "Slide") -> None:
        """
        Extract all elements from sections and add them to the slide's elements list.

        This recursively processes sections and their subsections to build a flat
        list of elements for the slide.

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
                        slide.elements.append(deepcopy(element))

                if section.subsections:
                    # Recursively process subsections
                    extract_from_section_list(section.subsections)

        extract_from_section_list(slide.sections)
        logger.debug(
            f"Extracted {len(slide.elements)} elements from {len(slide.sections)} sections"
        )
