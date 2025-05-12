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

    # Heuristics for code rendering
    # Monospace fonts are typically wider but more consistent.
    avg_char_width_monospace_pt = 8.0  # Slightly wider than proportional text avg
    line_height_monospace_pt = 16.0  # Typically a bit less than body text due to density
    padding_code_block_pt = 10.0  # Top and bottom padding for the block
    language_label_height_pt = 0.0

    if language and language.lower() != "text":
        language_label_height_pt = 15.0  # Small space for a language label if rendered

    # Effective width for code content inside the block
    effective_code_width = max(1.0, available_width - (2 * 8))  # Assume 8pt L/R internal padding

    num_lines = 0
    for line_text in code_content.split("\n"):
        if not line_text:  # Preserve empty lines in code
            num_lines += 1
        else:
            chars_per_line = max(1, int(effective_code_width / avg_char_width_monospace_pt))
            num_lines += (len(line_text) + chars_per_line - 1) // chars_per_line

    calculated_height = (
        (num_lines * line_height_monospace_pt)
        + (2 * padding_code_block_pt)
        + language_label_height_pt
    )

    final_height = max(calculated_height, 40.0)  # Min height for a code block with some content
    logger.debug(
        f"Code block calculated height: {final_height:.2f}pt "
        f"(lines={num_lines}, lang_label={language_label_height_pt:.0f}, width={available_width:.2f})"
    )
    return final_height


# estimate_max_line_length and estimate_language_display_height can be kept
# if they are used for more detailed layout decisions, but for basic height,
# the logic is now within calculate_code_element_height.
