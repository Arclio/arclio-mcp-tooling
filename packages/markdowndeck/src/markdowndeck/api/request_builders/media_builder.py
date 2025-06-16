import contextlib
import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import ImageElement

logger = logging.getLogger(__name__)


class MediaRequestBuilder(BaseRequestBuilder):
    """Builder for media-related Google Slides API requests."""

    def generate_image_element_requests(
        self, element: ImageElement, slide_id: str
    ) -> list[dict]:
        """
        Generate requests for an image element.
        """
        requests = []
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", None) or (300, 200)

        if size == (0, 0):
            logger.warning(
                f"Skipping request generation for zero-sized image element on slide {slide_id}."
            )
            return []

        if not element.object_id:
            element.object_id = self._generate_id(f"image_{slide_id}")
            logger.debug(
                f"Generated missing object_id for image element: {element.object_id}"
            )

        create_image_request = {
            "createImage": {
                "objectId": element.object_id,
                "url": element.url,
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
        requests.append(create_image_request)

        if element.object_id and element.alt_text:
            alt_text_request = {
                "updatePageElementAltText": {
                    "objectId": element.object_id,
                    "title": "Image",
                    "description": element.alt_text,
                }
            }
            requests.append(alt_text_request)
            logger.debug(f"Added alt text for image: {element.alt_text[:30]}")

        # Apply border directive if present
        self._apply_border_directive(element, requests)

        return requests

    def _apply_border_directive(self, element: ImageElement, requests: list[dict]):
        """Apply border directive to create an outline on the image."""
        directives = element.directives or {}
        border_value = directives.get("border")

        if not border_value:
            return

        outline_props = self._parse_border_directive(border_value)
        if not outline_props:
            return

        # REFACTORED: Use `updateImageProperties` for Image elements, not `updateShapeProperties`.
        # This is the fix for the HttpError 400. The Google Slides API treats
        # Images and Shapes as distinct object types.
        requests.append(
            {
                "updateImageProperties": {
                    "objectId": element.object_id,
                    "imageProperties": {"outline": outline_props},
                    "fields": "outline",
                }
            }
        )
        logger.debug(
            f"Applied border to image element {element.object_id}: {border_value}"
        )

    def _parse_border_directive(self, border_value: str) -> dict | None:
        """Parse border directive string into Google Slides API outline properties."""
        if not isinstance(border_value, str):
            return None

        # Default values
        weight = {"magnitude": 1, "unit": "PT"}
        dash_style = "SOLID"
        rgb_color = {"red": 0, "green": 0, "blue": 0}

        # Parse the compound border string
        parts = border_value.split()
        for part in parts:
            if part.endswith(("pt", "px")):
                # Width part
                try:
                    width_value = float(part.rstrip("ptx"))
                    weight = {"magnitude": width_value, "unit": "PT"}
                except ValueError:
                    pass
            elif part.lower() in ["solid", "dashed", "dotted"]:
                # Style part
                style_map = {"solid": "SOLID", "dashed": "DASH", "dotted": "DOT"}
                dash_style = style_map.get(part.lower(), "SOLID")
            elif part.startswith("#"):
                # Color part (hex)
                with contextlib.suppress(ValueError):
                    rgb_color = self._hex_to_rgb(part)
            elif part.lower() in [
                "black",
                "white",
                "red",
                "green",
                "blue",
                "yellow",
                "cyan",
                "magenta",
            ]:
                # Named color
                color_map = {
                    "black": {"red": 0, "green": 0, "blue": 0},
                    "white": {"red": 1, "green": 1, "blue": 1},
                    "red": {"red": 1, "green": 0, "blue": 0},
                    "green": {"red": 0, "green": 1, "blue": 0},
                    "blue": {"red": 0, "green": 0, "blue": 1},
                    "yellow": {"red": 1, "green": 1, "blue": 0},
                    "cyan": {"red": 0, "green": 1, "blue": 1},
                    "magenta": {"red": 1, "green": 0, "blue": 1},
                }
                rgb_color = color_map.get(part.lower(), rgb_color)

        return {
            "weight": weight,
            "dashStyle": dash_style,
            "outlineFill": {"solidFill": {"color": {"rgbColor": rgb_color}}},
        }
