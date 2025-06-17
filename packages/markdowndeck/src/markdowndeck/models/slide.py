from dataclasses import dataclass, field
from typing import Any

from markdowndeck.models.constants import ElementType, SlideLayout
from markdowndeck.models.elements.base import Element


@dataclass
class Section:
    """Represents a section in a slide (vertical or horizontal)."""

    directives: dict[str, Any] = field(default_factory=dict)
    # REFACTORED: This list temporarily holds `str` for raw content during parsing,
    # which is then replaced by `Element` objects by the ContentParser.
    children: list[Any] = field(default_factory=list)
    type: str = "section"  # "section", "row", or "column"
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
    """Represents a slide in a presentation - Updated for specification compliance."""

    # Core data structure per DATA_MODELS.md
    elements: list[Element] = field(default_factory=list)
    renderable_elements: list[Element] = field(default_factory=list)
    root_section: Section | None = None
    is_continuation: bool = False
    continuation_context_title: str | None = None

    # Standard slide properties
    layout: SlideLayout = SlideLayout.BLANK
    notes: str | None = None
    object_id: str | None = None
    background: dict[str, Any] | None = None
    speaker_notes_object_id: str | None = None

    # ADDED: Directive storage attributes per DATA_MODELS.md
    title_directives: dict[str, Any] = field(default_factory=dict)
    subtitle_directives: dict[str, Any] = field(default_factory=dict)
    footer_directives: dict[str, Any] = field(default_factory=dict)
    base_directives: dict[str, Any] = field(default_factory=dict)

    def get_title_element(self) -> Element | None:
        """Get the title element if present, searching authoritative lists first."""
        for element in self.renderable_elements:
            if element.element_type == ElementType.TITLE:
                return element
        for element in self.elements:
            if element.element_type == ElementType.TITLE:
                return element
        return None

    def get_subtitle_element(self) -> Element | None:
        """Get the subtitle element if present, searching authoritative lists first."""
        for element in self.renderable_elements:
            if element.element_type == ElementType.SUBTITLE:
                return element
        for element in self.elements:
            if element.element_type == ElementType.SUBTITLE:
                return element
        return None

    def get_footer_element(self) -> Element | None:
        """Get the footer element if present, searching authoritative lists first."""
        for element in self.renderable_elements:
            if element.element_type == ElementType.FOOTER:
                return element
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

    @property
    def title(self) -> str:
        """Get title text from title element (for backward compatibility)."""
        title_element = self.get_title_element()
        return getattr(title_element, "text", "") if title_element else ""

    @property
    def footer(self) -> str | None:
        """Get footer text from footer element (for backward compatibility)."""
        footer_element = self.get_footer_element()
        return getattr(footer_element, "text", None) if footer_element else None
