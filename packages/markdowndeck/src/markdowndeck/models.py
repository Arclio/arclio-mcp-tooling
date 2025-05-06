from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SlideLayout(str, Enum):
    """Predefined slide layouts in Google Slides."""

    TITLE = "TITLE"
    TITLE_AND_BODY = "TITLE_AND_BODY"
    TITLE_AND_TWO_COLUMNS = "TITLE_AND_TWO_COLUMNS"
    TITLE_ONLY = "TITLE_ONLY"
    BLANK = "BLANK"
    SECTION_HEADER = "SECTION_HEADER"
    CAPTION_ONLY = "CAPTION_ONLY"
    BIG_NUMBER = "BIG_NUMBER"


class ElementType(str, Enum):
    """Types of elements that can be added to a slide."""

    TITLE = "title"
    SUBTITLE = "subtitle"
    TEXT = "text"
    BULLET_LIST = "bullet_list"
    ORDERED_LIST = "ordered_list"
    IMAGE = "image"
    TABLE = "table"
    CODE = "code"
    QUOTE = "quote"
    FOOTER = "footer"  # Added footer type


class TextFormatType(str, Enum):
    """Types of text formatting."""

    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    CODE = "code"
    LINK = "link"
    COLOR = "color"  # Added color formatting


class AlignmentType(str, Enum):
    """Types of alignment for text and elements."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class VerticalAlignmentType(str, Enum):
    """Types of vertical alignment for elements."""

    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


@dataclass
class TextFormat:
    """Text formatting information."""

    start: int
    end: int
    format_type: TextFormatType
    value: Any = True  # Boolean for bold/italic or values for colors/links


@dataclass
class ListItem:
    """Represents an item in a list with optional nested items."""

    text: str
    level: int = 0
    formatting: list[TextFormat] = field(default_factory=list)
    children: list["ListItem"] = field(default_factory=list)


@dataclass
class Section:
    """Represents a section in a slide (vertical or horizontal)."""

    content: str = ""
    directives: dict[str, Any] = field(default_factory=dict)
    subsections: list["Section"] = field(default_factory=list)
    type: str = "section"  # "section" or "row"
    elements: list["Element"] = field(default_factory=list)
    position: tuple[float, float] | None = None
    size: tuple[float, float] | None = None


@dataclass
class Element:
    """Base class for slide elements."""

    element_type: ElementType
    position: tuple[float, float] = field(default_factory=lambda: (100, 100))
    size: tuple[float, float] = field(default_factory=lambda: (600, 100))
    object_id: str | None = None
    directives: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextElement(Element):
    """Text element (title, subtitle, paragraph, etc.)."""

    text: str = ""
    formatting: list[TextFormat] = field(default_factory=list)
    horizontal_alignment: AlignmentType = AlignmentType.LEFT
    vertical_alignment: VerticalAlignmentType = VerticalAlignmentType.TOP


@dataclass
class ListElement(Element):
    """List element (bullet list, ordered list)."""

    items: list[ListItem] = field(default_factory=list)


@dataclass
class ImageElement(Element):
    """Image element."""

    url: str = ""
    alt_text: str = ""


@dataclass
class TableElement(Element):
    """Table element."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class CodeElement(Element):
    """Code block element."""

    code: str = ""
    language: str = "text"


@dataclass
class Slide:
    """Represents a slide in a presentation."""

    elements: list[Element] = field(default_factory=list)
    layout: SlideLayout = SlideLayout.TITLE_AND_BODY
    notes: str | None = None
    object_id: str | None = None
    footer: str | None = None  # Added footer support
    sections: list[Section] = field(default_factory=list)  # Added sections support
    background: dict[str, Any] | None = None  # Added background support


@dataclass
class Deck:
    """Represents a complete presentation."""

    slides: list[Slide] = field(default_factory=list)
    title: str = "Untitled Presentation"
    theme_id: str | None = None
