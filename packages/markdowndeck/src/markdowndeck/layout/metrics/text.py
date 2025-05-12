"""Text element metrics for layout calculations."""

import logging
import re

from markdowndeck.layout.constants import (
    DEFAULT_TEXT_PADDING,
    QUOTE_PADDING,
    SUBTITLE_PADDING,
    TITLE_PADDING,
)
from markdowndeck.models import ElementType, TextElement, TextFormatType

logger = logging.getLogger(__name__)


def calculate_text_element_height(element: TextElement | dict, available_width: float) -> float:
    """
    Calculate the height needed for a text element based on its content.

    Args:
        element: The text element to calculate height for
        available_width: Available width for the element

    Returns:
        Calculated height in points
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
    formatting = getattr(
        element,
        "formatting",
        element.get("formatting") if isinstance(element, dict) else [],
    )
    directives = getattr(
        element,
        "directives",
        element.get("directives") if isinstance(element, dict) else {},
    )

    # Handle empty content
    if not text_content:
        return 20  # Minimal height for an empty text element

    # For footers, strip HTML comments (speaker notes) before calculating height
    if element_type == ElementType.FOOTER:
        text_content = re.sub(r"<!--.*?-->", "", text_content, flags=re.DOTALL)
        # Use a fixed height for footers regardless of content
        return 30.0  # Fixed footer height

    # OPTIMIZED: Use standardized constants for padding
    if element_type == ElementType.TITLE:
        avg_char_width_pt = 5.5
        line_height_pt = 20.0
        padding_pt = TITLE_PADDING
        min_height = 30.0
        max_height = 50.0
    elif element_type == ElementType.SUBTITLE:
        avg_char_width_pt = 5.0
        line_height_pt = 18.0
        padding_pt = SUBTITLE_PADDING
        min_height = 25.0
        max_height = 40.0
    elif element_type == ElementType.QUOTE:
        avg_char_width_pt = 5.0
        line_height_pt = 16.0
        padding_pt = QUOTE_PADDING
        min_height = 25.0
        max_height = 120.0
    else:  # Default for all other text elements
        avg_char_width_pt = 5.0
        line_height_pt = 14.0
        padding_pt = DEFAULT_TEXT_PADDING
        min_height = 18.0
        max_height = 250.0

    # FIXED: Adjust minimum height based on font size directive
    if directives and "fontsize" in directives:
        try:
            fontsize = float(directives["fontsize"])
            # Ensure minimum height is at least 120% of font size plus padding
            font_based_min_height = fontsize * 1.2 + padding_pt
            min_height = max(min_height, font_based_min_height)
            # Also scale line height based on font size
            line_height_pt = max(line_height_pt, fontsize * 1.1)
            logger.debug(f"Adjusted min height to {min_height} based on fontsize={fontsize}")
        except (ValueError, TypeError):
            logger.warning(f"Invalid fontsize directive: {directives['fontsize']}")

    # For headings (determined by leading #), ensure reasonable minimum height
    if text_content.strip().startswith("#"):
        heading_level = 0
        for char in text_content.strip():
            if char == "#":
                heading_level += 1
            else:
                break

        if 1 <= heading_level <= 6:
            heading_min_height = 30 - (heading_level * 2)  # h1=28, h2=26, etc.
            min_height = max(min_height, heading_min_height)
            logger.debug(f"Set minimum height {min_height} for heading level {heading_level}")

    # OPTIMIZED: Calculate effective width with minimal internal padding
    effective_width = max(1.0, available_width - 4.0)  # Reduced from 6.0

    # OPTIMIZED: More efficient line counting algorithm
    lines = text_content.split("\n")
    line_count = 0

    for line in lines:
        if not line.strip():  # Empty line
            line_count += 1
        else:
            # Calculate characters per line based on available width
            chars_per_line = max(1, int(effective_width / avg_char_width_pt))

            # Simple line wrapping calculation
            text_length = len(line)
            lines_needed = (text_length + chars_per_line - 1) // chars_per_line  # Ceiling division
            line_count += max(1, lines_needed)  # Ensure at least 1 line

    # OPTIMIZED: Minimal adjustments for formatting
    if formatting and any(fmt.format_type == TextFormatType.CODE for fmt in formatting):
        line_count *= 1.02  # Very minor increase (reduced from 1.05)

    # Calculate final height with minimal padding
    calculated_height = (line_count * line_height_pt) + padding_pt  # Single padding

    # FIXED: Ensure absolute minimum height for all text elements
    calculated_height = max(calculated_height, min_height)

    # Apply reasonable min/max constraints
    final_height = max(min_height, min(calculated_height, max_height))

    # Verify height is reasonable (at least 8px for any visible text)
    if final_height < 8.0 and text_content.strip():
        final_height = max(final_height, 16.0)
        logger.warning(
            f"Adjusted unrealistically small text height from {final_height} to minimum 16pt"
        )

    logger.debug(
        f"Calculated height for {element_type}: {final_height:.2f}pt "
        f"(text_len={len(text_content)}, lines={line_count}, width={available_width:.2f})"
    )

    return final_height
