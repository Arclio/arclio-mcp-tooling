"""Rendering utilities for colors, borders, and text formatting."""

import contextlib
import logging

logger = logging.getLogger(__name__)

# Mapping for common CSS/theme color names to hex for Matplotlib
NAMED_COLORS_HEX = {
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#008000",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "brown": "#A52A2A",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#C0C0C0",
    "gold": "#FFD700",
    "transparent": "none",
    "aqua": "#00FFFF",
    "teal": "#008080",
    "navy": "#000080",
    "olive": "#808000",
    "maroon": "#800000",
    "lime": "#00FF00",
    "fuchsia": "#FF00FF",
    "darkred": "#8B0000",
    "darkgreen": "#006400",
    "darkblue": "#00008B",
    "lightblue": "#ADD8E6",
    "crimson": "#DC143C",
    "coral": "#FF7F50",
    "salmon": "#FA8072",
    "khaki": "#F0E68C",
    "violet": "#EE82EE",
    "indigo": "#4B0082",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "turquoise": "#40E0D0",
    "plum": "#DDA0DD",
    "orchid": "#DA70D6",
    "tan": "#D2B48C",
    "beige": "#F5F5DC",
    "ivory": "#FFFFF0",
    # Google Slides Theme Colors (Approximate Visual Mapping)
    "BACKGROUND1": "#FFFFFF",
    "BACKGROUND2": "#F3F3F3",
    "TEXT1": "#000000",
    "TEXT2": "#555555",
    "ACCENT1": "#4A86E8",
    "ACCENT2": "#FF9900",
    "ACCENT3": "#3C78D8",
    "ACCENT4": "#6AA84F",
    "ACCENT5": "#A64D79",
    "ACCENT6": "#CC0000",
    "HYPERLINK": "#1155CC",
}


def parse_color(color_value, default_color="#000000"):
    """Parse a color value (dict, hex, named, or theme) into a Matplotlib-compatible format."""
    if isinstance(color_value, dict):
        if color_value.get("type") == "hex":
            return color_value.get("value", default_color)
        if color_value.get("type") == "named":
            return NAMED_COLORS_HEX.get(
                color_value.get("value", "").lower(), default_color
            )
        if color_value.get("type") == "theme":
            theme_color = color_value.get("themeColor", "").upper()
            return NAMED_COLORS_HEX.get(theme_color, default_color)
        if color_value.get("type") == "rgba":
            r, g, b, a = (
                color_value.get("r", 0),
                color_value.get("g", 0),
                color_value.get("b", 0),
                color_value.get("a", 1.0),
            )
            return (r / 255.0, g / 255.0, b / 255.0, a)

    if isinstance(color_value, str):
        color_str = color_value.strip().lower()
        if color_str.startswith("#"):
            return color_value.strip()
        if color_str in NAMED_COLORS_HEX:
            return NAMED_COLORS_HEX[color_str]
        if color_str.upper() in NAMED_COLORS_HEX:
            return NAMED_COLORS_HEX[color_str.upper()]

    logger.warning(
        f"Unknown color value '{color_value}', defaulting to {default_color}."
    )
    return default_color


def parse_border_directive(border_info):
    """Parse a border directive (string or dict) into components for Matplotlib."""
    if not border_info:
        return None

    border_props = {"width": 1.0, "style": "solid", "color": "#000000"}  # Defaults
    linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    if isinstance(border_info, dict):
        # Handle dict format: {'width': '1pt', 'style': 'solid', 'color': {'type': 'named', 'value': 'gray'}}
        with contextlib.suppress(ValueError, TypeError):
            border_props["width"] = float(
                str(border_info.get("width", "1")).rstrip("ptx")
            )
        border_props["style"] = border_info.get("style", "solid")
        border_props["color"] = parse_color(
            border_info.get("color"), border_props["color"]
        )
    elif isinstance(border_info, str):
        # Handle string format: "1pt solid #cccccc"
        parts = border_info.lower().split()
        for part in parts:
            if part.endswith("pt") or part.endswith("px"):
                with contextlib.suppress(ValueError):
                    border_props["width"] = float(part.rstrip("ptx"))
            elif part in linestyle_map:
                border_props["style"] = part
            else:
                border_props["color"] = parse_color(part, border_props["color"])

    border_props["style"] = linestyle_map.get(border_props["style"], "-")
    return border_props
