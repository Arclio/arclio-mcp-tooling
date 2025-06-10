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
        # Google Slides API has a 50-character limit on object IDs
        continuation_id = self._generate_safe_object_id(
            base_id=self.original_slide.object_id,
            suffix=f"cont_{slide_number}",
            max_length=50,
        )

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

    def _reset_section_positions_recursively(
        self, sections: list["Section"], visited: set[str] = None
    ) -> None:
        """
        Recursively reset positions and sizes for all sections and their subsections.

        This is critical for continuation slides to ensure the layout calculator
        can properly reposition everything from scratch.

        Args:
            sections: List of sections to reset
            visited: Set of visited section IDs to prevent circular references
        """
        if visited is None:
            visited = set()

        for section in sections:
            # Check for circular reference
            if section.id in visited:
                logger.warning(
                    f"Circular reference detected for section {section.id}, skipping"
                )
                continue

            visited.add(section.id)

            # Reset section position and size
            section.position = None
            section.size = None

            logger.debug(f"Reset position/size for section {section.id}")

            # Reset element positions within this section
            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            for element in section_elements:
                element.position = None
                element.size = None

            # Recursively reset child sections
            child_sections = [c for c in section.children if hasattr(c, "children")]
            if child_sections:
                self._reset_section_positions_recursively(
                    child_sections, visited.copy()
                )

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
            object_id=self._generate_safe_element_id("title"),
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
            object_id=self._generate_safe_element_id("footer"),
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

        visited = set()

        def extract_from_section_list(sections: list[Section]):
            for section in sections:
                # Check for circular reference
                if section.id in visited:
                    logger.warning(
                        f"Circular reference detected for section {section.id} during element extraction, skipping"
                    )
                    continue

                visited.add(section.id)

                # Get elements and child sections from unified children list
                section_elements = [
                    c for c in section.children if not hasattr(c, "children")
                ]
                child_sections = [c for c in section.children if hasattr(c, "children")]

                if section_elements:
                    # Add elements from this section
                    for element in section_elements:
                        # Generate unique object ID for each element to avoid conflicts
                        # Use safe object ID generation to stay under Google's 50-char limit
                        if hasattr(element, "object_id"):
                            element.object_id = self._generate_safe_element_id(
                                element.element_type.value
                            )

                        # CRITICAL: Reset element positions for continuation slides
                        # Elements in continuation slides must start with fresh positioning
                        element_copy = deepcopy(element)
                        element_copy.position = None
                        element_copy.size = None
                        slide.elements.append(element_copy)

                if child_sections:
                    # Recursively process child sections
                    extract_from_section_list(child_sections)

        extract_from_section_list(slide.sections)
        logger.debug(
            f"Extracted {len(slide.elements)} elements from {len(slide.sections)} sections "
            f"with positions reset for continuation slide"
        )

    def _generate_safe_object_id(
        self, base_id: str, suffix: str, max_length: int = 50
    ) -> str:
        """
        Generate an object ID that stays within Google Slides API limits (50 characters).

        Strategy:
        1. Try full format: {base_id}_{suffix}_{uuid6}
        2. If too long, truncate base_id intelligently
        3. Always ensure uniqueness with UUID suffix

        Args:
            base_id: The base object ID (e.g., slide_10 or slide_10_cont_1_4ba998)
            suffix: The suffix to add (e.g., "cont_1")
            max_length: Maximum allowed length (Google Slides limit is 50)

        Returns:
            Safe object ID under the length limit
        """
        uuid_suffix = uuid.uuid4().hex[:6]  # 6 chars for uniqueness
        separator_chars = 2  # Two underscores: _{suffix}_{uuid}

        # Calculate available space for base_id
        reserved_space = len(suffix) + len(uuid_suffix) + separator_chars
        available_for_base = max_length - reserved_space

        # If base_id is too long, intelligently truncate it
        if len(base_id) > available_for_base:
            # For continuation slides, prioritize keeping the original slide number
            # and truncate the complex continuation chain
            if "_cont_" in base_id:
                # Extract original slide part (e.g., "slide_10" from "slide_10_cont_1_4ba998")
                original_part = base_id.split("_cont_")[0]
                if len(original_part) <= available_for_base:
                    # Use original slide ID + truncation indicator
                    truncated_base = original_part
                else:
                    # Even original is too long, truncate it
                    truncated_base = base_id[: available_for_base - 3] + "..."
            else:
                # Simple truncation with indicator
                truncated_base = base_id[: available_for_base - 3] + "..."
        else:
            truncated_base = base_id

        safe_id = f"{truncated_base}_{suffix}_{uuid_suffix}"

        logger.debug(f"Generated safe object ID: '{safe_id}' (length: {len(safe_id)})")
        return safe_id

    def _generate_safe_element_id(self, element_type: str, max_length: int = 50) -> str:
        """
        Generate a safe element object ID under Google's length limit.

        Args:
            element_type: The element type (e.g., "text", "image", "title")
            max_length: Maximum allowed length (50 for Google Slides)

        Returns:
            Safe element object ID
        """
        uuid_suffix = uuid.uuid4().hex[:8]  # 8 chars for uniqueness
        separator_chars = 1  # One underscore: {type}_{uuid}

        # Calculate available space for element type
        available_for_type = max_length - len(uuid_suffix) - separator_chars

        # Truncate element type if needed
        truncated_type = (
            element_type[:available_for_type]
            if len(element_type) > available_for_type
            else element_type
        )

        return f"{truncated_type}_{uuid_suffix}"

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

            # Check child sections recursively
            child_sections = [c for c in section.children if hasattr(c, "children")]
            if child_sections:
                subsection_warnings = self._validate_section_reset(
                    child_sections, level + 1
                )
                warnings.extend(subsection_warnings)

        return warnings
