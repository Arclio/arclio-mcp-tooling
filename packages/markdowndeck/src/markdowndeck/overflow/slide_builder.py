"""Slide builder for creating continuation slides with proper formatting and position reset."""

import logging
import re
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, cast

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
    """

    def __init__(self, original_slide: "Slide"):
        self.original_slide = original_slide

    def create_continuation_slide(
        self, new_root_section: "Section", slide_number: int
    ) -> "Slide":
        """
        Create a continuation slide with the specified root section.
        """
        from markdowndeck.models import Slide, SlideLayout

        continuation_id = self._generate_safe_object_id(
            self.original_slide.object_id, f"cont_{slide_number}"
        )
        continuation_slide = Slide(
            object_id=continuation_id,
            layout=SlideLayout.BLANK,
            root_section=deepcopy(new_root_section),
            is_continuation=True,
            elements=[],
            background=(
                deepcopy(self.original_slide.background)
                if self.original_slide.background
                else None
            ),
            notes=self.original_slide.notes,
        )

        if continuation_slide.root_section:
            self._reset_section_positions_recursively([continuation_slide.root_section])

        continuation_title = self._create_continuation_title(slide_number)
        if continuation_title:
            continuation_slide.elements.append(continuation_title)
            continuation_slide.title = continuation_title.text

        continuation_footer = self._create_continuation_footer()
        if continuation_footer:
            continuation_slide.elements.append(continuation_footer)

        self._extract_elements_from_sections_with_reset(continuation_slide)
        return continuation_slide

    def _find_original_title_element(self) -> "TextElement | None":
        """
        Find the title element in the original slide's renderable_elements or elements list.
        REFACTORED: To check renderable_elements first.
        """
        search_lists = [
            self.original_slide.renderable_elements,
            self.original_slide.elements,
        ]
        for L in search_lists:
            for element in L:
                if element.element_type == ElementType.TITLE:
                    return cast(TextElement, element)
        return None

    def _find_original_footer_element(self) -> "TextElement | None":
        """
        Find the footer element in the original slide's renderable_elements or elements list.
        REFACTORED: To check renderable_elements first.
        """
        search_lists = [
            self.original_slide.renderable_elements,
            self.original_slide.elements,
        ]
        for L in search_lists:
            for element in L:
                if element.element_type == ElementType.FOOTER:
                    return cast(TextElement, element)
        return None

    def _reset_section_positions_recursively(
        self, sections: list["Section"], visited: set[str] = None
    ) -> None:
        """
        Recursively reset positions and sizes for all sections and their subsections.
        """
        if visited is None:
            visited = set()

        for section in sections:
            if section.id in visited:
                logger.warning(
                    f"Circular reference detected for section {section.id}, skipping"
                )
                continue
            visited.add(section.id)

            section.position = None
            section.size = None
            logger.debug(f"Reset position/size for section {section.id}")

            section_elements = [
                c for c in section.children if not hasattr(c, "children")
            ]
            for element in section_elements:
                element.position = None
                element.size = None

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
        Extract all elements from the root_section and add them to the slide's elements list.
        REFACTORED: To start from the single root_section.
        """
        if not slide.root_section:
            return

        visited = set()

        def extract_from_section(section: "Section"):
            if section.id in visited:
                logger.warning(
                    f"Circular reference detected for section {section.id}, skipping"
                )
                return
            visited.add(section.id)

            for child in section.children:
                if not hasattr(child, "children"):  # It's an Element
                    element_copy = deepcopy(child)
                    element_copy.object_id = self._generate_safe_element_id(
                        element_copy.element_type.value
                    )
                    element_copy.position = None
                    element_copy.size = None
                    slide.elements.append(element_copy)
                else:  # It's a Section
                    extract_from_section(child)

        extract_from_section(slide.root_section)
        logger.debug(
            f"Extracted {len(slide.elements)} elements from root section "
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
        if not base_id or len(base_id) > available_for_base:
            # For continuation slides, prioritize keeping the original slide number
            # and truncate the complex continuation chain
            if base_id and "_cont_" in base_id:
                # Extract original slide part (e.g., "slide_10" from "slide_10_cont_1_4ba998")
                original_part = base_id.split("_cont_")[0]
                if len(original_part) <= available_for_base:
                    # Use original slide ID + truncation indicator
                    truncated_base = original_part
                else:
                    # Even original is too long, simple truncation
                    truncated_base = base_id[: available_for_base - 3] + "..."
            else:
                # Simple truncation with indicator
                truncated_base = (base_id or "slide")[:available_for_base]
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
