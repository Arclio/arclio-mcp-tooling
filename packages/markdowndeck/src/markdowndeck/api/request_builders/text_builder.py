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
                start_index = min(
                    text_format.start, text_length - 1 if text_length > 0 else 0
                )
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

        # REFACTORED: Consolidate all paragraph and text styling into one method call.
        self._apply_styling_directives(element, requests)

        return requests

    def _add_shape_properties(
        self, element: TextElement, props: dict, fields: list[str]
    ):
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
        if isinstance(bg_dir, dict) and bg_dir.get("type") == "hex":
            bg_val = bg_dir.get("value")
            if bg_val:
                try:
                    rgb = self._hex_to_rgb(bg_val)
                    props.setdefault("shapeBackgroundFill", {})["solidFill"] = {
                        "color": {"rgbColor": rgb}
                    }
                    fields.append("shapeBackgroundFill.solidFill.color.rgbColor")
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid background color value: {bg_val}")
        elif isinstance(bg_dir, str):
            try:
                rgb = self._hex_to_rgb(bg_dir)
                props.setdefault("shapeBackgroundFill", {})["solidFill"] = {
                    "color": {"rgbColor": rgb}
                }
                fields.append("shapeBackgroundFill.solidFill.color.rgbColor")
            except (ValueError, AttributeError):
                logger.warning(f"Invalid background color value: {bg_dir}")

        if isinstance(directives.get("border"), str):
            props["outline"] = {"dashStyle": "SOLID"}
            fields.append("outline.dashStyle")

    def _apply_styling_directives(self, element: TextElement, requests: list[dict]):
        """Consolidates all text and paragraph styling from directives."""
        para_style_updates, para_fields = {}, []
        text_style_updates, text_fields = {}, []
        directives = element.directives or {}

        # Paragraph styles
        alignment_map = {
            AlignmentType.LEFT: "START",
            AlignmentType.CENTER: "CENTER",
            AlignmentType.RIGHT: "END",
            AlignmentType.JUSTIFY: "JUSTIFIED",
        }
        api_alignment = alignment_map.get(element.horizontal_alignment, "START")
        if "align" in directives:
            api_alignment = alignment_map.get(directives["align"], api_alignment)
        para_style_updates["alignment"] = api_alignment
        para_fields.append("alignment")

        line_spacing = directives.get("line-spacing", 1.15)
        if isinstance(line_spacing, int | float) and line_spacing > 0:
            para_style_updates["lineSpacing"] = float(line_spacing) * 100.0
            para_fields.append("lineSpacing")

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

        # Text styles
        if "color" in directives:
            color_val = directives["color"]
            color_str = (
                color_val.get("value") if isinstance(color_val, dict) else color_val
            )
            if color_str:
                try:
                    style = self._format_to_style(
                        TextFormat(0, 0, TextFormatType.COLOR, color_str)
                    )
                    if "foregroundColor" in style:
                        text_style_updates["foregroundColor"] = style["foregroundColor"]
                        text_fields.append("foregroundColor")
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid text color value: {color_str}")

        if "fontsize" in directives:
            try:
                font_size = float(directives["fontsize"])
                if font_size > 0:
                    text_style_updates["fontSize"] = {
                        "magnitude": font_size,
                        "unit": "PT",
                    }
                    text_fields.append("fontSize")
            except (ValueError, TypeError):
                logger.warning(f"Invalid font size value: {directives['fontsize']}")

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
