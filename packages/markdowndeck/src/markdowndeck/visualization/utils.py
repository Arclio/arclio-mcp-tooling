import contextlib
import logging

from markdowndeck.layout.constants import (
    CODE_FONT_SIZE,
    FOOTER_FONT_SIZE,
    H1_FONT_SIZE,
    H2_FONT_SIZE,
    P_FONT_SIZE,
)
from markdowndeck.models import Element, ElementType

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
    "background1": "#FFFFFF",
    "background2": "#F3F3F3",
    "text1": "#000000",
    "text2": "#555555",
    "accent1": "#4A86E8",
    "accent2": "#FF9900",
    "accent3": "#3C78D8",
    "accent4": "#6AA84F",
    "accent5": "#A64D79",
    "accent6": "#CC0000",
    "hyperlink": "#1155CC",
}


def parse_color(color_value, default_color="#000000"):
    """Parse a color value (dict, hex, named, or theme) into a Matplotlib-compatible format."""
    if isinstance(color_value, dict) and "type" in color_value:
        color_type = color_value["type"]
        value = color_value.get("value", color_value.get("themeColor"))
        if color_type == "hex":
            return value
        if color_type in ["named", "theme"]:
            return NAMED_COLORS_HEX.get(str(value).lower(), default_color)
        if color_type == "rgba":
            r, g, b, a = (
                value.get("r", 0),
                value.get("g", 0),
                value.get("b", 0),
                value.get("a", 1.0),
            )
            return (r / 255.0, g / 255.0, b / 255.0, a)

    if isinstance(color_value, str):
        color_str = color_value.strip().lower()
        if color_str.startswith("#"):
            return color_value.strip()
        return NAMED_COLORS_HEX.get(color_str, default_color)

    logger.warning(
        f"Unknown color value '{color_value}', defaulting to {default_color}."
    )
    return default_color


def parse_border_directive(border_info):
    """Parse a border directive (string or dict) into components for Matplotlib."""
    if not border_info:
        return None

    border_props = {"width": 1.0, "style": "solid", "color": "#000000"}
    linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    if isinstance(border_info, dict):
        with contextlib.suppress(ValueError, TypeError):
            border_props["width"] = float(
                str(border_info.get("width", "1")).rstrip("ptx")
            )
        border_props["style"] = border_info.get("style", "solid")
        border_props["color"] = parse_color(
            border_info.get("color"), border_props["color"]
        )
    elif isinstance(border_info, str):
        parts = border_info.lower().split()
        color_part = parts[-1]
        border_props["color"] = parse_color(color_part, border_props["color"])
        for part in parts[:-1]:
            if part.endswith("pt") or part.endswith("px"):
                with contextlib.suppress(ValueError):
                    border_props["width"] = float(part.rstrip("ptx"))
            elif part in linestyle_map:
                border_props["style"] = part

    border_props["style"] = linestyle_map.get(border_props["style"], "-")
    return border_props


def _get_font_for_element(element: Element) -> tuple[float, str]:
    """Determines the correct font size and family for an element."""
    directives = getattr(element, "directives", {})

    font_family = directives.get("font-family", "sans-serif")
    if element.element_type == ElementType.CODE:
        font_family = "monospace"

    default_sizes = {
        ElementType.TITLE: H1_FONT_SIZE,
        ElementType.SUBTITLE: H2_FONT_SIZE,
        ElementType.TEXT: P_FONT_SIZE,
        ElementType.QUOTE: P_FONT_SIZE,
        ElementType.CODE: CODE_FONT_SIZE,
        ElementType.FOOTER: FOOTER_FONT_SIZE,
        ElementType.BULLET_LIST: P_FONT_SIZE,
        ElementType.ORDERED_LIST: P_FONT_SIZE,
        ElementType.TABLE: P_FONT_SIZE - 2,
    }

    font_size = default_sizes.get(element.element_type, P_FONT_SIZE)
    if "fontsize" in directives:
        try:
            font_size = float(directives["fontsize"])
        except (ValueError, TypeError):
            pass

    return font_size, font_family
