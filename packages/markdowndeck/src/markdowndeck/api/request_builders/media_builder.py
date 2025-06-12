"""Media request builder for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.api.validation import is_valid_image_url
from markdowndeck.models import ImageElement

logger = logging.getLogger(__name__)


class MediaRequestBuilder(BaseRequestBuilder):
    """Builder for media-related Google Slides API requests."""

    def generate_image_element_requests(
        self, element: ImageElement, slide_id: str
    ) -> list[dict]:
        """
        Generate requests for an image element.

        Args:
            element: The image element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        if not is_valid_image_url(element.url):
            logger.warning(
                f"Image URL is invalid or inaccessible: {element.url}. "
                f"Skipping image element creation."
            )
            return []

        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", None) or (300, 200)

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
            # REFACTORED: Set title to "Image" per API_GEN_SPEC.md.
            alt_text_request = {
                "updatePageElementAltText": {
                    "objectId": element.object_id,
                    "title": "Image",  # Set a meaningful title for accessibility.
                    "description": element.alt_text,
                }
            }
            requests.append(alt_text_request)
            logger.debug(f"Added alt text for image: {element.alt_text[:30]}")

        return requests
