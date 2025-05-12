"""Code element metrics for layout calculations."""

import logging
from typing import cast

from markdowndeck.models import (
    CodeElement,
)  # Keep TextElement if using text_height_calculator for language label

logger = logging.getLogger(__name__)


def calculate_code_element_height(element: CodeElement | dict, available_width: float) -> float:
    """
    Calculate the height needed for a code element.

    Args:
        element: The code element or dict.
        available_width: Available width for the code block.

    Returns:
        Calculated height in points.
    """
    code_element = (
        cast(CodeElement, element) if isinstance(element, CodeElement) else CodeElement(**element)
    )
    code_content = code_element.code
    language = code_element.language

    if not code_content:
        return 30  # Min height for an empty code block

    # OPTIMIZED: Reduced parameters for more efficient space usage
    avg_char_width_monospace_pt = 7.5  # Reduced from 8.0
    line_height_monospace_pt = 14.0  # Reduced from 16.0
    padding_code_block_pt = 8.0  # Reduced from 10.0

    # OPTIMIZED: Reduced or eliminated language label height
    language_label_height_pt = 0.0
    if language and language.lower() not in ("text", "plaintext", "plain"):
        language_label_height_pt = 12.0  # Reduced from 15.0

    # OPTIMIZED: Reduced internal padding for more usable width
    effective_code_width = max(1.0, available_width - (2 * 6))  # Reduced from 8pt L/R padding

    # Count lines more efficiently
    num_lines = 0
    for line_text in code_content.split("\n"):
        if not line_text:  # Preserve empty lines in code
            num_lines += 1
        else:
            # OPTIMIZED: More accurate character counting
            chars_per_line = max(1, int(effective_code_width / avg_char_width_monospace_pt))
            num_lines += (len(line_text) + chars_per_line - 1) // chars_per_line

    # Calculate total height with reduced padding
    calculated_height = (
        (num_lines * line_height_monospace_pt)
        + padding_code_block_pt  # Single padding (not 2x)
        + language_label_height_pt
    )

    # OPTIMIZED: Reduced minimum height
    final_height = max(calculated_height, 35.0)  # Reduced from 40.0
    logger.debug(
        f"Code block calculated height: {final_height:.2f}pt "
        f"(lines={num_lines}, lang_label={language_label_height_pt:.0f}, width={available_width:.2f})"
    )
    return final_height


# estimate_max_line_length and estimate_language_display_height can be kept
# if they are used for more detailed layout decisions, but for basic height,
# the logic is now within calculate_code_element_height.
