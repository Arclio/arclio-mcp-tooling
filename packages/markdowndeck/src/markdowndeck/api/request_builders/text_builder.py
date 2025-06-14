import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    TextElement,
    TextFormat,
    TextFormatType,
)

logger = logging.getLogger(__name__)


class TextRequestBuilder(BaseRequestBuilder):
    """Builder for text-related Google Slides API requests."""

    def generate_text_element_requests(
        self,
        element: TextElement,
        slide_id: str,
    ) -> list[dict]:
        """
        Generate requests for a text element. Always creates a new shape.
        """
        requests = []
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", None) or (300, 200)

        if not element.object_id:
            from copy import deepcopy

            element = deepcopy(element)
            element.object_id = self._generate_id(f"text_{slide_id}")

        requests.append(
            {
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
        )

        requests.append(
            {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "shapeProperties": {"autofit": {"autofitType": "NONE"}},
                    "fields": "autofit.autofitType",
                }
            }
        )

        shape_props = {}
        fields = []
        self._add_shape_properties(element, shape_props, fields)
        if shape_props and fields:
            requests.append(
                {
                    "updateShapeProperties": {
                        "objectId": element.object_id,
                        "shapeProperties": shape_props,
                        "fields": ",".join(sorted(set(fields))),
                    }
                }
            )

        if not element.text:
            return requests

        requests.append(
            {
                "insertText": {
                    "objectId": element.object_id,
                    "insertionIndex": 0,
                    "text": element.text,
                }
            }
        )

        if hasattr(element, "formatting") and element.formatting:
            for text_format in element.formatting:
                text_length = len(element.text)
                start_index = min(text_format.start, text_length - 1 if text_length > 0 else 0)
                end_index = min(text_format.end, text_length)
                if start_index < end_index:
                    requests.append(
                        self._apply_text_formatting(
                            element_id=element.object_id,
                            style=self._format_to_style(text_format),
                            fields=self._format_to_fields(text_format),
                            start_index=start_index,
                            end_index=end_index,
                        )
                    )

        self._apply_styling_directives(element, requests)

        return requests

    def _add_shape_properties(self, element: TextElement, props: dict, fields: list[str]):
        """Helper to aggregate all shape-level property updates."""
        directives = element.directives or {}
        valign_directive = directives.get("valign")
        content_alignment = None
        if element.element_type in [ElementType.TITLE, ElementType.SUBTITLE]:
            content_alignment = "MIDDLE"
        elif valign_directive and str(valign_directive).upper() in [
            "TOP",
            "MIDDLE",
            "BOTTOM",
        ]:
            content_alignment = str(valign_directive).upper()
        if content_alignment:
            props["contentAlignment"] = content_alignment
            fields.append("contentAlignment")

        bg_dir = directives.get("background")
        if isinstance(bg_dir, dict) and bg_dir.get("type") == "color":
            color_info = bg_dir.get("value")
            if color_info:
                # The value might be a simple string (hex) or another dict
                bg_val = color_info.get("value") if isinstance(color_info, dict) else color_info
                if isinstance(bg_val, str) and bg_val.startswith("#"):
                    try:
                        rgb = self._hex_to_rgb(bg_val)
                        props.setdefault("shapeBackgroundFill", {})["solidFill"] = {"color": {"rgbColor": rgb}}
                        fields.append("shapeBackgroundFill.solidFill.color")
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid background color value: {bg_val}")

    def _apply_styling_directives(self, element: TextElement, requests: list[dict]):
        """Consolidates all text and paragraph styling from directives into unified requests."""
        # REFACTORED: This logic is now consolidated to prevent multiple, conflicting update requests.
        para_style_updates, text_style_updates = {}, {}
        para_fields, text_fields = [], []
        directives = element.directives or {}

        # --- Paragraph Styles ---
        alignment_map = {
            AlignmentType.LEFT: "START",
            AlignmentType.CENTER: "CENTER",
            AlignmentType.RIGHT: "END",
            AlignmentType.JUSTIFY: "JUSTIFIED",
        }
        # Final alignment is determined by the directive, falling back to the element's attribute
        align_directive = directives.get("align", element.horizontal_alignment.value)
        api_alignment = alignment_map.get(align_directive, "START")

        para_style_updates["alignment"] = api_alignment
        para_fields.append("alignment")

        line_spacing = directives.get("line-spacing")
        if isinstance(line_spacing, int | float) and line_spacing > 0:
            para_style_updates["lineSpacing"] = float(line_spacing) * 100.0
            para_fields.append("lineSpacing")

        # --- Text Styles ---
        color_directive = directives.get("color")
        if isinstance(color_directive, dict) and color_directive.get("type") == "color":
            color_value = color_directive.get("value", {})
            # The value can be a string (named color) or a dict (hex)
            color_str = color_value.get("value") if isinstance(color_value, dict) else color_value
            if color_str:
                try:
                    style = self._format_to_style(TextFormat(0, 0, TextFormatType.COLOR, color_str))
                    if "foregroundColor" in style:
                        text_style_updates["foregroundColor"] = style["foregroundColor"]
                        text_fields.append("foregroundColor")
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid text color value: {color_str}")

        fontsize_directive = directives.get("fontsize")
        if fontsize_directive:
            try:
                font_size = float(fontsize_directive)
                if font_size > 0:
                    text_style_updates["fontSize"] = {
                        "magnitude": font_size,
                        "unit": "PT",
                    }
                    text_fields.append("fontSize")
            except (ValueError, TypeError):
                logger.warning(f"Invalid font size value: {fontsize_directive}")

        # --- Generate Consolidated Requests ---
        if para_style_updates:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": para_style_updates,
                        "fields": ",".join(sorted(set(para_fields))),
                    }
                }
            )

        if text_style_updates:
            requests.append(
                {
                    "updateTextStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": text_style_updates,
                        "fields": ",".join(sorted(set(text_fields))),
                    }
                }
            )
