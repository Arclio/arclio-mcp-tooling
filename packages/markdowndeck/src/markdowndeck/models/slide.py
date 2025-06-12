"""Slide model for presentations."""

from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import ElementType, SlideLayout
from markdowndeck.models.elements.base import Element


@dataclass
class Section:
    """Represents a section in a slide (vertical or horizontal)."""

    content: str = ""
    directives: dict[str, Any] = field(default_factory=dict)
    children: list["Element | Section"] = field(default_factory=list)
    type: str = "section"  # "section" or "row"
    position: tuple[float, float] | None = None
    size: tuple[float, float] | None = None
    id: str | None = None

    def is_row(self) -> bool:
        """Check if this is a row section."""
        return self.type == "row"

    def has_children(self) -> bool:
        """Check if this section has children."""
        return bool(self.children)

    def validate(self) -> bool:
        """
        Validate the section structure.

        Returns:
            True if valid, False otherwise
        """
        return not (self.is_row() and not self.has_children())


@dataclass
class Slide:
    """Represents a slide in a presentation."""

    # REFACTORED: The `elements` list is now the primary inventory of all elements created by the parser.
    # It is used by the LayoutManager and then cleared during finalization.
    elements: list[Element] = field(default_factory=list)
    # REFACTORED: `renderable_elements` is populated by the LayoutManager and OverflowManager and is the
    # final source of truth for the API Generator.
    renderable_elements: list[Element] = field(default_factory=list)

    # REFACTORED: `root_section` is the new single entry point for the slide's body content hierarchy.
    # This aligns with ARCHITECTURE.md Sec 3.
    root_section: Section | None = None
    # REFACTORED: `is_continuation` flag added per DATA_MODELS.md Sec 3.1.
    is_continuation: bool = False

    layout: SlideLayout = SlideLayout.BLANK
    notes: str | None = None
    object_id: str | None = None
    footer: str | None = None
    background: dict[str, Any] | None = None
    title: str = ""  # Store the title text for easier reference
    speaker_notes_object_id: str | None = None

    # REMOVED: `sections`, `title_directives`, `subtitle_directives`, and `placeholder_mappings`
    # are obsolete under the new architecture. Directives are stored directly on elements.

    def __post_init__(self):
        """Extract title from elements for convenience."""
        if not self.title:
            for element in self.elements:
                if element.element_type == ElementType.TITLE:
                    if hasattr(element, "text"):
                        self.title = getattr(element, "text", "")
                    break

    def get_title_element(self) -> Element | None:
        """Get the title element if present."""
        for element in self.elements:
            if element.element_type == ElementType.TITLE:
                return element
        return None

    def get_subtitle_element(self) -> Element | None:
        """Get the subtitle element if present."""
        for element in self.elements:
            if element.element_type == ElementType.SUBTITLE:
                return element
        return None

    def get_footer_element(self) -> Element | None:
        """Get the footer element if present."""
        for element in self.elements:
            if element.element_type == ElementType.FOOTER:
                return element
        return None

    def get_content_elements(self) -> list[Element]:
        """Get all non-title, non-subtitle, non-footer elements."""
        return [
            element
            for element in self.elements
            if element.element_type
            not in (ElementType.TITLE, ElementType.SUBTITLE, ElementType.FOOTER)
        ]

    def find_elements_by_type(self, element_type: ElementType) -> list[Element]:
        """Find all elements of a specific type."""
        return [
            element for element in self.elements if element.element_type == element_type
        ]
