"""Constants and enums for the markdowndeck package."""

from enum import Enum


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
    FOOTER = "footer"


class TextFormatType(str, Enum):
    """Types of text formatting."""

    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    CODE = "code"
    LINK = "link"
    COLOR = "color"  # Represents foreground color
    BACKGROUND_COLOR = "backgroundColor"  # Added
    FONT_SIZE = "fontSize"  # Added
    FONT_FAMILY = "fontFamily"  # Added
    VERTICAL_ALIGN = "verticalAlign"  # Represents baselineOffset (superscript/subscript) - Added


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
