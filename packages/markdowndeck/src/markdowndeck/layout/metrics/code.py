"""Pure code element metrics for layout calculations - Content-aware height calculation."""

import logging
from typing import cast

from markdowndeck.layout.constants import (
    # Code specific constants
    CODE_FONT_SIZE,
    CODE_LANGUAGE_LABEL_HEIGHT,
    CODE_LINE_HEIGHT_MULTIPLIER,
    CODE_PADDING,
    # Minimum dimensions
    MIN_CODE_HEIGHT,
    MONOSPACE_CHAR_WIDTH,
)
from markdowndeck.models import CodeElement

logger = logging.getLogger(__name__)


def calculate_code_element_height(element: CodeElement | dict, available_width: float) -> float:
    """
    Calculate the pure intrinsic height needed for a code element based on its content.

    This is a pure measurement function that returns the actual height required
    to render the code block at the given width with proper line wrapping.

    Args:
        element: The code element to measure
        available_width: Available width for the code block

    Returns:
        The intrinsic height in points required to render the complete code block
    """
    code_element = cast(CodeElement, element) if isinstance(element, CodeElement) else CodeElement(**element)

    code_content = code_element.code
    language = getattr(code_element, "language", "")

    if not code_content:
        return MIN_CODE_HEIGHT

    # Calculate effective content width (subtract padding)
    content_padding = CODE_PADDING * 2  # Left and right padding
    effective_width = max(10.0, available_width - content_padding)

    # Calculate line height based on code font
    line_height = CODE_FONT_SIZE * CODE_LINE_HEIGHT_MULTIPLIER

    # Calculate how many lines the code will require
    total_lines = _calculate_code_line_count(code_content, effective_width)

    # Calculate content height
    content_height = total_lines * line_height

    # Add language label height if needed
    language_height = 0.0
    if language and language.lower() not in ("text", "plaintext", "plain", ""):
        language_height = CODE_LANGUAGE_LABEL_HEIGHT

    # Calculate total height
    total_height = content_height + CODE_PADDING * 2 + language_height  # Top and bottom padding

    # Apply minimum height
    final_height = max(total_height, MIN_CODE_HEIGHT)

    logger.debug(
        f"Code height calculation: lines={total_lines}, "
        f"line_height={line_height:.1f}, language_height={language_height:.1f}, "
        f"width={available_width:.1f}, final_height={final_height:.1f}"
    )

    return final_height


def _calculate_code_line_count(code_content: str, available_width: float) -> int:
    """
    Calculate how many visual lines the code content will require.

    Args:
        code_content: The code text content
        available_width: Available width for code content

    Returns:
        Number of visual lines needed
    """
    if not code_content.strip():
        return 1

    # Calculate characters per line for monospace font
    chars_per_line = max(1, int(available_width / MONOSPACE_CHAR_WIDTH))

    # Split by explicit newlines
    code_lines = code_content.split("\n")
    total_visual_lines = 0

    for line in code_lines:
        if not line:
            # Empty lines still count as one visual line
            total_visual_lines += 1
        else:
            # Calculate how many visual lines this logical line needs
            line_length = len(line)
            visual_lines_needed = max(1, (line_length + chars_per_line - 1) // chars_per_line)
            total_visual_lines += visual_lines_needed

    return total_visual_lines


def estimate_code_complexity(code_content: str) -> str:
    """
    Estimate the complexity/density of code content.

    Args:
        code_content: The code text content

    Returns:
        Complexity classification: "simple", "moderate", "complex"
    """
    if not code_content.strip():
        return "simple"

    lines = code_content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    if len(non_empty_lines) <= 5:
        return "simple"
    if len(non_empty_lines) <= 15:
        return "moderate"
    return "complex"


def calculate_code_content_width(available_width: float) -> float:
    """
    Calculate the actual content width available inside a code block.

    Args:
        available_width: Total available width for the code element

    Returns:
        Width available for code content (after padding)
    """
    content_padding = CODE_PADDING * 2  # Left and right padding
    return max(10.0, available_width - content_padding)


def estimate_max_line_length(code_content: str) -> int:
    """
    Find the length of the longest line in the code content.

    Args:
        code_content: The code text content

    Returns:
        Length of the longest line in characters
    """
    if not code_content.strip():
        return 0

    lines = code_content.split("\n")
    return max(len(line) for line in lines)


def will_code_require_wrapping(code_content: str, available_width: float) -> bool:
    """
    Determine if the code content will require line wrapping.

    Args:
        code_content: The code text content
        available_width: Available width for the code block

    Returns:
        True if wrapping will be required, False otherwise
    """
    if not code_content.strip():
        return False

    max_line_length = estimate_max_line_length(code_content)
    content_width = calculate_code_content_width(available_width)
    chars_per_line = int(content_width / MONOSPACE_CHAR_WIDTH)

    return max_line_length > chars_per_line
