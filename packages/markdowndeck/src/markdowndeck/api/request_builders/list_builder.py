import logging
from typing import Any

from markdown_it.token import Token

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import Element, ListItem, TextFormat
from markdowndeck.models.elements.list import ListElement

logger = logging.getLogger(__name__)


class ListRequestBuilder(BaseRequestBuilder):
    """Formatter for list elements (ordered and unordered)."""

    def __init__(self, element_factory):
        """Initialize the ListRequestBuilder with element factory."""
        self.element_factory = element_factory

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
                item_content_start_idx = i + 1
                item_text = ""
                item_formatting: list[TextFormat] = []
                children: list[ListItem] = []
                j = item_content_start_idx
                item_content_processed_up_to = j

                while j < list_end_idx and not (
                    tokens[j].type == "list_item_close"
                    and tokens[j].level == token.level
                ):
                    item_token = tokens[j]
                    if item_token.type == "paragraph_open":
                        inline_idx = j + 1
                        if (
                            inline_idx < list_end_idx
                            and tokens[inline_idx].type == "inline"
                        ):
                            if item_text:
                                item_text += "\n"
                            current_text_offset = len(item_text)
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
                        j = self.find_closing_token(tokens, j, "paragraph_close")
                    elif item_token.type in ["bullet_list_open", "ordered_list_open"]:
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

                    item_content_processed_up_to = j
                    j += 1

                list_item_obj = ListItem(
                    text=item_text.strip(),
                    level=level,
                    formatting=item_formatting,
                    children=children,
                )
                items.append(list_item_obj)
                i = item_content_processed_up_to + 1
            else:
                i += 1
        return items

    def generate_bullet_list_element_requests(
        self,
        element: ListElement,
        slide_id: str,
    ) -> list[dict]:
        """Generate requests for a bullet list element."""
        # REFACTORED: Removed subheading_data and theme_placeholders parameters.
        return self.generate_list_element_requests(
            element,
            slide_id,
            "BULLET_DISC_CIRCLE_SQUARE",
        )

    def generate_list_element_requests(
        self,
        element: ListElement,
        slide_id: str,
        bullet_type: str,
    ) -> list[dict]:
        """
        Generate requests for a list element.
        """
        # REFACTORED: Removed all logic related to subheading_data and theme_placeholders.
        # JUSTIFICATION: Aligns with API_GEN_SPEC.md Rule #5.
        requests = []

        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", None) or (400, 200)

        if not element.object_id:
            element.object_id = self._generate_id(f"list_{slide_id}")

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

        autofit_request = {
            "updateShapeProperties": {
                "objectId": element.object_id,
                "fields": "autofit.autofitType",
                "shapeProperties": {"autofit": {"autofitType": "NONE"}},
            }
        }
        requests.append(autofit_request)

        if not hasattr(element, "items") or not element.items:
            return requests

        text_content, text_ranges = self._format_list_with_nesting(element.items)

        if text_content.strip():
            requests.append(
                {
                    "insertText": {
                        "objectId": element.object_id,
                        "insertionIndex": 0,
                        "text": text_content,
                    }
                }
            )
        else:
            return requests

        for range_info in text_ranges:
            start_index = range_info["start"]
            end_index = range_info["end"]

            requests.append(
                {
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
            )
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {
                            "type": "FIXED_RANGE",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                        "style": {
                            "spaceAbove": {"magnitude": 3, "unit": "PT"},
                            "spaceBelow": {"magnitude": 3, "unit": "PT"},
                            "lineSpacing": 115,
                        },
                        "fields": "spaceAbove,spaceBelow,lineSpacing",
                    }
                }
            )

            level = range_info.get("level", 0)
            if level > 0:
                indent_amount = level * 20.0
                requests.append(
                    {
                        "updateParagraphStyle": {
                            "objectId": element.object_id,
                            "textRange": {
                                "type": "FIXED_RANGE",
                                "startIndex": start_index,
                                "endIndex": end_index,
                            },
                            "style": {
                                "indentStart": {
                                    "magnitude": indent_amount,
                                    "unit": "PT",
                                },
                                "indentFirstLine": {
                                    "magnitude": indent_amount,
                                    "unit": "PT",
                                },
                            },
                            "fields": "indentStart,indentFirstLine",
                        }
                    }
                )

        for range_info in text_ranges:
            item = range_info.get("item")
            offset_mapping = range_info.get("offset_mapping", {})
            if item and hasattr(item, "formatting") and item.formatting:
                for text_format in item.formatting:
                    adjusted_start = offset_mapping.get(
                        text_format.start, range_info["start"]
                    )
                    adjusted_end = offset_mapping.get(
                        text_format.end, range_info["end"]
                    )
                    if adjusted_start < adjusted_end:
                        style_request = self._apply_text_formatting(
                            element_id=element.object_id,
                            style=self._format_to_style(text_format),
                            fields=self._format_to_fields(text_format),
                            start_index=adjusted_start,
                            end_index=adjusted_end,
                        )
                        requests.append(style_request)

        self._apply_color_directive(element, requests)
        self._apply_list_styling_directives(element, requests)

        return requests

    def _format_list_with_nesting(
        self, items: list[ListItem]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Format list items with proper nesting using tab characters."""
        text_content = ""
        text_ranges = []

        def process_items(items_list, level=0):
            nonlocal text_content, text_ranges
            for item in items_list:
                item_text = (
                    item.text.rstrip() if hasattr(item, "text") else str(item).rstrip()
                )
                tabs = "\t" * level
                lines = item_text.split("\n")
                tabbed_lines = [tabs + line for line in lines]
                tabbed_item_text = "\n".join(tabbed_lines)
                start_pos = len(text_content)
                text_content += tabbed_item_text + " \n"
                end_pos = len(text_content) - 2
                if end_pos <= start_pos:
                    end_pos = start_pos + 1
                offset_mapping = {}
                orig_pos = 0
                tabbed_pos = start_pos
                for line_idx, line in enumerate(lines):
                    if line_idx > 0:
                        tabbed_pos += 1
                    tabbed_pos += len(tabs)
                    for _i in range(len(line)):
                        offset_mapping[orig_pos] = tabbed_pos
                        orig_pos += 1
                        tabbed_pos += 1
                    if line_idx < len(lines) - 1:
                        orig_pos += 1
                text_ranges.append(
                    {
                        "start": start_pos,
                        "end": end_pos,
                        "level": level,
                        "offset_mapping": offset_mapping,
                        "item": item,
                    }
                )
                if hasattr(item, "children") and item.children:
                    process_items(item.children, level + 1)

        process_items(items)
        return text_content, text_ranges

    def _apply_color_directive(
        self, element: ListElement, requests: list[dict]
    ) -> None:
        """Apply color directive to a list element."""
        color_val = (element.directives or {}).get("color")
        if not isinstance(color_val, str):
            return

        try:
            # Use _format_to_style to handle hex or theme colors
            color_format = TextFormat(
                start=0, end=0, format_type=TextFormatType.COLOR, value=color_val
            )
            style = self._format_to_style(color_format)
            if "foregroundColor" in style:
                requests.append(
                    self._apply_text_formatting(
                        element_id=element.object_id,
                        style={"foregroundColor": style["foregroundColor"]},
                        fields="foregroundColor",
                        range_type="ALL",
                    )
                )
        except (ValueError, AttributeError):
            logger.warning(f"Invalid color value for list: {color_val}")

    def _apply_list_styling_directives(
        self, element: ListElement, requests: list[dict]
    ) -> None:
        """Apply additional styling directives to the list element."""
        if not hasattr(element, "directives") or not element.directives:
            return
        if "fontsize" in element.directives:
            font_size = element.directives["fontsize"]
            if isinstance(font_size, int | float) and font_size > 0:
                requests.append(
                    self._apply_text_formatting(
                        element_id=element.object_id,
                        style={
                            "fontSize": {"magnitude": float(font_size), "unit": "PT"}
                        },
                        fields="fontSize",
                        range_type="ALL",
                    )
                )
        if "font" in element.directives:
            font_family = element.directives["font"]
            if isinstance(font_family, str):
                requests.append(
                    self._apply_text_formatting(
                        element_id=element.object_id,
                        style={"fontFamily": font_family},
                        fields="fontFamily",
                        range_type="ALL",
                    )
                )
