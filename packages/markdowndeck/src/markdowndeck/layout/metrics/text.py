"""Pure text element metrics for layout calculations - Content-aware height calculation."""

import logging
import re

from markdowndeck.layout.constants import (
    FOOTER_FONT_SIZE,
    # Font sizes
    H1_FONT_SIZE,
    # Line height multipliers
    H1_LINE_HEIGHT_MULTIPLIER,
    H2_FONT_SIZE,
    H2_LINE_HEIGHT_MULTIPLIER,
    H3_FONT_SIZE,
    H4_FONT_SIZE,
    H5_FONT_SIZE,
    H6_FONT_SIZE,
    MIN_QUOTE_HEIGHT,
    MIN_SUBTITLE_HEIGHT,
    MIN_TEXT_HEIGHT,
    # Minimum heights
    MIN_TITLE_HEIGHT,
    P_FONT_SIZE,
    P_LINE_HEIGHT_MULTIPLIER,
    QUOTE_PADDING,
    # Character widths
    STANDARD_CHAR_WIDTH,
    SUBTITLE_PADDING,
    TEXT_PADDING,
    TITLE_CHAR_WIDTH,
    # Padding
    TITLE_PADDING,
)
from markdowndeck.models import ElementType, TextElement

logger = logging.getLogger(__name__)


def calculate_text_element_height(
    element: TextElement | dict, available_width: float
) -> float:
    """
    Calculate the pure intrinsic height needed for a text element based on its content.

    This is a pure measurement function that returns the actual height required
    to render the element's content at the given width. It does not apply any
    constraints or attempt to fit content within boundaries.

    Args:
        element: The text element to measure
        available_width: Available width for the element

    Returns:
        The intrinsic height in points required to render the content
    """
    # Extract element properties
    element_type = getattr(
        element,
        "element_type",
        element.get("element_type") if isinstance(element, dict) else ElementType.TEXT,
    )
    text_content = getattr(
        element, "text", element.get("text") if isinstance(element, dict) else ""
    )
    directives = getattr(
        element,
        "directives",
        element.get("directives") if isinstance(element, dict) else {},
    )

    # Handle empty content
    if not text_content:
        return _get_minimum_height_for_type(element_type)

    # For footers, strip HTML comments (speaker notes) before calculating height
    if element_type == ElementType.FOOTER:
        text_content = re.sub(r"<!--.*?-->", "", text_content, flags=re.DOTALL)
        text_content = text_content.strip()
        if not text_content:
            return _get_minimum_height_for_type(element_type)

    # Get typography parameters for this element type
    font_size, line_height_multiplier, char_width, padding, min_height = (
        _get_typography_params(element_type)
    )

    # Apply font size directive if present
    if directives and "fontsize" in directives:
        try:
            custom_font_size = float(directives["fontsize"])
            if custom_font_size > 0:
                font_size = custom_font_size
                # Recalculate minimum height based on custom font size
                min_height = max(min_height, font_size * 1.5 + padding)
                logger.debug(f"Applied custom font size: {font_size}pt")
        except (ValueError, TypeError):
            logger.warning(f"Invalid fontsize directive: {directives['fontsize']}")

    # Calculate actual line height
    line_height = font_size * line_height_multiplier

    # Calculate effective width (subtract minimal border padding)
    effective_width = max(10.0, available_width - 4.0)  # 2pt padding on each side

    # Calculate how many lines the text will require
    total_lines = _calculate_line_count(text_content, effective_width, char_width)

    # Calculate total height: lines * line_height + padding
    content_height = total_lines * line_height
    total_height = content_height + padding

    # Apply minimum height constraint
    final_height = max(total_height, min_height)

    logger.debug(
        f"Text height calculation: type={element_type}, "
        f"content_length={len(text_content)}, lines={total_lines}, "
        f"line_height={line_height:.1f}, final_height={final_height:.1f}"
    )

    return final_height


def _get_typography_params(
    element_type: ElementType,
) -> tuple[float, float, float, float, float]:
    """
    Get typography parameters for a specific element type.

    Returns:
        (font_size, line_height_multiplier, char_width, padding, min_height)
    """
    if element_type == ElementType.TITLE:
        return (
            H1_FONT_SIZE,
            H1_LINE_HEIGHT_MULTIPLIER,
            TITLE_CHAR_WIDTH,
            TITLE_PADDING,
            MIN_TITLE_HEIGHT,
        )
    if element_type == ElementType.SUBTITLE:
        return (
            H2_FONT_SIZE,
            H2_LINE_HEIGHT_MULTIPLIER,
            STANDARD_CHAR_WIDTH,
            SUBTITLE_PADDING,
            MIN_SUBTITLE_HEIGHT,
        )
    if element_type == ElementType.QUOTE:
        return (
            P_FONT_SIZE,
            P_LINE_HEIGHT_MULTIPLIER,
            STANDARD_CHAR_WIDTH,
            QUOTE_PADDING,
            MIN_QUOTE_HEIGHT,
        )
    if element_type == ElementType.FOOTER:
        return (
            FOOTER_FONT_SIZE,
            P_LINE_HEIGHT_MULTIPLIER,
            STANDARD_CHAR_WIDTH,
            TEXT_PADDING,
            20.0,
        )  # Footer minimum
    # Default for TEXT and other types
    return (
        P_FONT_SIZE,
        P_LINE_HEIGHT_MULTIPLIER,
        STANDARD_CHAR_WIDTH,
        TEXT_PADDING,
        MIN_TEXT_HEIGHT,
    )


def _get_minimum_height_for_type(element_type: ElementType) -> float:
    """Get the minimum height for an element type."""
    minimums = {
        ElementType.TITLE: MIN_TITLE_HEIGHT,
        ElementType.SUBTITLE: MIN_SUBTITLE_HEIGHT,
        ElementType.QUOTE: MIN_QUOTE_HEIGHT,
        ElementType.FOOTER: 20.0,
        ElementType.TEXT: MIN_TEXT_HEIGHT,
    }
    return minimums.get(element_type, MIN_TEXT_HEIGHT)


def _calculate_line_count(text: str, available_width: float, char_width: float) -> int:
    """
    Calculate how many lines the text will require for the given width.

    Args:
        text: The text content
        available_width: Available width in points
        char_width: Average character width in points

    Returns:
        Number of lines required
    """
    if not text.strip():
        return 1  # Empty text still takes one line

    # Calculate characters per line
    chars_per_line = max(1, available_width // char_width)

    # Split by explicit newlines first
    lines = text.split("\n")
    total_lines = 0

    for line in lines:
        if not line.strip():
            # Empty lines still count
            total_lines += 1
        else:
            # Calculate how many visual lines this logical line needs
            line_length = len(line)
            lines_needed = max(1, (line_length + chars_per_line - 1) // chars_per_line)
            total_lines += lines_needed

    return total_lines


def _detect_heading_level(text: str) -> int:
    """
    Detect heading level from markdown syntax.

    Args:
        text: Text content that might start with #

    Returns:
        Heading level (1-6) or 0 if not a heading
    """
    stripped = text.strip()
    if not stripped.startswith("#"):
        return 0

    level = 0
    for char in stripped:
        if char == "#":
            level += 1
        else:
            break

    return min(level, 6)  # Cap at h6


def get_heading_typography_params(heading_level: int) -> tuple[float, float]:
    """
    Get font size and line height multiplier for a heading level.

    Args:
        heading_level: Heading level (1-6)

    Returns:
        (font_size, line_height_multiplier)
    """
    heading_fonts = {
        1: (H1_FONT_SIZE, H1_LINE_HEIGHT_MULTIPLIER),
        2: (H2_FONT_SIZE, H2_LINE_HEIGHT_MULTIPLIER),
        3: (H3_FONT_SIZE, P_LINE_HEIGHT_MULTIPLIER),
        4: (H4_FONT_SIZE, P_LINE_HEIGHT_MULTIPLIER),
        5: (H5_FONT_SIZE, P_LINE_HEIGHT_MULTIPLIER),
        6: (H6_FONT_SIZE, P_LINE_HEIGHT_MULTIPLIER),
    }
    return heading_fonts.get(heading_level, (P_FONT_SIZE, P_LINE_HEIGHT_MULTIPLIER))
