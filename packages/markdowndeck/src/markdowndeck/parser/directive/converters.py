"""Value converters for directive parsing."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Google Slides theme colors
KNOWN_THEME_COLORS = {
    "TEXT1",
    "TEXT2",
    "BACKGROUND1",
    "BACKGROUND2",
    "ACCENT1",
    "ACCENT2",
    "ACCENT3",
    "ACCENT4",
    "ACCENT5",
    "ACCENT6",
    "HYPERLINK",
    "FOLLOWED_HYPERLINK",
    "DARK1",
    "LIGHT1",
}


def _create_color_value(color_type: str, color_value: str) -> dict[str, Any]:
    """
    Create a standardized color value dictionary.

    Args:
        color_type: Type of color ('hex', 'named', 'theme')
        color_value: The color value

    Returns:
        Standardized color dictionary
    """
    if color_type == "theme":
        return {"type": "theme", "themeColor": color_value}
    if color_type == "hex":
        return {"type": "hex", "value": color_value}
    if color_type == "named":
        return {"type": "named", "value": color_value}
    return {"type": "unknown", "value": color_value}


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


def get_theme_colors() -> set[str]:
    """
    Get a set of valid Google Slides theme color names.

    Returns:
        Set of valid theme color names in uppercase
    """
    return {
        "TEXT1",
        "TEXT2",
        "BACKGROUND1",
        "BACKGROUND2",
        "ACCENT1",
        "ACCENT2",
        "ACCENT3",
        "ACCENT4",
        "ACCENT5",
        "ACCENT6",
        "HYPERLINK",
        "FOLLOWED_HYPERLINK",
        "DARK1",
        "LIGHT1",
        "DARK2",
        "LIGHT2",
    }


def convert_style(value: str) -> tuple[str, Any]:
    """
    Convert style value (color, URL, border style, or generic value) with enhanced support.

    Args:
        value: Style value as string

    Returns:
        Tuple of (type, converted_value) where type indicates the style type
        and converted_value is the processed value in a structured format.
    """
    value = value.strip()
    logger.debug(f"Converting style value: '{value}'")

    # Handle hex colors
    if value.startswith("#"):
        if re.match(r"^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$", value):
            logger.debug(f"Valid hex color: {value}")
            return ("color", _create_color_value("hex", value))
        logger.warning(f"Invalid hex color format: {value}")
        return (
            "color",
            _create_color_value("hex", value),
        )  # Return as-is but mark as color

    # Handle URLs
    url_match = re.match(r"url\(\s*['\"]?([^'\"]*)['\"]?\s*\)", value)
    if url_match:
        url = url_match.group(1).strip()
        logger.debug(f"Extracted URL: {url}")
        return ("url", {"type": "url", "value": url})

    # Handle theme colors (case-insensitive)
    if value.upper() in KNOWN_THEME_COLORS:
        return ("color", _create_color_value("theme", value.upper()))

    # Handle compound border values (e.g., "1pt solid #FF0000", "2px dashed ACCENT1")
    border_match = re.match(
        r"^(\d+(?:\.\d+)?(?:pt|px|em|rem|%))\s+(solid|dashed|dotted|double|groove|ridge|inset|outset)\s+(.+)$",
        value,
        re.IGNORECASE,
    )
    if border_match:
        width_str, style_str, color_str = border_match.groups()

        # Parse the color component recursively
        color_type, color_value = convert_style(color_str.strip())

        # Ensure color_value is in the right format
        color_data = (
            color_value
            if color_type == "color"
            else {"type": "unknown", "value": color_value}
        )

        border_info = {
            "width": width_str,
            "style": style_str.lower(),
            "color": color_data,
        }
        logger.debug(f"Parsed compound border: {border_info}")
        return ("border", border_info)

    # Handle simple border styles (for backward compatibility)
    simple_border_styles = {
        "solid",
        "dashed",
        "dotted",
        "double",
        "groove",
        "ridge",
        "inset",
        "outset",
    }
    if value.lower() in simple_border_styles:
        return ("border_style", value.lower())

    # Handle named colors
    color_names = get_color_names()
    if value.lower() in color_names:
        logger.debug(f"Named color: {value}")
        return ("color", _create_color_value("named", value.lower()))

    # Handle other style values - return as generic value
    logger.debug(f"Generic style value: {value}")
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
