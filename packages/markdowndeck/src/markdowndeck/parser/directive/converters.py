"""Value converters for directive parsing."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def convert_dimension(value: str) -> float:
    """
    Convert dimension value (fraction, percentage, or value) with improved handling.

    Args:
        value: Dimension as string (e.g., "2/3", "50%", "300")

    Returns:
        Normalized float value between 0 and 1 for fractions/percentages,
        or absolute value for pixel-like values.
    """
    value = value.strip()  # Ensure no leading/trailing spaces
    logger.debug(f"Converting dimension value: '{value}'")

    # Handle fraction values (e.g., 2/3)
    if "/" in value:
        parts = value.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                denom = float(parts[1].strip())
            # Catch original error and chain it
            except ValueError as e:  # Catch only conversion errors
                raise ValueError(f"Invalid fraction format: '{value}'") from e

            # Check for division by zero
            if denom == 0:
                logger.warning(f"Division by zero in dimension value: '{value}'")
                # Raise the specific error the test expects
                raise ValueError("division by zero")

            # Perform division *after* checks
            return num / denom
        # Handle cases like "1/2/3"
        raise ValueError(f"Invalid fraction format: '{value}'")

    # Handle percentage values (e.g., 50%)
    if value.endswith("%"):
        percentage_str = value.rstrip("%").strip()
        logger.debug(f"Parsed percentage string: '{percentage_str}'")
        try:
            percentage = float(percentage_str)
            logger.debug(f"Converted percentage: {percentage}%")
            return percentage / 100.0
        # Catch original error and chain it
        except ValueError as e:
            logger.warning(f"Invalid percentage format: '{value}'")
            raise ValueError(f"Invalid dimension format: '{value}'") from e

    # Handle numeric values (pixels)
    try:
        numeric_value = value.strip()
        logger.debug(f"Parsing as numeric value: '{numeric_value}'")
        # First try as int, then as float
        if numeric_value.isdigit():
            return int(numeric_value)
        return float(numeric_value)
    # Catch original error and chain it
    except ValueError as e:
        logger.warning(f"Invalid numeric format: '{value}'")
        raise ValueError(f"Invalid dimension format: '{value}'") from e


def convert_alignment(value: str) -> str:
    """
    Convert alignment value.

    Args:
        value: Alignment as string (e.g., "center", "right")

    Returns:
        Normalized alignment value
    """
    value = value.strip().lower()  # Ensure stripped and lower case
    valid_alignments = [
        "left",
        "center",
        "right",
        "justify",
        "top",
        "middle",
        "bottom",
    ]

    if value in valid_alignments:
        return value

    # Handle aliases
    aliases = {
        "start": "left",
        "end": "right",
        "centered": "center",
        "justified": "justify",
    }

    if value in aliases:
        return aliases[value]

    # Return as-is if not recognized, but log warning
    logger.warning(f"Unrecognized alignment value: '{value}', using as is.")
    return value


def convert_style(value: str) -> tuple[str, Any]:
    """
    Convert style value with improved handling.

    Args:
        value: Style as string (e.g., "#f5f5f5", "url(image.jpg)")

    Returns:
        Tuple of (type, value)
    """
    value = value.strip()  # Ensure stripped

    # Handle colors with improved validation
    color_names = get_color_names()
    if value.startswith("#") or value.lower() in color_names:
        # If it's a hex color, validate the format
        if value.startswith("#") and not re.fullmatch(
            r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{1,5})?", value
        ):
            logger.warning(f"Invalid hex color format: '{value}', using as is.")
        # Return for all colors
        return ("color", value)

    # Handle URLs with improved pattern matching
    url_match = re.fullmatch(r"url\(\s*['\"]?(.+?)['\"]?\s*\)", value, re.IGNORECASE)
    if url_match:
        url = url_match.group(1)
        return ("url", url)

    # Handle other style values
    if value in ["solid", "dashed", "dotted", "none", "hidden"]:
        return ("border-style", value)

    # Return as-is for other values
    logger.debug(f"Directive style value '{value}' treated as generic value.")
    return ("value", value)


def get_color_names() -> set[str]:
    """
    Get a set of valid CSS color names.

    Returns:
        Set of valid color names
    """
    # Common color names (non-exhaustive list)
    return {
        "black",
        "white",
        "red",
        "green",
        "blue",
        "yellow",
        "orange",
        "purple",
        "pink",
        "brown",
        "gray",
        "grey",
        "silver",
        "gold",
        "transparent",
        "aqua",
        "teal",
        "navy",
        "olive",
        "maroon",
        "lime",
        "fuchsia",
    }
