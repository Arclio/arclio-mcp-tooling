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

        # FIXED: Consolidate all shape property updates into a single request.
        shape_props = {}
        fields = []

        # Default: Disable autofit
        shape_props["autofit"] = {"autofitType": "NONE"}
        fields.append("autofit.autofitType")

        # Add other shape properties from directives
        self._add_shape_properties(element, shape_props, fields)

        if shape_props:
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

        # FIXED: Pass section directives to paragraph styling to handle inheritance.
        # This is a bit of a workaround; ideally, directives are merged in the parser.
        # However, to avoid major refactoring, we handle it here.
        (element.directives or {}).copy()

        self._apply_paragraph_styling(element, requests)
        self._apply_text_color_directive(element, requests)
        self._apply_font_size_directive(element, requests)

        return requests

    def _add_shape_properties(
        self, element: TextElement, props: dict, fields: list[str]
    ):
        """Helper to aggregate all shape-level property updates."""
        directives = element.directives or {}

        # Vertical Alignment
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

        # Background Properties
        bg_dir = directives.get("background")
        if isinstance(bg_dir, tuple) and len(bg_dir) == 2:
            bg_type, bg_val = bg_dir
            if bg_type == "color":
                try:
                    rgb = self._hex_to_rgb(bg_val)
                    props.setdefault("shapeBackgroundFill", {})["solidFill"] = {
                        "color": {"rgbColor": rgb}
                    }
                    fields.append("shapeBackgroundFill.solidFill.color.rgbColor")
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid background color value: {bg_val}")

        # Border Properties (simplified)
        border_val = directives.get("border")
        if isinstance(border_val, str):
            props["outline"] = {"dashStyle": "SOLID"}
            fields.append("outline.dashStyle")

    def _apply_paragraph_styling(self, element: TextElement, requests: list[dict]):
        style_updates = {}
        fields_list = []
        directives = element.directives or {}

        line_spacing = directives.get("line-spacing", 1.15)
        if isinstance(line_spacing, int | float) and line_spacing > 0:
            style_updates["lineSpacing"] = float(line_spacing) * 100.0
            fields_list.append("lineSpacing")

        alignment_map = {
            AlignmentType.LEFT: "START",
            AlignmentType.CENTER: "CENTER",
            AlignmentType.RIGHT: "END",
            AlignmentType.JUSTIFY: "JUSTIFIED",
        }
        api_alignment = alignment_map.get(element.horizontal_alignment, "START")
        style_updates["alignment"] = api_alignment
        fields_list.append("alignment")

        if style_updates:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": element.object_id,
                        "textRange": {"type": "ALL"},
                        "style": style_updates,
                        "fields": ",".join(sorted(set(fields_list))),
                    }
                }
            )

    def _apply_text_color_directive(self, element: TextElement, requests: list[dict]):
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
            logger.warning(f"Invalid text color value: {color_val}")

    def _apply_font_size_directive(self, element: TextElement, requests: list[dict]):
        font_size = (element.directives or {}).get("fontsize")
        if not isinstance(font_size, int | float) or font_size <= 0:
            return

        requests.append(
            self._apply_text_formatting(
                element_id=element.object_id,
                style={"fontSize": {"magnitude": float(font_size), "unit": "PT"}},
                fields="fontSize",
                range_type="ALL",
            )
        )
