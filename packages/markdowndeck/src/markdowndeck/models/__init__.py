"""Models for representing slides and presentation elements."""

# Re-export model classes for backward compatibility
from markdowndeck.models.constants import (
    AlignmentType,
    ElementType,
    SlideLayout,
    TextFormatType,
    VerticalAlignmentType,
)
from markdowndeck.models.deck import Deck
from markdowndeck.models.elements.base import Element
from markdowndeck.models.elements.code import CodeElement
from markdowndeck.models.elements.list import ListElement, ListItem
from markdowndeck.models.elements.media import ImageElement
from markdowndeck.models.elements.table import TableElement
from markdowndeck.models.elements.text import TextElement, TextFormat
from markdowndeck.models.slide import Section, Slide

# Keep all imports here to avoid circular dependencies
__all__ = [
    "AlignmentType",
    "CodeElement",
    "Deck",
    "Element",
    "ElementType",
    "ImageElement",
    "ListElement",
    "ListItem",
    "Section",
    "Slide",
    "SlideLayout",
    "TableElement",
    "TextElement",
    "TextFormat",
    "TextFormatType",
    "VerticalAlignmentType",
]
