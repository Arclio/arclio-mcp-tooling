"""Text request builder for Google Slides API requests."""

import logging
from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    TextElement,
)

logger = logging.getLogger(__name__)


class TextRequestBuilder(BaseRequestBuilder):
    """Builder for text-related Google Slides API requests."""

    def generate_text_element_requests(
        self,
        element: TextElement,
        slide_id: str,
        theme_placeholders: dict[str, str] = None,
    ) -> list[dict]:
        """
        Generate requests for a text element.
        """
        requests = []
        # Check if this element should use a theme placeholder
        if theme_placeholders and element.element_type in theme_placeholders:
            return self._handle_themed_text_element(
                element, theme_placeholders[element.element_type]
            )
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (300, 200))
        if not element.object_id:
            element.object_id = self._generate_id(f"text_{slide_id}")
            logger.debug(
                f"Generated missing object_id for text element: {element.object_id}"
            )
        create_textbox_request = {
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
        requests.append(create_textbox_request)

        # Removed autofit request since only NONE is supported by the Google Slides REST API
        # and NONE is the default state, so we don't need to set it explicitly

        # --- CORRECTED SECTION FOR CONTENT ALIGNMENT ---
        # Define content alignment for text box (vertical alignment)
        content_alignment = None
        if (
            element.element_type == ElementType.TITLE
            or element.element_type == ElementType.SUBTITLE
        ):
            content_alignment = "MIDDLE"
        elif hasattr(element, "directives") and "textanchor" in element.directives:
            anchor_directive = str(element.directives["textanchor"]).upper()
            if anchor_directive in ["TOP", "MIDDLE", "BOTTOM"]:
                content_alignment = anchor_directive

        # Only set contentAlignment if needed - it's a direct property of shapeProperties
        if content_alignment:
            content_alignment_request = {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "fields": "contentAlignment",
                    "shapeProperties": {"contentAlignment": content_alignment},
                }
            }
            requests.append(content_alignment_request)
            logger.debug(
                f"Added contentAlignment '{content_alignment}' to element {element.object_id}"
            )
        # --- END OF CORRECTED SECTION ---

        if not element.text:
            return requests
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": element.text,
            }
        }
        requests.append(insert_text_request)
        if hasattr(element, "formatting") and element.formatting:
            for text_format in element.formatting:
                text_length = len(element.text)
                start_index = min(
                    text_format.start, text_length - 1 if text_length > 0 else 0
                )
                end_index = min(text_format.end, text_length)
                if start_index < 0:
                    start_index = 0
                if start_index >= end_index and text_length > 0:
                    if text_format.start >= text_format.end:
                        logger.warning(
                            f"Skipping invalid formatting range: start({text_format.start}) >= end({text_format.end}) for text '{element.text}'"
                        )
                        continue
                    start_index = max(0, end_index - 1)
                if start_index < end_index:
                    style_request = self._apply_text_formatting(
                        element_id=element.object_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=start_index,
                        end_index=end_index,
                    )
                    requests.append(style_request)
                elif text_format.start == text_format.end == 0 and not element.text:
                    pass
                elif text_format.start == text_format.end and text_format.start == len(
                    element.text
                ):
                    pass
                else:
                    logger.warning(
                        f"Skipping formatting due to invalid range after adjustment: start({start_index}) >= end({end_index}) for text '{element.text}'"
                    )
        if element.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
            paragraph_style_payload = {
                "alignment": "CENTER",
                "spaceAbove": {"magnitude": 0, "unit": "PT"},
                "spaceBelow": {"magnitude": 6, "unit": "PT"},
            }
            fields_list = "alignment,spaceAbove,spaceBelow"
            # Titles/Subtitles often have default line spacing from the theme.
            # Only add lineSpacing if explicitly different or always desired.
            # paragraph_style_payload["lineSpacing"] = 1.15 # Example if needed
            # fields_list += ",lineSpacing"
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": paragraph_style_payload,
                        "fields": fields_list,
                    }
                }
            )
        elif hasattr(element, "horizontal_alignment") and element.horizontal_alignment:
            alignment_map = {
                AlignmentType.LEFT: "START",
                AlignmentType.CENTER: "CENTER",
                AlignmentType.RIGHT: "END",
                AlignmentType.JUSTIFY: "JUSTIFIED",
            }
            api_alignment = alignment_map.get(element.horizontal_alignment, "START")
            paragraph_style_for_text = {
                "alignment": api_alignment,
                "spaceAbove": {"magnitude": 0, "unit": "PT"},
                "spaceBelow": {"magnitude": 0, "unit": "PT"},
                "lineSpacing": 1.15,  # API expects float (e.g., 1.0 for single, 1.15 for 115%)
            }
            fields_for_text_para = "alignment,spaceAbove,spaceBelow,lineSpacing"
            if element.element_type == ElementType.TEXT and hasattr(element, "text"):
                text = element.text.strip()
                is_heading = text.startswith("#") or (
                    hasattr(element, "directives")
                    and "fontsize" in element.directives
                    and isinstance(element.directives["fontsize"], (int, float))
                    and element.directives["fontsize"] >= 16
                )
                if is_heading:
                    paragraph_style_for_text["spaceAbove"] = {
                        "magnitude": 6,
                        "unit": "PT",
                    }
                    paragraph_style_for_text["spaceBelow"] = {
                        "magnitude": 3,
                        "unit": "PT",
                    }
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": paragraph_style_for_text,
                        "fields": fields_for_text_para,
                    }
                }
            )
        if (
            hasattr(element, "directives")
            and element.directives
            and "valign" in element.directives
        ):
            valign_value = element.directives["valign"]
            if isinstance(valign_value, str):
                valign_map = {"top": "TOP", "middle": "MIDDLE", "bottom": "BOTTOM"}
                api_valign = valign_map.get(valign_value.lower())
                if api_valign:
                    # This updates ShapeProperties.contentAlignment
                    requests.append(
                        {
                            "updateShapeProperties": {
                                "objectId": element.object_id,
                                "fields": "contentAlignment",
                                "shapeProperties": {"contentAlignment": api_valign},
                            }
                        }
                    )
                    logger.debug(
                        f"Applied contentAlignment '{api_valign}' to element {element.object_id}"
                    )
        self._apply_paragraph_styling(
            element, requests
        )  # Handles directives like line-spacing, para-spacing, indents
        self._apply_text_color_directive(element, requests)
        self._apply_font_size_directive(element, requests)
        self._apply_background_directive(element, requests)  # Shape background
        self._apply_border_directive(element, requests)  # Shape outline
        self._apply_padding_directive(element, requests)  # Handle padding directive
        return requests

    def _handle_themed_text_element(
        self, element: TextElement, placeholder_id: str
    ) -> list[dict]:
        requests = []
        element.object_id = placeholder_id
        if element.text:
            requests.append(
                {
                    "insertText": {
                        "objectId": placeholder_id,
                        "insertionIndex": 0,
                        "text": element.text,
                    }
                }
            )
            if hasattr(element, "formatting") and element.formatting:
                for text_format in element.formatting:
                    text_length = len(element.text)
                    start_index = min(
                        text_format.start, text_length - 1 if text_length > 0 else 0
                    )
                    end_index = min(text_format.end, text_length)
                    if start_index < 0:
                        start_index = 0
                    if start_index >= end_index and text_length > 0:
                        if text_format.start >= text_format.end:
                            logger.warning(
                                f"Skipping invalid themed formatting: start({text_format.start}) >= end({text_format.end}) for '{element.text}'"
                            )
                            continue
                        start_index = max(0, end_index - 1)
                    if start_index < end_index:
                        requests.append(
                            self._apply_text_formatting(
                                element_id=placeholder_id,
                                style=self._format_to_style(text_format),
                                fields=self._format_to_fields(text_format),
                                start_index=start_index,
                                end_index=end_index,
                            )
                        )
                    elif text_format.start == text_format.end == 0 and not element.text:
                        pass
                    elif (
                        text_format.start == text_format.end
                        and text_format.start == len(element.text)
                    ):
                        pass
                    else:
                        logger.warning(
                            f"Skipping themed formatting due to invalid range: start({start_index}) >= end({end_index}) for '{element.text}'"
                        )
            # For themed elements, paragraph style is mostly from the theme.
            # We might only want to apply minimal or very specific overrides.
            # The old code used "spaceMultiple: 115", which implies lineSpacing: 1.15.
            # Let's make it conditional or minimal to avoid overriding theme too much.
            para_style_payload = {
                "objectId": placeholder_id,
                "textRange": {"type": "ALL"},
                "style": {},
                "fields": "",
            }
            para_fields_list = []
            if (
                element.element_type == ElementType.TITLE
                or element.element_type == ElementType.SUBTITLE
            ):
                para_style_payload["style"][
                    "alignment"
                ] = "CENTER"  # Titles often centered
                para_fields_list.append("alignment")
                # Themes usually handle title spacing well, but if needed:
                # para_style_payload["style"]["spaceBelow"] = {"magnitude": 6, "unit": "PT"}
                # para_fields_list.append("spaceBelow")
            # Only apply if there's something specific to set, otherwise let theme control.
            if para_fields_list:
                para_style_payload["fields"] = ",".join(para_fields_list)
                requests.append({"updateParagraphStyle": para_style_payload})
            # Apply specific directives if they should override theme (e.g. explicit color)
            self._apply_text_color_directive(element, requests)
            self._apply_font_size_directive(element, requests)
        logger.debug(
            f"Generated {len(requests)} requests for themed element {element.element_type} using placeholder {placeholder_id}"
        )
        return requests

    def _apply_paragraph_styling(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        if not hasattr(element, "directives") or not element.directives:
            return
        style_updates = {}
        fields = []
        if "line-spacing" in element.directives:
            spacing = element.directives["line-spacing"]
            if isinstance(spacing, (int, float)) and spacing > 0:
                style_updates["lineSpacing"] = float(
                    spacing
                )  # API expects float (e.g., 1.15 for 115%)
                fields.append("lineSpacing")
        if "para-spacing-before" in element.directives:
            spacing = element.directives["para-spacing-before"]
            if isinstance(spacing, (int, float)) and spacing >= 0:
                style_updates["spaceAbove"] = {
                    "magnitude": float(spacing),
                    "unit": "PT",
                }
                fields.append("spaceAbove")
        if "para-spacing-after" in element.directives:
            spacing = element.directives["para-spacing-after"]
            if isinstance(spacing, (int, float)) and spacing >= 0:
                style_updates["spaceBelow"] = {
                    "magnitude": float(spacing),
                    "unit": "PT",
                }
                fields.append("spaceBelow")
        if "indent-start" in element.directives:
            indent = element.directives["indent-start"]
            if isinstance(indent, (int, float)) and indent >= 0:
                style_updates["indentStart"] = {
                    "magnitude": float(indent),
                    "unit": "PT",
                }
                fields.append("indentStart")
        if "indent-first-line" in element.directives:
            indent = element.directives["indent-first-line"]
            if isinstance(indent, (int, float)):
                style_updates["indentFirstLine"] = {
                    "magnitude": float(indent),
                    "unit": "PT",
                }
                fields.append("indentFirstLine")
        if style_updates and fields:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": style_updates,
                        "fields": ",".join(sorted(list(set(fields)))),
                    }
                }
            )

    def _apply_text_color_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        if not (
            hasattr(element, "directives")
            and element.directives
            and "color" in element.directives
        ):
            return
        color_val_dir = element.directives["color"]
        actual_color_val = (
            color_val_dir[1]
            if isinstance(color_val_dir, tuple)
            and len(color_val_dir) == 2
            and color_val_dir[0] == "color"
            else color_val_dir if isinstance(color_val_dir, str) else None
        )
        if not actual_color_val:
            return
        color_spec = None
        if actual_color_val.startswith("#"):
            try:
                color_spec = {
                    "opaqueColor": {"rgbColor": self._hex_to_rgb(actual_color_val)}
                }
            except ValueError:
                logger.warning(f"Invalid hex color for text: {actual_color_val}")
                return
        else:
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
                "HYPERLINK",
                "FOLLOWED_HYPERLINK",
                "DARK1",
                "LIGHT1",
            ]
            if actual_color_val.upper() in theme_colors:
                color_spec = {"opaqueColor": {"themeColor": actual_color_val.upper()}}
            else:
                logger.warning(f"Unknown theme color name for text: {actual_color_val}")
                return
        if color_spec:
            requests.append(
                self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"foregroundColor": color_spec},
                    fields="foregroundColor",
                    range_type="ALL",
                )
            )

    def _apply_font_size_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        if not (
            hasattr(element, "directives")
            and element.directives
            and "fontsize" in element.directives
        ):
            return
        font_size_val = element.directives["fontsize"]
        if isinstance(font_size_val, (int, float)) and font_size_val > 0:
            requests.append(
                self._apply_text_formatting(
                    element_id=element.object_id,
                    style={
                        "fontSize": {"magnitude": float(font_size_val), "unit": "PT"}
                    },
                    fields="fontSize",
                    range_type="ALL",
                )
            )
        else:
            logger.warning(f"Invalid fontsize directive value: {font_size_val}")

    def _apply_background_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        if not (
            hasattr(element, "directives")
            and element.directives
            and "background" in element.directives
        ):
            return
        bg_dir = element.directives["background"]
        if not isinstance(bg_dir, tuple) or len(bg_dir) != 2:
            logger.warning(f"Unexpected background directive format: {bg_dir}")
            return
        bg_type, bg_val_str = bg_dir
        fill_props = None
        if bg_type == "color":
            if bg_val_str.startswith("#"):
                try:
                    fill_props = {
                        "solidFill": {
                            "color": {"rgbColor": self._hex_to_rgb(bg_val_str)}
                        }
                    }
                    fields = "shapeBackgroundFill.solidFill.color.rgbColor"
                except ValueError:
                    logger.warning(f"Invalid hex color for background: {bg_val_str}")
                    return
            else:
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
                    "DARK1",
                    "LIGHT1",
                ]
                if bg_val_str.upper() in theme_colors:
                    fill_props = {
                        "solidFill": {"color": {"themeColor": bg_val_str.upper()}}
                    }
                    fields = "shapeBackgroundFill.solidFill.color.themeColor"
                else:
                    logger.warning(
                        f"Unknown theme color name for background: {bg_val_str}"
                    )
                    return
        elif bg_type == "url":
            fill_props = {"stretchedPictureFill": {"contentUrl": bg_val_str}}
            fields = "shapeBackgroundFill.stretchedPictureFill.contentUrl"
        else:
            logger.warning(f"Unsupported background type: {bg_type}")
            return
        if fill_props:
            requests.append(
                {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "fields": fields,
                        "shapeProperties": {"shapeBackgroundFill": fill_props},
                    }
                }
            )

    def _apply_border_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        if not (
            hasattr(element, "directives")
            and element.directives
            and "border" in element.directives
        ):
            return
        border_val_dir = element.directives["border"]
        border_str = (
            border_val_dir[1]
            if isinstance(border_val_dir, tuple)
            and len(border_val_dir) == 2
            and border_val_dir[0] == "value"
            else border_val_dir if isinstance(border_val_dir, str) else None
        )
        if not border_str:
            logger.warning(f"Unsupported border directive format: {border_val_dir}")
            return
        parts, weight_pt, dash_style, hex_color_str = (
            border_str.split(),
            1.0,
            "SOLID",
            "#000000",
        )
        final_fields = []
        for part in parts:
            p_low = part.lower()
            if p_low.endswith("pt") or p_low.endswith("px"):
                try:
                    weight_pt = float(p_low.rstrip("ptx"))
                    final_fields.append("outline.weight")
                except ValueError:
                    pass
            elif p_low in ["solid", "dash", "dot", "dashed", "dotted"]:
                dash_style = {"solid": "SOLID", "dash": "DASH", "dotted": "DOT"}.get(
                    p_low, "SOLID"
                )
                final_fields.append("outline.dashStyle")
            elif p_low.startswith("#"):
                hex_color_str = p_low
                final_fields.append("outline.outlineFill.solidFill.color")
            else:
                named_colors = {
                    "black": "#000000",
                    "white": "#FFFFFF",
                    "red": "#FF0000",
                    "blue": "#0000FF",
                    "green": "#008000",
                }
                theme_colors = ["TEXT1", "BACKGROUND1", "ACCENT1"]
                if p_low in named_colors:
                    hex_color_str = named_colors[p_low]
                    final_fields.append("outline.outlineFill.solidFill.color")
                elif p_low.upper() in theme_colors:
                    hex_color_str = p_low.upper()
                    final_fields.append("outline.outlineFill.solidFill.color")
        try:
            rgb_or_theme = (
                {"rgbColor": self._hex_to_rgb(hex_color_str)}
                if hex_color_str.startswith("#")
                else {"themeColor": hex_color_str}
            )
        except ValueError:
            rgb_or_theme = {"rgbColor": {"red": 0, "green": 0, "blue": 0}}
        if final_fields:
            requests.append(
                {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "fields": ",".join(sorted(list(set(final_fields)))),
                        "shapeProperties": {
                            "outline": {
                                "outlineFill": {"solidFill": {"color": rgb_or_theme}},
                                "weight": {"magnitude": weight_pt, "unit": "PT"},
                                "dashStyle": dash_style,
                            }
                        },
                    }
                }
            )

    def _apply_padding_directive(
        self, element: TextElement, requests: list[dict]
    ) -> None:
        """
        Handle the padding directive for a text element.

        NOTE: The Google Slides REST API does not directly support textBoxProperties
        for setting insets (padding). While these properties exist in the object model
        and in the Google Apps Script API, they are not accessible through the REST API's
        updateShapeProperties request. We provide this method for compatibility with the
        directive but log a warning about the API limitation.

        Args:
            element: The text element
            requests: List to append requests to
        """
        if not (
            hasattr(element, "directives")
            and element.directives
            and "padding" in element.directives
        ):
            return

        padding_value = element.directives["padding"]
        if isinstance(padding_value, (int, float)) and padding_value >= 0:
            logger.warning(
                f"Padding directive with value {padding_value} cannot be applied: "
                "textBoxProperties is not supported in the Google Slides REST API. "
                "This feature is only available in Google Apps Script."
            )
            # No request is added as this feature isn't supported in the REST API

    # _apply_text_formatting, _format_to_style, _format_to_fields are from BaseRequestBuilder
    # No need to redefine them here if they are inherited and sufficient.
    # Ensure BaseRequestBuilder's versions are correct and used.
