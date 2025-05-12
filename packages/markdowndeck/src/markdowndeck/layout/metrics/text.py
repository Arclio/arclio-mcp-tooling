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

    # Set base parameters based on element type - REVISED VALUES BASED ON REAL PRESENTATION TOOLS
    if element_type == ElementType.TITLE:
        avg_char_width_pt = (
            6.0  # More realistic character width for titles (using ~24pt font)
        )
        line_height_pt = 24.0  # Slightly reduced from 28pt
        padding_pt = 8.0  # Reduced from 15pt
        min_height = 30.0  # Reduced from 40pt
        max_height = 60.0  # Maintained max height
    elif element_type == ElementType.SUBTITLE:
        avg_char_width_pt = (
            5.5  # More realistic character width for subtitles (using ~20pt font)
        )
        line_height_pt = 20.0  # Reduced from 24pt
        padding_pt = 6.0  # Reduced from 12pt
        min_height = 25.0  # Reduced from 35pt
        max_height = 50.0  # Maintained max height
    elif element_type == ElementType.QUOTE:
        avg_char_width_pt = 5.0  # More realistic character width for quotes
        line_height_pt = 18.0  # Reduced from 20pt
        padding_pt = 10.0  # Reduced from 20pt
        min_height = 30.0  # Reduced from 40pt
        max_height = 150.0  # Reduced from 200pt
    else:  # Default for all other text elements
        avg_char_width_pt = (
            5.0  # More realistic character width for body text (using ~14-16pt font)
        )
        line_height_pt = 16.0  # Reduced from 18pt
        padding_pt = 4.0  # Reduced from 10pt
        min_height = 20.0  # Reduced from 30pt
        max_height = 300.0  # Reduced from 500pt

    # Calculate effective width (accounting for internal padding)
    effective_width = max(
        1.0, available_width - 6.0
    )  # Reduced internal padding from 10pt to 6pt

    # Use word-based line counting for more accurate wrap calculation
    lines = text_content.split("\n")
    line_count = 0

    for line in lines:
        if not line.strip():  # Empty line
            line_count += 1
        else:
            # Split into words and calculate word-based wrapping
            words = line.split()
            if not words:
                line_count += 1
                continue

            current_line_width = 0
            for word in words:
                # Average word length (including trailing space)
                word_width = (
                    len(word) * avg_char_width_pt + avg_char_width_pt
                )  # Add space

                if current_line_width + word_width <= effective_width:
                    # Word fits on current line
                    current_line_width += word_width
                else:
                    # Word requires a new line
                    line_count += 1
                    current_line_width = word_width

            # Count the last line
            line_count += 1

    # Adjust for formatting if needed (reduced impact)
    if formatting and any(fmt.format_type == TextFormatType.CODE for fmt in formatting):
        line_count *= 1.05  # Reduced from 10% to 5% height increase for code formatting

    # Calculate final height with padding
    calculated_height = (
        line_count * line_height_pt
    ) + padding_pt  # Reduced from 2*padding_pt

    # Apply min/max constraints
    final_height = max(min_height, min(calculated_height, max_height))

    logger.debug(
        f"Calculated height for {element_type}: {final_height:.2f}pt "
        f"(text_len={len(text_content)}, lines={line_count}, width={available_width:.2f})"
    )

    return final_height
