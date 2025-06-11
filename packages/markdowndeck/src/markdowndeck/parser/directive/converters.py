"""Enhanced value converters for directive parsing."""

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
    "DARK2",
    "LIGHT2",
}

# Extended CSS color names for P8 enhancement
EXTENDED_COLOR_NAMES = {
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
    # Additional web colors
    "darkred",
    "darkgreen",
    "darkblue",
    "lightred",
    "lightgreen",
    "lightblue",
    "crimson",
    "coral",
    "salmon",
    "khaki",
    "violet",
    "indigo",
    "cyan",
    "magenta",
    "turquoise",
    "plum",
    "orchid",
    "tan",
    "beige",
    "ivory",
}


def _create_color_value(color_type: str, color_value: str | dict) -> dict[str, Any]:
    """Create a standardized color value dictionary."""
    if color_type == "theme":
        return {"type": "theme", "themeColor": color_value}
    if color_type == "hex":
        return {"type": "hex", "value": color_value}
    if color_type == "named":
        return {"type": "named", "value": color_value}
    if color_type == "rgba":
        return {"type": "rgba", **color_value}
    if color_type == "hsla":
        return {"type": "hsla", **color_value}
    return {"type": "unknown", "value": color_value}


def convert_dimension(value: str) -> float | tuple[float, ...]:
    """
    Convert dimension value, now supporting multi-value strings for spacing.
    """
    value = value.strip()

    # Handle multi-value strings (e.g., "10,20" or "10, 20, 10, 20")
    if "," in value:
        try:
            parts = [float(p.strip()) for p in value.split(",")]
            return tuple(parts)
        except ValueError as e:
            raise ValueError(f"Invalid multi-value dimension format: '{value}'") from e

    # Handle CSS units (strip and process separately if needed)
    css_unit_pattern = r"^([\d.]+)(px|pt|em|rem|%|in|cm|mm|vh|vw)?$"
    css_match = re.match(css_unit_pattern, value)

    if css_match:
        numeric_part = css_match.group(1)
        unit = css_match.group(2) or ""
        try:
            numeric_value = float(numeric_part)
            if unit == "%":
                return numeric_value / 100.0
            return numeric_value
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in dimension: '{value}'") from e

    # Handle fractions
    if "/" in value:
        num_str, den_str = value.split("/", 1)
        try:
            num, den = float(num_str.strip()), float(den_str.strip())
            if den == 0:
                raise ValueError("division by zero")
            return num / den
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid fraction format: '{value}'") from e

    # Handle single numeric value
    try:
        return float(value)
    except ValueError as e:
        raise ValueError(f"Invalid dimension format: '{value}'") from e


def convert_alignment(value: str) -> str:
    """Convert alignment value with extended alias support."""
    value = value.strip().lower()

    valid_alignments = [
        "left",
        "center",
        "right",
        "justify",
        "top",
        "middle",
        "bottom",
        "baseline",
    ]

    if value in valid_alignments:
        return value

    # Enhanced aliases for P8
    aliases = {
        "start": "left",
        "end": "right",
        "centered": "center",
        "justified": "justify",
        "flex-start": "left",
        "flex-end": "right",
        "center": "center",
        "space-between": "justify",
    }

    return aliases.get(value, value)


def convert_style(value: str) -> tuple[str, Any]:
    """
    Enhanced style value conversion with comprehensive CSS support.

    ENHANCEMENT P8: Comprehensive CSS value parsing including:
    - rgba/hsla colors
    - CSS gradients
    - Multiple shadow values
    - Complex border specifications
    """
    value = value.strip()
    logger.debug(f"Converting style value: '{value}'")

    # Enhanced hex color detection
    hex_pattern = r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$"
    if re.match(hex_pattern, value):
        return ("color", _create_color_value("hex", value))

    # ENHANCEMENT P8: Invalid hex color detection for better error reporting
    # If it starts with # but doesn't match valid hex pattern, treat as invalid hex color
    if value.startswith("#"):
        return ("color", {"type": "hex", "value": value, "error": "Invalid hex format"})

    # ENHANCEMENT P8: rgba/hsla color parsing
    rgba_match = re.match(r"rgba?\(\s*([^)]+)\s*\)", value)
    if rgba_match:
        rgba_content = rgba_match.group(1)
        try:
            parts = [part.strip() for part in rgba_content.split(",")]
            if len(parts) in [3, 4]:
                r, g, b = map(int, parts[:3])
                a = float(parts[3]) if len(parts) == 4 else 1.0

                color_data = {"r": r, "g": g, "b": b, "a": a}
                return ("color", _create_color_value("rgba", color_data))
        except (ValueError, IndexError):
            logger.warning(f"Invalid rgba format: {value}")

    hsla_match = re.match(r"hsla?\(\s*([^)]+)\s*\)", value)
    if hsla_match:
        hsla_content = hsla_match.group(1)
        try:
            parts = [part.strip() for part in hsla_content.split(",")]
            if len(parts) in [3, 4]:
                h = int(parts[0])
                s = int(parts[1].rstrip("%"))
                lightness = int(parts[2].rstrip("%"))
                a = float(parts[3]) if len(parts) == 4 else 1.0

                color_data = {"h": h, "s": s, "l": lightness, "a": a}
                return ("color", _create_color_value("hsla", color_data))
        except (ValueError, IndexError):
            logger.warning(f"Invalid hsla format: {value}")

    # ENHANCEMENT P8: CSS gradient parsing with improved definition capture
    gradient_patterns = [
        (r"linear-gradient\(\s*(.*)\s*\)$", "linear"),
        (r"radial-gradient\(\s*(.*)\s*\)$", "radial"),
        (r"conic-gradient\(\s*(.*)\s*\)$", "conic"),
    ]

    for pattern, gradient_type in gradient_patterns:
        gradient_match = re.match(pattern, value)
        if gradient_match:
            return (
                "gradient",
                {
                    "type": gradient_type,
                    "value": value,
                    "definition": gradient_match.group(1),
                },
            )

    # Enhanced URL detection
    url_match = re.match(r"url\(\s*['\"]?([^'\"]*)['\"]?\s*\)", value)
    if url_match:
        url = url_match.group(1).strip()
        return ("url", {"type": "url", "value": url})

    # Theme colors (case-insensitive)
    if value.upper() in KNOWN_THEME_COLORS:
        return ("color", _create_color_value("theme", value.upper()))

    # ENHANCEMENT P8: Complex border parsing with multiple properties
    complex_border_match = re.match(
        r"^(\d+(?:\.\d+)?(?:px|pt|em|rem)?)\s+(solid|dashed|dotted|double|groove|ridge|inset|outset)\s+(.+)$",
        value,
        re.IGNORECASE,
    )
    if complex_border_match:
        width_str, style_str, color_str = complex_border_match.groups()

        # Recursively parse the color component
        color_type, color_value = convert_style(color_str.strip())
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
        return ("border", border_info)

    # ENHANCEMENT P8: CSS transform parsing
    if value.startswith(("translate", "rotate", "scale", "skew", "matrix")):
        return ("transform", {"type": "css", "value": value})

    # ENHANCEMENT P8: Box shadow parsing - improved to handle inset shadows
    # Pattern matches: [inset] <offset-x> <offset-y> [blur-radius] [spread-radius] <color>
    shadow_pattern = r"^(?:inset\s+)?(?:\d+(?:\.\d+)?(?:px|pt|em|rem)?\s+){2,4}(?:rgba?\([^)]+\)|hsla?\([^)]+\)|#[0-9A-Fa-f]{3,8}|\w+)"
    if (
        re.match(shadow_pattern, value, re.IGNORECASE)
        or "shadow" in value.lower()
        or re.match(r"^\d+.*\d+", value)
    ):
        return ("shadow", {"type": "css", "value": value})

    # ENHANCEMENT P8: CSS transition/animation parsing
    # Recognize typical transition/animation patterns (more specific)
    transition_pattern = r"^(all|\w+)\s+[\d.]+s\s+[\w-]+(?:\s+[\d.]+s)?$"
    if (
        "transition" in value.lower()
        or "animation" in value.lower()
        or re.match(transition_pattern, value.lower())
    ):
        return ("animation", {"type": "css", "value": value})

    # Simple border styles
    border_styles = {
        "solid",
        "dashed",
        "dotted",
        "double",
        "groove",
        "ridge",
        "inset",
        "outset",
        "none",
        "hidden",
    }
    if value.lower() in border_styles:
        return ("border_style", value.lower())

    # Extended color names
    if value.lower() in EXTENDED_COLOR_NAMES:
        return ("color", _create_color_value("named", value.lower()))

    # Generic value fallback
    return ("value", value)


def get_theme_colors() -> set[str]:
    """Get valid Google Slides theme color names."""
    return KNOWN_THEME_COLORS.copy()


def get_color_names() -> set[str]:
    """Get extended CSS color names."""
    return EXTENDED_COLOR_NAMES.copy()
