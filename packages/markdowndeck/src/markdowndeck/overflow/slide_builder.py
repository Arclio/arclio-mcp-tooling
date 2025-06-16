import logging
import re
import uuid
from copy import deepcopy
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from markdowndeck.models import Slide, TextElement
    from markdowndeck.models.slide import Section

from markdowndeck.models import ElementType

logger = logging.getLogger(__name__)

# REFACTORED: Suffixes are now local constants.
CONTINUED_TITLE_SUFFIX = "(continued)"
CONTINUED_FOOTER_SUFFIX = "(cont.)"


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

        # SPECIFICATION_GAP: List Continuation Context - OVERFLOW_SPEC.md Rule #8
        # BLOCKS: The current architecture, which splits the entire root_section, makes it difficult
        # to reliably determine the parent context of a single overflowing nested list element.
        # This would require passing the full parent chain of the overflowing element, which is not
        # currently supported. This feature is deferred.
        # WORKAROUND: No context title is added.

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
            self._reset_positions_recursively(continuation_slide.root_section)

        continuation_title = self._create_continuation_title(slide_number)
        if continuation_title:
            continuation_slide.elements.append(continuation_title)

        continuation_footer = self._create_continuation_footer()
        if continuation_footer:
            continuation_slide.elements.append(continuation_footer)

        self._extract_elements_from_sections_with_reset(continuation_slide)
        return continuation_slide

    def _find_original_title_element(self) -> "TextElement | None":
        """
        Find the title element in the original slide's renderable_elements or elements list.
        """
        search_lists = [
            self.original_slide.renderable_elements,
            self.original_slide.elements,
        ]
        for element_list in search_lists:
            for element in element_list:
                if element.element_type == ElementType.TITLE:
                    return cast("TextElement", element)
        return None

    def _find_original_footer_element(self) -> "TextElement | None":
        """
        Find the footer element in the original slide's renderable_elements or elements list.
        """
        search_lists = [
            self.original_slide.renderable_elements,
            self.original_slide.elements,
        ]
        for element_list in search_lists:
            for element in element_list:
                if element.element_type == ElementType.FOOTER:
                    return cast("TextElement", element)
        return None

    def _reset_positions_recursively(self, section: "Section") -> None:
        """
        Recursively reset positions and sizes for all sections and their children.
        """
        section.position = None
        section.size = None
        for child in section.children:
            child.position = None
            child.size = None
            if hasattr(child, "children"):
                self._reset_positions_recursively(child)

    def _create_continuation_title(self, slide_number: int) -> "TextElement | None":
        """Create a title element for the continuation slide with correct numbering."""
        from markdowndeck.models import TextElement

        original_title_text = self._extract_original_title_text()
        base_title = original_title_text
        match = re.search(r"\s*\(continued(?:\s\d+)?\)$", base_title)
        if match:
            base_title = base_title[: match.start()].strip()
        if not base_title:
            base_title = "Content"
        continuation_text = f"{base_title} {CONTINUED_TITLE_SUFFIX}"
        title_element = TextElement(
            element_type=ElementType.TITLE,
            text=continuation_text,
            object_id=self._generate_safe_element_id("title"),
            position=None,
            size=None,
        )
        original_title_element = self._find_original_title_element()
        if original_title_element:
            title_element.directives = deepcopy(original_title_element.directives)
            title_element.horizontal_alignment = getattr(
                original_title_element,
                "horizontal_alignment",
                title_element.horizontal_alignment,
            )
        return title_element

    def _create_continuation_footer(self) -> "TextElement | None":
        """Create a footer element for the continuation slide."""
        from markdowndeck.models import TextElement

        original_footer_element = self._find_original_footer_element()
        if not original_footer_element:
            return None
        original_footer_text = getattr(original_footer_element, "text", "")
        continuation_footer_text = (
            f"{original_footer_text} {CONTINUED_FOOTER_SUFFIX}"
            if CONTINUED_FOOTER_SUFFIX not in original_footer_text
            else original_footer_text
        )
        return TextElement(
            element_type=ElementType.FOOTER,
            text=continuation_footer_text,
            object_id=self._generate_safe_element_id("footer"),
            horizontal_alignment=getattr(
                original_footer_element, "horizontal_alignment", "left"
            ),
            directives=deepcopy(getattr(original_footer_element, "directives", {})),
            position=None,
            size=None,
        )

    def _extract_original_title_text(self) -> str:
        """Extract the title text from the original slide."""
        title_element = self._find_original_title_element()
        if title_element and hasattr(title_element, "text"):
            return title_element.text
        return ""

    def _extract_elements_from_sections_with_reset(self, slide: "Slide") -> None:
        """Extract all elements from the root_section and add them to the slide's elements list."""
        from markdowndeck.models.slide import Section as SectionModel

        if not slide.root_section:
            return
        visited = set()

        def extract_from_section(section: "Section"):
            if section.id in visited:
                return
            visited.add(section.id)
            for child in section.children:
                if not isinstance(child, SectionModel):
                    element_copy = deepcopy(child)
                    element_copy.object_id = self._generate_safe_element_id(
                        element_copy.element_type.value
                    )
                    element_copy.position = None
                    element_copy.size = None
                    slide.elements.append(element_copy)
                else:
                    extract_from_section(child)

        extract_from_section(slide.root_section)

    def _generate_safe_object_id(
        self, base_id: str, suffix: str, max_length: int = 50
    ) -> str:
        """Generate a safe object ID."""
        uuid_suffix = uuid.uuid4().hex[:6]
        separator_chars = 2
        available_for_base = (
            max_length - len(suffix) - len(uuid_suffix) - separator_chars
        )
        if not base_id or len(base_id) > available_for_base:
            if base_id and "_cont_" in base_id:
                original_part = base_id.split("_cont_")[0]
                truncated_base = (
                    original_part
                    if len(original_part) <= available_for_base
                    else original_part[: available_for_base - 3] + "..."
                )
            else:
                truncated_base = (base_id or "slide")[:available_for_base]
        else:
            truncated_base = base_id
        return f"{truncated_base}_{suffix}_{uuid_suffix}"

    def _generate_safe_element_id(self, element_type: str, max_length: int = 50) -> str:
        """Generate a safe element object ID."""
        uuid_suffix = uuid.uuid4().hex[:8]
        separator_chars = 1
        available_for_type = max_length - len(uuid_suffix) - separator_chars
        truncated_type = (
            element_type[:available_for_type]
            if len(element_type) > available_for_type
            else element_type
        )
        return f"{truncated_type}_{uuid_suffix}"
