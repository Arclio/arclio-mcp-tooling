"""List request builder for Google Slides API requests."""

import logging
from typing import Any

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import ListElement, ListItem

logger = logging.getLogger(__name__)


class ListRequestBuilder(BaseRequestBuilder):
    """Builder for list-related Google Slides API requests."""

    def generate_bullet_list_element_requests(
        self, element: ListElement, slide_id: str
    ) -> list[dict]:
        """
        Generate requests for a bullet list element.

        Args:
            element: The bullet list element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # For bullet lists, generate the base list requests
        base_requests = self.generate_list_element_requests(
            element, slide_id, "BULLET_DISC_CIRCLE_SQUARE"
        )
        requests.extend(base_requests)

        # Apply item-specific text formatting if present
        # This is needed because the ListItem formatting may not be properly applied in generate_list_element_requests
        for item in element.items:
            if hasattr(item, "formatting") and item.formatting:
                for text_format in item.formatting:
                    style_request = self._apply_text_formatting(
                        element_id=element.object_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=text_format.start,
                        end_index=text_format.end,
                    )
                    requests.append(style_request)
                    logger.debug(
                        f"Applied formatting {text_format.format_type} to list item at position {text_format.start}-{text_format.end}"
                    )

        return requests

    def generate_list_element_requests(
        self, element: ListElement, slide_id: str, bullet_type: str
    ) -> list[dict]:
        """
        Generate requests for a list element.

        Args:
            element: The list element
            slide_id: The slide ID
            bullet_type: Type of bullet (e.g., "BULLET_DISC_CIRCLE_SQUARE")

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"list_{slide_id}")
            logger.debug(f"Generated missing object_id for list element: {element.object_id}")

        # Create shape
        create_shape_request = {
            "createShape": {
                "objectId": element.object_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": size[0], "unit": "PT"},
                        "height": {"magnitude": size[1], "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": position[0],
                        "translateY": position[1],
                        "unit": "PT",
                    },
                },
            }
        }
        requests.append(create_shape_request)

        # Skip insertion if there are no items
        if not hasattr(element, "items") or not element.items:
            return requests

        # ENHANCEMENT: Handle nested lists properly
        text_content, text_ranges = self._format_list_with_nesting(element.items)

        # Insert the text content
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": text_content,
            }
        }
        requests.append(insert_text_request)

        # Create bullets with proper nesting
        for range_info in text_ranges:
            start_index = range_info["start"]
            end_index = range_info["end"]
            nesting_level = range_info["level"]

            # Create bullets for this range
            bullets_request = {
                "createParagraphBullets": {
                    "objectId": element.object_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "bulletPreset": bullet_type,
                }
            }

            # Set nesting level if greater than 0
            if nesting_level > 0:
                bullets_request["createParagraphBullets"]["nestingLevel"] = nesting_level

            requests.append(bullets_request)

            logger.debug(
                f"Created bullets for range {start_index}-{end_index} with nesting level {nesting_level}"
            )

        # Apply text formatting for each item
        if hasattr(element, "formatting") and element.formatting:
            for text_format in element.formatting:
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style=self._format_to_style(text_format),
                    fields=self._format_to_fields(text_format),
                    start_index=text_format.start,
                    end_index=text_format.end,
                )
                requests.append(style_request)

        # Apply color directive if specified
        self._apply_color_directive(element, requests)

        # ENHANCEMENT: Apply additional styling from directives
        self._apply_list_styling_directives(element, requests)

        return requests

    def _format_list_with_nesting(self, items: list[ListItem]) -> tuple[str, list[dict[str, Any]]]:
        """
        Format list items with proper nesting.

        Args:
            items: List items (potentially with nested children)

        Returns:
            Tuple of (text_content, list of ranges with nesting levels)
        """
        text_content = ""
        text_ranges = []

        def process_items(items_list, level=0):
            nonlocal text_content, text_ranges

            for item in items_list:
                # Get item text and remove trailing newlines
                item_text = item.text.rstrip() if hasattr(item, "text") else str(item).rstrip()

                # Record the start position of this item
                start_pos = len(text_content)

                # Add the item text
                text_content += item_text + "\n"

                # Record the end position (before the newline)
                end_pos = len(text_content)

                # Add the range information
                text_ranges.append(
                    {
                        "start": start_pos,
                        "end": end_pos - 1,  # Exclude the newline
                        "level": level,
                    }
                )

                # Process children if any
                if hasattr(item, "children") and item.children:
                    process_items(item.children, level + 1)

        # Process all items
        process_items(items)

        return text_content, text_ranges

    def _apply_color_directive(self, element: ListElement, requests: list[dict]) -> None:
        """Apply color directive to the list element."""
        if (
            not hasattr(element, "directives")
            or not element.directives
            or "color" not in element.directives
        ):
            return

        color_value = element.directives["color"]

        # Handle both string and tuple color values
        if isinstance(color_value, tuple) and len(color_value) == 2:
            color_type, color_value = color_value
            if color_type != "color" or not isinstance(color_value, str):
                return

        # Check if this is a theme color reference
        if isinstance(color_value, str) and not color_value.startswith("#"):
            theme_colors = [
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
            ]

            if color_value.upper() in theme_colors:
                # Use theme color reference
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"foregroundColor": {"themeColor": color_value.upper()}},
                    fields="foregroundColor.themeColor",
                    range_type="ALL",
                )
                requests.append(style_request)
                logger.debug(
                    f"Applied theme color {color_value.upper()} to list {element.object_id}"
                )
                return

        # Apply RGB color if it's a hex value
        if isinstance(color_value, str) and color_value.startswith("#"):
            rgb = self._hex_to_rgb(color_value)
            style_request = self._apply_text_formatting(
                element_id=element.object_id,
                style={"foregroundColor": {"rgbColor": rgb}},
                fields="foregroundColor.rgbColor",
                range_type="ALL",
            )
            requests.append(style_request)
            logger.debug(f"Applied color {color_value} to list {element.object_id}")

    def _apply_list_styling_directives(self, element: ListElement, requests: list[dict]) -> None:
        """Apply additional styling directives to the list element."""
        if not hasattr(element, "directives") or not element.directives:
            return

        # Apply font size if specified
        if "fontsize" in element.directives:
            font_size = element.directives["fontsize"]
            if isinstance(font_size, int | float):
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"fontSize": {"magnitude": font_size, "unit": "PT"}},
                    fields="fontSize",
                    range_type="ALL",
                )
                requests.append(style_request)
                logger.debug(f"Applied font size {font_size}pt to list {element.object_id}")

        # Apply font family if specified
        if "font" in element.directives:
            font_family = element.directives["font"]
            if isinstance(font_family, str):
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"fontFamily": font_family},
                    fields="fontFamily",
                    range_type="ALL",
                )
                requests.append(style_request)
                logger.debug(f"Applied font family '{font_family}' to list {element.object_id}")
