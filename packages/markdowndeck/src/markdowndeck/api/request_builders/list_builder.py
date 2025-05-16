"""List request builder for Google Slides API requests."""

import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.models import Element, ListItem, TextFormat
from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models.elements.list import ListElement

logger = logging.getLogger(__name__)


class ListRequestBuilder(BaseRequestBuilder):
    """Formatter for list elements (ordered and unordered)."""

    def can_handle(self, token: Token, leading_tokens: list[Token]) -> bool:
        """Check if this formatter can handle the given token."""
        return token.type in ["bullet_list_open", "ordered_list_open"]

    def process(
        self, tokens: list[Token], start_index: int, directives: dict[str, Any]
    ) -> tuple[Element | None, int]:
        """Create a list element from tokens."""
        open_token = tokens[start_index]
        ordered = open_token.type == "ordered_list_open"
        close_tag_type = "ordered_list_close" if ordered else "bullet_list_close"

        end_index = self.find_closing_token(tokens, start_index, close_tag_type)

        items = self._extract_list_items(tokens, start_index + 1, end_index, 0)

        if not items:
            logger.debug(
                f"No list items found for list at index {start_index}, skipping element."
            )
            return None, end_index

        element = self.element_factory.create_list_element(
            items=items, ordered=ordered, directives=directives.copy()
        )
        logger.debug(
            f"Created {'ordered' if ordered else 'bullet'} list with {len(items)} top-level items from token index {start_index} to {end_index}"
        )
        return element, end_index

    def _extract_list_items(
        self, tokens: list[Token], current_token_idx: int, list_end_idx: int, level: int
    ) -> list[ListItem]:
        """
        Recursively extracts list items, handling nesting.
        """
        items: list[ListItem] = []
        i = current_token_idx

        while i < list_end_idx:
            token = tokens[i]

            if token.type == "list_item_open":
                # Find the content of this list item
                item_content_start_idx = i + 1
                item_text = ""
                item_formatting: list[TextFormat] = []
                children: list[ListItem] = []

                # Iterate within the list_item_open and list_item_close
                # A list item can contain paragraphs, nested lists, etc.
                j = item_content_start_idx
                item_content_processed_up_to = j

                while j < list_end_idx and not (
                    tokens[j].type == "list_item_close"
                    and tokens[j].level == token.level
                ):
                    item_token = tokens[j]
                    if (
                        item_token.type == "paragraph_open"
                    ):  # Text content of list item is usually in a paragraph
                        inline_idx = j + 1
                        if (
                            inline_idx < list_end_idx
                            and tokens[inline_idx].type == "inline"
                        ):
                            # Append text, if multiple paragraphs, join with newline
                            if item_text:
                                item_text += "\n"
                            current_text_offset = len(item_text)

                            # Use helper method to extract plain text instead of raw markdown
                            plain_text = self._get_plain_text_from_inline_token(
                                tokens[inline_idx]
                            )
                            item_text += plain_text

                            extracted_fmts = self.element_factory._extract_formatting_from_inline_token(
                                tokens[inline_idx]
                            )
                            for fmt in extracted_fmts:
                                item_formatting.append(
                                    TextFormat(
                                        start=fmt.start + current_text_offset,
                                        end=fmt.end + current_text_offset,
                                        format_type=fmt.format_type,
                                        value=fmt.value,
                                    )
                                )
                        # Move j past the paragraph
                        j = self.find_closing_token(tokens, j, "paragraph_close")
                    elif item_token.type in ["bullet_list_open", "ordered_list_open"]:
                        # This is a nested list
                        nested_list_close_tag = (
                            "bullet_list_close"
                            if item_token.type == "bullet_list_open"
                            else "ordered_list_close"
                        )
                        nested_list_end_idx = self.find_closing_token(
                            tokens, j, nested_list_close_tag
                        )
                        children.extend(
                            self._extract_list_items(
                                tokens, j + 1, nested_list_end_idx, level + 1
                            )
                        )
                        j = nested_list_end_idx

                    item_content_processed_up_to = (
                        j  # update how far we've processed for this item
                    )
                    j += 1

                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                )
                items.append(list_item_obj)
                i = (
                    item_content_processed_up_to + 1
                )  # Continue after the list_item_close or processed content

            else:  # Not a list_item_open, means we are past the items at current_level or malformed
                i += 1

        return items

    def generate_bullet_list_element_requests(
        self,
        element: ListElement,
        slide_id: str,
        theme_placeholders: dict[str, str] = None,
        subheading_data: dict = None,
    ) -> list[dict]:
        """
        Generate requests for a bullet list element.

        Args:
            element: The bullet list element
            slide_id: The slide ID
            theme_placeholders: Dictionary mapping element types to placeholder IDs
            subheading_data: Optional data from a subheading to prepend to the list

        Returns:
            List of request dictionaries
        """
        requests = []

        # For bullet lists, generate the base list requests
        base_requests = self.generate_list_element_requests(
            element,
            slide_id,
            "BULLET_DISC_CIRCLE_SQUARE",
            theme_placeholders,
            subheading_data,
        )
        requests.extend(base_requests)

        return requests

    def generate_list_element_requests(
        self,
        element: ListElement,
        slide_id: str,
        bullet_type: str,
        theme_placeholders: dict[str, str] = None,
        subheading_data: dict = None,
    ) -> list[dict]:
        """
        Generate requests for a list element.

        Args:
            element: The list element
            slide_id: The slide ID
            bullet_type: Type of bullet (e.g., "BULLET_DISC_CIRCLE_SQUARE")
            theme_placeholders: Dictionary mapping element types to placeholder IDs
            subheading_data: Optional data from a subheading to prepend to the list

        Returns:
            List of request dictionaries
        """
        requests = []

        # Check if this element should use a theme placeholder
        if theme_placeholders and element.element_type in theme_placeholders:
            # Use placeholder instead of creating a new shape
            return self._handle_themed_list_element(
                element,
                theme_placeholders[element.element_type],
                bullet_type,
                subheading_data,
            )

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"list_{slide_id}")
            logger.debug(
                f"Generated missing object_id for list element: {element.object_id}"
            )

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

        # Removed autofit request since only NONE is supported by the Google Slides REST API
        # and NONE is the default state, so we don't need to set it explicitly

        # Skip insertion if there are no items
        if not hasattr(element, "items") or not element.items:
            return requests

        # Prepare subheading text if provided
        subheading_text = ""
        subheading_formatting = []
        title_offset = 0

        if subheading_data:
            subheading_text = subheading_data.get("text", "")
            subheading_formatting = subheading_data.get("formatting", [])

            if subheading_text:
                subheading_text += "\n"  # Add newline after subheading
                title_offset = len(subheading_text)

        # Format list content with proper nesting using tabs
        text_content, text_ranges = self._format_list_with_nesting(element.items)

        # Insert the subheading (if any) and the list content
        full_text = subheading_text + text_content

        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": full_text,
            }
        }
        requests.append(insert_text_request)

        # If we have a subheading, apply its styling
        if subheading_data and subheading_text:
            # Get the exact length for proper index calculations
            subheading_length = len(subheading_text)

            # Adjust end index to ensure it doesn't exceed text length
            # Subtract 1 from the end index to avoid off-by-one errors
            end_index = max(0, min(subheading_length - 1, len(subheading_text) - 1))

            # Style the subheading text
            subheading_style_request = {
                "updateTextStyle": {
                    "objectId": element.object_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": 0,
                        "endIndex": end_index,  # Safe end index
                    },
                    "style": {
                        "bold": True,
                        "fontSize": {"magnitude": 14, "unit": "PT"},
                    },
                    "fields": "bold,fontSize",
                }
            }
            requests.append(subheading_style_request)

            # Apply spacing after the subheading
            subheading_para_request = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": 0,
                        "endIndex": end_index,  # Safe end index
                    },
                    "style": {
                        "spaceBelow": {"magnitude": 6, "unit": "PT"},
                    },
                    "fields": "spaceBelow",
                }
            }
            requests.append(subheading_para_request)

            # Apply any formatting from the original subheading
            for fmt in subheading_formatting:
                # Ensure start and end indices are within bounds
                fmt_start = min(fmt.start, end_index)
                fmt_end = min(fmt.end, end_index)

                if fmt_start < fmt_end:
                    style_request = self._apply_text_formatting(
                        element_id=element.object_id,
                        style=self._format_to_style(fmt),
                        fields=self._format_to_fields(fmt),
                        start_index=fmt_start,
                        end_index=fmt_end,
                    )
                    requests.append(style_request)

        # Create bullets for each range
        for range_info in text_ranges:
            start_index = range_info["start"] + title_offset
            end_index = range_info["end"] + title_offset

            # Safety check: ensure end_index doesn't exceed the text length
            text_length = len(full_text)
            if end_index >= text_length:
                logger.warning(
                    f"Correcting end_index from {end_index} to {text_length - 1} for bullet range"
                )
                end_index = max(start_index, text_length - 1)

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
            requests.append(bullets_request)

            # Apply consistent paragraph spacing to each list item
            para_spacing_request = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "style": {
                        # Apply consistent spacing for all list items
                        "spaceAbove": {"magnitude": 3, "unit": "PT"},
                        "spaceBelow": {"magnitude": 3, "unit": "PT"},
                        # Use percentage-based line spacing (115%)
                        "lineSpacing": 115,
                    },
                    "fields": "spaceAbove,spaceBelow,lineSpacing",
                }
            }
            requests.append(para_spacing_request)

        # Apply item-specific text formatting with adjusted positions
        for range_info in text_ranges:
            item = range_info.get("item")
            offset_mapping = range_info.get("offset_mapping", {})

            if item and hasattr(item, "formatting") and item.formatting:
                for text_format in item.formatting:
                    # Adjust start and end indices based on offset mapping
                    adjusted_start = offset_mapping.get(
                        text_format.start, range_info["start"]
                    )
                    adjusted_end = offset_mapping.get(
                        text_format.end, range_info["end"]
                    )

                    # Adjust for any title offset
                    adjusted_start += title_offset
                    adjusted_end += title_offset

                    # Safety check: ensure end_index doesn't exceed the text length
                    # and start is less than end
                    text_length = len(full_text)
                    if adjusted_end >= text_length:
                        adjusted_end = text_length - 1
                    if adjusted_start >= adjusted_end:
                        adjusted_start = max(0, adjusted_end - 1)

                    style_request = self._apply_text_formatting(
                        element_id=element.object_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=adjusted_start,
                        end_index=adjusted_end,
                    )
                    requests.append(style_request)

        # Apply color directive if specified
        self._apply_color_directive(element, requests)

        # Apply additional styling from directives
        self._apply_list_styling_directives(element, requests)

        return requests

    def _handle_themed_list_element(
        self,
        element: ListElement,
        placeholder_id: str,
        bullet_type: str,
        subheading_data: dict = None,
    ) -> list[dict]:
        """
        Handle list element that should use a theme placeholder.

        Args:
            element: The list element
            placeholder_id: The ID of the placeholder to use
            bullet_type: Type of bullet (e.g., "BULLET_DISC_CIRCLE_SQUARE")
            subheading_data: Optional data from a subheading to prepend to the list

        Returns:
            List of request dictionaries
        """
        requests = []

        # Override placeholder_id if specified in subheading_data
        if subheading_data and "placeholder_id" in subheading_data:
            placeholder_id = subheading_data["placeholder_id"]
            logger.debug(
                f"Using specific placeholder ID from subheading: {placeholder_id}"
            )

        # Store the placeholder ID as the element's object_id for future reference
        element.object_id = placeholder_id

        # Skip insertion if there are no items
        if not hasattr(element, "items") or not element.items:
            return requests

        # First, always delete any existing text in the placeholder
        delete_text_request = {
            "deleteText": {"objectId": placeholder_id, "textRange": {"type": "ALL"}}
        }
        requests.append(delete_text_request)

        # Prepare subheading text if provided
        subheading_text = ""
        subheading_formatting = []
        title_offset = 0

        if subheading_data:
            subheading_text = subheading_data.get("text", "")
            subheading_formatting = subheading_data.get("formatting", [])
            subheading_alignment = subheading_data.get("horizontal_alignment", None)

            if subheading_text:
                subheading_text += "\n"  # Add newline after subheading
                title_offset = len(subheading_text)

        # Format list content with proper nesting using tabs
        text_content, text_ranges = self._format_list_with_nesting(element.items)

        # Insert the subheading (if any) and the list content
        full_text = subheading_text + text_content

        insert_text_request = {
            "insertText": {
                "objectId": placeholder_id,
                "insertionIndex": 0,
                "text": full_text,
            }
        }
        requests.append(insert_text_request)

        # If we have a subheading, apply its styling
        if subheading_data and subheading_text:
            # Get the exact length for proper index calculations
            subheading_length = len(subheading_text)

            # Adjust end index to ensure it doesn't exceed text length
            # Subtract 1 from the end index to avoid off-by-one errors
            end_index = max(0, min(subheading_length - 1, len(subheading_text) - 1))

            # Style the subheading text with bold and larger font
            subheading_style_request = {
                "updateTextStyle": {
                    "objectId": placeholder_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": 0,
                        "endIndex": end_index,  # Safe end index
                    },
                    "style": {
                        "bold": True,
                        "fontSize": {"magnitude": 14, "unit": "PT"},
                    },
                    "fields": "bold,fontSize",
                }
            }
            requests.append(subheading_style_request)

            # Apply paragraph alignment for the subheading
            if subheading_alignment:
                alignment_value = (
                    subheading_alignment.value
                    if hasattr(subheading_alignment, "value")
                    else subheading_alignment
                )
                api_alignment = {
                    "left": "START",
                    "center": "CENTER",
                    "right": "END",
                    "justify": "JUSTIFIED",
                }.get(alignment_value, "START")

                alignment_request = {
                    "updateParagraphStyle": {
                        "objectId": placeholder_id,
                        "textRange": {
                            "type": "FIXED_RANGE",
                            "startIndex": 0,
                            "endIndex": end_index,  # Safe end index
                        },
                        "style": {
                            "alignment": api_alignment,
                            "spaceBelow": {"magnitude": 6, "unit": "PT"},
                        },
                        "fields": "alignment,spaceBelow",
                    }
                }
                requests.append(alignment_request)

            # Apply any formatting from the original subheading
            for fmt in subheading_formatting:
                # Ensure start and end indices are within bounds
                fmt_start = min(fmt.start, end_index)
                fmt_end = min(fmt.end, end_index)

                if fmt_start < fmt_end:
                    style_request = self._apply_text_formatting(
                        element_id=placeholder_id,
                        style=self._format_to_style(fmt),
                        fields=self._format_to_fields(fmt),
                        start_index=fmt_start,
                        end_index=fmt_end,
                    )
                    requests.append(style_request)

        # Create bullets for each range with proper nesting
        for range_info in text_ranges:
            start_index = range_info["start"] + title_offset
            end_index = range_info["end"] + title_offset

            # Safety check: ensure end_index doesn't exceed the text length
            text_length = len(full_text)
            if end_index >= text_length:
                logger.warning(
                    f"Correcting end_index from {end_index} to {text_length - 1} for bullet range"
                )
                end_index = max(start_index, text_length - 1)

            # Create bullets for this range
            bullets_request = {
                "createParagraphBullets": {
                    "objectId": placeholder_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "bulletPreset": bullet_type,
                }
            }
            requests.append(bullets_request)

            # Apply consistent paragraph spacing to each list item
            para_spacing_request = {
                "updateParagraphStyle": {
                    "objectId": placeholder_id,
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "style": {
                        # Apply consistent spacing for all list items
                        "spaceAbove": {"magnitude": 3, "unit": "PT"},
                        "spaceBelow": {"magnitude": 3, "unit": "PT"},
                        # Use percentage-based line spacing (115%)
                        "lineSpacing": 115,
                    },
                    "fields": "spaceAbove,spaceBelow,lineSpacing",
                }
            }
            requests.append(para_spacing_request)

        # Apply item-specific text formatting with adjusted positions
        for range_info in text_ranges:
            item = range_info.get("item")
            offset_mapping = range_info.get("offset_mapping", {})

            if item and hasattr(item, "formatting") and item.formatting:
                for text_format in item.formatting:
                    # Adjust start and end indices based on offset mapping
                    adjusted_start = offset_mapping.get(
                        text_format.start, range_info["start"]
                    )
                    adjusted_end = offset_mapping.get(
                        text_format.end, range_info["end"]
                    )

                    # Adjust for any title offset
                    adjusted_start += title_offset
                    adjusted_end += title_offset

                    # Safety check: ensure end_index doesn't exceed the text length
                    # and start is less than end
                    text_length = len(full_text)
                    if adjusted_end >= text_length:
                        adjusted_end = text_length - 1
                    if adjusted_start >= adjusted_end:
                        adjusted_start = max(0, adjusted_end - 1)

                    style_request = self._apply_text_formatting(
                        element_id=placeholder_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=adjusted_start,
                        end_index=adjusted_end,
                    )
                    requests.append(style_request)

        # Apply color directive if specified
        if (
            hasattr(element, "directives")
            and element.directives
            and "color" in element.directives
        ):
            color_value = element.directives["color"]
            if isinstance(color_value, str) and not color_value.startswith("#"):
                # Theme color handling
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
                    style_request = self._apply_text_formatting(
                        element_id=placeholder_id,
                        style={
                            "foregroundColor": {
                                "opaqueColor": {"themeColor": color_value.upper()}
                            }
                        },
                        fields="foregroundColor",
                        range_type="ALL",
                    )
                    requests.append(style_request)
            elif isinstance(color_value, str) and color_value.startswith("#"):
                # RGB color handling
                rgb = self._hex_to_rgb(color_value)
                style_request = self._apply_text_formatting(
                    element_id=placeholder_id,
                    style={"foregroundColor": {"opaqueColor": {"rgbColor": rgb}}},
                    fields="foregroundColor",
                    range_type="ALL",
                )
                requests.append(style_request)

        logger.debug(
            f"Generated {len(requests)} requests for themed list using placeholder {placeholder_id}"
        )
        return requests

    def _format_list_with_nesting(
        self, items: list[ListItem]
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Format list items with proper nesting using tab characters.
        Google Slides API uses tabs to determine nesting level for bullets.

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
                item_text = (
                    item.text.rstrip() if hasattr(item, "text") else str(item).rstrip()
                )

                # Add tabs based on nesting level
                tabs = "\t" * level

                # Handle multi-line text items by adding tabs to each line
                lines = item_text.split("\n")
                tabbed_lines = [tabs + line for line in lines]
                tabbed_item_text = "\n".join(tabbed_lines)

                # Record the start position of this item
                start_pos = len(text_content)

                # Add the item text with a newline
                text_content += tabbed_item_text + " \n"

                # Record the end position (before the newline)
                # Ensure end position is always less than the total length and greater than start
                end_pos = len(text_content) - 2  # Exclude trailing space and newline
                if end_pos <= start_pos:
                    end_pos = start_pos + 1  # Ensure at least one character is selected

                # Create offset mapping for formatting
                offset_mapping = {}
                orig_pos = 0
                tabbed_pos = start_pos

                for line_idx, line in enumerate(lines):
                    if line_idx > 0:
                        # For lines after the first, there's an additional offset
                        tabbed_pos += 1  # +1 for the newline

                    # For each line, add tabs offset
                    tabbed_pos += len(tabs)

                    # Map positions for this line
                    for i in range(len(line)):
                        offset_mapping[orig_pos] = tabbed_pos
                        orig_pos += 1
                        tabbed_pos += 1

                    # Move past this line in the original text
                    if line_idx < len(lines) - 1:
                        orig_pos += 1  # +1 for the newline in original text

                # Add the range information
                text_ranges.append(
                    {
                        "start": start_pos,
                        "end": end_pos,
                        "level": level,
                        "offset_mapping": offset_mapping,
                        "item": item,  # Store reference to original item for formatting
                    }
                )

                # Process children if any
                if hasattr(item, "children") and item.children:
                    process_items(item.children, level + 1)

        # Process all items
        process_items(items)

        return text_content, text_ranges

    def _apply_color_directive(
        self, element: ListElement, requests: list[dict]
    ) -> None:
        """
        Apply color directive to a list element.

        Args:
            element: The list element
            requests: List to append requests to
        """
        if not (
            hasattr(element, "directives")
            and element.directives
            and "color" in element.directives
        ):
            return

        color_value = element.directives["color"]

        if isinstance(color_value, str) and not color_value.startswith("#"):
            # Theme color handling
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
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={
                        "foregroundColor": {
                            "opaqueColor": {"themeColor": color_value.upper()}
                        }
                    },
                    fields="foregroundColor",
                    range_type="ALL",
                )
                requests.append(style_request)
        elif isinstance(color_value, str) and color_value.startswith("#"):
            # RGB color handling
            rgb = self._hex_to_rgb(color_value)
            style_request = self._apply_text_formatting(
                element_id=element.object_id,
                style={"foregroundColor": {"opaqueColor": {"rgbColor": rgb}}},
                fields="foregroundColor",
                range_type="ALL",
            )
            requests.append(style_request)
        else:
            logger.warning(f"Unsupported color directive value: {color_value}")

    def _apply_list_styling_directives(
        self, element: ListElement, requests: list[dict]
    ) -> None:
        """
        Apply additional styling directives to the list element.

        Args:
            element: The list element
            requests: List to append requests to
        """
        if not hasattr(element, "directives") or not element.directives:
            return

        # Handle font size directive
        if "fontsize" in element.directives:
            font_size = element.directives["fontsize"]
            if isinstance(font_size, (int, float)) and font_size > 0:
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"fontSize": {"magnitude": float(font_size), "unit": "PT"}},
                    fields="fontSize",
                    range_type="ALL",
                )
                requests.append(style_request)

        # Handle font family directive
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
