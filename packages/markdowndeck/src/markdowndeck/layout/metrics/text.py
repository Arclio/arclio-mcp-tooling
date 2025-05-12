"""Text element metrics for layout calculations."""

import logging
import re

from markdowndeck.models import ElementType, TextElement, TextFormatType

logger = logging.getLogger(__name__)


def calculate_text_element_height(
    element: TextElement | dict, available_width: float
) -> float:
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

    # Handle empty content
    if not text_content:
        return 20  # Minimal height for an empty text element

    # For footers, strip HTML comments (speaker notes) before calculating height
    if element_type == ElementType.FOOTER:
        text_content = re.sub(r"<!--.*?-->", "", text_content, flags=re.DOTALL)
        # Use a fixed height for footers regardless of content
        return 30.0  # Fixed footer height

    # OPTIMIZED: Reduced parameters for all element types
    if element_type == ElementType.TITLE:
        avg_char_width_pt = 5.5  # Reduced from 6.0
        line_height_pt = 20.0  # Reduced from 24.0
        padding_pt = 5.0  # Reduced from 8.0
        min_height = 30.0  # Reduced from 40.0
        max_height = 50.0  # Reduced from 60.0
    elif element_type == ElementType.SUBTITLE:
        avg_char_width_pt = 5.0  # Reduced from 5.5
        line_height_pt = 18.0  # Reduced from 20.0
        padding_pt = 4.0  # Reduced from 6.0
        min_height = 25.0  # Reduced from 35.0
        max_height = 40.0  # Reduced from 50.0
    elif element_type == ElementType.QUOTE:
        avg_char_width_pt = 5.0  # Unchanged
        line_height_pt = 16.0  # Reduced from 18.0
        padding_pt = 8.0  # Reduced from 10.0
        min_height = 25.0  # Reduced from 30.0
        max_height = 120.0  # Reduced from 150.0
    else:  # Default for all other text elements
        avg_char_width_pt = 5.0  # Unchanged
        line_height_pt = 14.0  # Reduced from 16.0
        padding_pt = 3.0  # Reduced from 4.0
        min_height = 18.0  # Reduced from 20.0
        max_height = 250.0  # Reduced from 300.0

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
            lines_needed = (
                text_length + chars_per_line - 1
            ) // chars_per_line  # Ceiling division
            line_count += lines_needed

    # OPTIMIZED: Minimal adjustments for formatting
    if formatting and any(fmt.format_type == TextFormatType.CODE for fmt in formatting):
        line_count *= 1.02  # Very minor increase (reduced from 1.05)

    # Calculate final height with minimal padding
    calculated_height = (line_count * line_height_pt) + padding_pt  # Single padding

    # Apply reasonable min/max constraints
    final_height = max(min_height, min(calculated_height, max_height))

    logger.debug(
        f"Calculated height for {element_type}: {final_height:.2f}pt "
        f"(text_len={len(text_content)}, lines={line_count}, width={available_width:.2f})"
    )

    return final_height
