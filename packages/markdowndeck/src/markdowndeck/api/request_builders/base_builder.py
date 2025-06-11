"""Base request builder for Google Slides API requests."""

import logging
import uuid
from typing import Any

from markdowndeck.models import TextFormat, TextFormatType

logger = logging.getLogger(__name__)


class BaseRequestBuilder:
    """Base class for Google Slides API request builders."""

    def _generate_id(self, prefix: str = "", max_length: int = 50) -> str:
        """
        Generate a unique ID string that stays within Google Slides API limits.

        Args:
            prefix: Optional prefix for the ID
            max_length: Maximum allowed length (Google Slides limit is 50)

        Returns:
            String with the generated ID under the length limit
        """
        uuid_suffix = uuid.uuid4().hex[:8]  # 8 chars for uniqueness

        if not prefix:
            return uuid_suffix

        # Calculate available space for prefix
        separator_chars = 1  # One underscore: {prefix}_{uuid}
        available_for_prefix = max_length - len(uuid_suffix) - separator_chars

        # Intelligently truncate prefix if needed while preserving meaning
        if len(prefix) > available_for_prefix:
            # For slide-related prefixes, try to preserve the slide number
            if prefix.startswith("slide_") and "_" in prefix:
                parts = prefix.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    # Keep "slide_N" and truncate the rest
                    essential_part = f"slide_{parts[1]}"
                    if len(essential_part) <= available_for_prefix:
                        truncated_prefix = essential_part
                    else:
                        # Even essential part is too long, simple truncation
                        truncated_prefix = prefix[:available_for_prefix]
                else:
                    # Simple truncation
                    truncated_prefix = prefix[:available_for_prefix]
            else:
                # Simple truncation for non-slide prefixes
                truncated_prefix = prefix[:available_for_prefix]
        else:
            truncated_prefix = prefix

        return f"{truncated_prefix}_{uuid_suffix}"

    def _hex_to_rgb(self, hex_color: str) -> dict[str, float]:
        """
        Convert hex color to RGB values for Google Slides API.

        Args:
            hex_color: Hex color string (e.g., "#FF5733")

        Returns:
            Dictionary with red, green, blue values between 0-1
        """
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Handle shorthand hex
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])

        # Convert to RGB
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        return {"red": r, "green": g, "blue": b}

    def _rgb_to_color_dict(self, r: int, g: int, b: int) -> dict[str, dict]:
        """
        Convert RGB values to Google Slides API color dictionary.

        Args:
            r, g, b: RGB values (0-255)

        Returns:
            Dictionary with rgbColor format for Google Slides API
        """
        return {
            "rgbColor": {
                "red": r / 255.0,
                "green": g / 255.0,
                "blue": b / 255.0,
            }
        }

    def _format_to_style(self, text_format: TextFormat) -> dict[str, Any]:
        """
        Convert TextFormat to Google Slides TextStyle.

        Args:
            text_format: The text format

        Returns:
            Dictionary with the style
        """
        style = {}

        if text_format.format_type == TextFormatType.BOLD:
            style["bold"] = True
        elif text_format.format_type == TextFormatType.ITALIC:
            style["italic"] = True
        elif text_format.format_type == TextFormatType.UNDERLINE:
            style["underline"] = True
        elif text_format.format_type == TextFormatType.STRIKETHROUGH:
            style["strikethrough"] = True
        elif text_format.format_type == TextFormatType.CODE:
            style["fontFamily"] = "Courier New"
            style["backgroundColor"] = {  # OptionalColor
                "opaqueColor": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
            }
        elif text_format.format_type == TextFormatType.LINK:
            style["link"] = {"url": text_format.value}
        elif text_format.format_type == TextFormatType.COLOR:
            # FIXED: This block now handles hex, named colors, and theme colors correctly.
            color_value_str = text_format.value
            if isinstance(color_value_str, str):
                color_value_lower = color_value_str.lower()
                named_colors = {
                    "black": "#000000",
                    "white": "#FFFFFF",
                    "red": "#FF0000",
                    "green": "#008000",
                    "blue": "#0000FF",
                    "yellow": "#FFFF00",
                    "cyan": "#00FFFF",
                    "magenta": "#FF00FF",
                    "silver": "#C0C0C0",
                    "gray": "#808080",
                    "maroon": "#800000",
                    "olive": "#808000",
                    "purple": "#800080",
                    "teal": "#008080",
                    "navy": "#000080",
                }
                theme_colors = {
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
                }

                if color_value_str.startswith("#"):
                    rgb = self._hex_to_rgb(color_value_str)
                    style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                elif color_value_lower in named_colors:
                    rgb = self._hex_to_rgb(named_colors[color_value_lower])
                    style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                elif color_value_str.upper() in theme_colors:
                    style["foregroundColor"] = {
                        "opaqueColor": {"themeColor": color_value_str.upper()}
                    }
                else:
                    logger.warning(
                        f"Unsupported color value: '{color_value_str}'. It is not a valid hex, named, or theme color."
                    )
        elif text_format.format_type == TextFormatType.BACKGROUND_COLOR:
            color_value_str = text_format.value
            if isinstance(color_value_str, str):
                if color_value_str.startswith("#"):
                    rgb = self._hex_to_rgb(color_value_str)
                    style["backgroundColor"] = {"opaqueColor": {"rgbColor": rgb}}
                else:  # Assume theme color name
                    style["backgroundColor"] = {
                        "opaqueColor": {"themeColor": color_value_str.upper()}
                    }
        elif text_format.format_type == TextFormatType.FONT_SIZE:
            if isinstance(text_format.value, int | float):
                style["fontSize"] = {
                    "magnitude": float(text_format.value),
                    "unit": "PT",
                }
        elif text_format.format_type == TextFormatType.FONT_FAMILY:
            if isinstance(text_format.value, str):
                style["fontFamily"] = text_format.value
        elif (
            text_format.format_type == TextFormatType.VERTICAL_ALIGN
            and isinstance(text_format.value, str)
            and text_format.value.upper()
            in [
                "SUPERSCRIPT",
                "SUBSCRIPT",
                "NONE",
            ]
        ):
            style["baselineOffset"] = text_format.value.upper()

        return style

    def _format_to_fields(self, text_format: TextFormat) -> str:
        """
        Convert TextFormat to fields string for updateTextStyle.

        Args:
            text_format: The text format

        Returns:
            String with the fields to update
        """
        if text_format.format_type == TextFormatType.BOLD:
            return "bold"
        if text_format.format_type == TextFormatType.ITALIC:
            return "italic"
        if text_format.format_type == TextFormatType.UNDERLINE:
            return "underline"
        if text_format.format_type == TextFormatType.STRIKETHROUGH:
            return "strikethrough"
        if text_format.format_type == TextFormatType.CODE:
            return "fontFamily,backgroundColor"  # Updates the whole backgroundColor OptionalColor object
        if text_format.format_type == TextFormatType.LINK:
            return "link"
        if text_format.format_type == TextFormatType.COLOR:
            return "foregroundColor"  # Updates the whole foregroundColor OptionalColor object
        if text_format.format_type == TextFormatType.FONT_SIZE:
            return "fontSize"  # Updates the whole Dimension object for fontSize
        if text_format.format_type == TextFormatType.FONT_FAMILY:
            return "fontFamily"
        if text_format.format_type == TextFormatType.VERTICAL_ALIGN:
            return "baselineOffset"
        if text_format.format_type == TextFormatType.BACKGROUND_COLOR:
            return "backgroundColor"  # Updates the whole backgroundColor OptionalColor object

        return ""

    def _apply_text_formatting(
        self,
        element_id: str,
        style: dict[str, Any],
        fields: str,
        range_type: str = None,
        start_index: int = None,
        end_index: int = None,
        cell_location: dict[str, int] = None,
    ) -> dict:
        """
        Helper method to create properly formatted text style requests.

        Args:
            element_id: ID of the element to update
            style: Style dictionary to apply
            fields: Fields to update
            range_type: Type of range (e.g., "ALL") or None for specific indices
            start_index: Start index for specific range
            end_index: End index for specific range
            cell_location: Location of a cell in a table (dict with rowIndex and columnIndex)

        Returns:
            Dictionary with the update text style request
        """
        # Safety check - prevent accidental mixing of range_type with indices
        if range_type and (start_index is not None or end_index is not None):
            logger.warning(
                f"Mixed text range specification detected: range_type={range_type} with "
                f"start_index={start_index}, end_index={end_index}. Defaulting to range_type only."
            )
            # Force indices to None to avoid mixing
            start_index = None
            end_index = None

        request = {
            "updateTextStyle": {
                "objectId": element_id,
                "style": style,
                "fields": fields,
            }
        }

        # FIXED: Be explicit and never mix type and indices in the textRange
        # The Google Slides API treats unspecified type as RANGE_TYPE_UNSPECIFIED
        # which causes conflicts if indices are also present
        if range_type:
            # Use type-based range (e.g., "ALL")
            request["updateTextStyle"]["textRange"] = {"type": range_type}
        elif start_index is not None and end_index is not None:
            # Use index-based range, with explicit FIXED_RANGE type
            request["updateTextStyle"]["textRange"] = {
                "type": "FIXED_RANGE",
                "startIndex": start_index,
                "endIndex": end_index,
            }
        else:
            # Default to ALL if neither is specified and text range is required
            # However, if style is empty, textRange might not be needed - API dependent.
            # For safety, always include it if fields are specified.
            if fields:  # Only add textRange if there are fields to update
                request["updateTextStyle"]["textRange"] = {"type": "ALL"}

        # Add cell location for table text styling if provided
        if cell_location:
            request["updateTextStyle"][
                "cellLocation"
            ] = cell_location  # Corrected: cellLocation is part of updateTextStyle directly
            # The tableRange is not needed here if cellLocation is used.
            # The API docs for UpdateTextStyleRequest show cellLocation at the same level as textRange.
            # If textRange is also set, it applies within the specified cell.

        return request
