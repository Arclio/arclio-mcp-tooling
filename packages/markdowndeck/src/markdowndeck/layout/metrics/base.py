"""Base metrics utilities for layout calculations."""

import logging

from markdowndeck.models import Element, ElementType

logger = logging.getLogger(__name__)


# Default margins
DEFAULT_MARGINS = {"top": 50, "right": 50, "bottom": 50, "left": 50}

# Default slide dimensions (in points)
DEFAULT_SLIDE_WIDTH = 720
DEFAULT_SLIDE_HEIGHT = 405

# Default element sizes
DEFAULT_ELEMENT_SIZES = {
    ElementType.TITLE: (620, 60),
    ElementType.SUBTITLE: (620, 40),
    ElementType.TEXT: (620, 80),
    ElementType.BULLET_LIST: (620, 200),
    ElementType.ORDERED_LIST: (620, 200),
    ElementType.IMAGE: (300, 200),
    ElementType.TABLE: (620, 200),
    ElementType.CODE: (620, 150),
    ElementType.QUOTE: (620, 100),
    ElementType.FOOTER: (620, 30),
}

# Default spacing
DEFAULT_VERTICAL_SPACING = 20
DEFAULT_HORIZONTAL_SPACING = 15


def get_default_size(element_type: ElementType) -> tuple[float, float]:
    """
    Get the default size for an element type.

    Args:
        element_type: Element type

    Returns:
        Tuple of (width, height)
    """
    return DEFAULT_ELEMENT_SIZES.get(element_type, (620, 80))


def get_element_size(element: Element) -> tuple[float, float]:
    """
    Get the size of an element, using default if not available.

    Args:
        element: Element

    Returns:
        Tuple of (width, height)
    """
    if hasattr(element, "size") and element.size:
        return element.size
    return get_default_size(element.element_type)


def get_max_content_dimensions(
    slide_width: float = DEFAULT_SLIDE_WIDTH,
    slide_height: float = DEFAULT_SLIDE_HEIGHT,
    margins: dict[str, float] = None,
) -> tuple[float, float]:
    """
    Calculate maximum content dimensions based on slide size and margins.

    Args:
        slide_width: Slide width in points
        slide_height: Slide height in points
        margins: Margins dictionary

    Returns:
        Tuple of (max_width, max_height)
    """
    if margins is None:
        margins = DEFAULT_MARGINS

    max_width = slide_width - margins["left"] - margins["right"]
    max_height = slide_height - margins["top"] - margins["bottom"]

    return max_width, max_height
