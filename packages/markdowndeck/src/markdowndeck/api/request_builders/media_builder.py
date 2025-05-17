"""Media request builder for Google Slides API requests."""

import logging

import requests

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

        Args:
            element: The image element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (300, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"image_{slide_id}")
            logger.debug(
                f"Generated missing object_id for image element: {element.object_id}"
            )

        # Validate image URL
        if not element.url or not self._is_valid_image_url(element.url):
            logger.warning(f"Invalid image URL: {element.url}. Creating a placeholder.")

            # Create a placeholder shape instead of image
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

            # Add placeholder text
            insert_text_request = {
                "insertText": {
                    "objectId": element.object_id,
                    "insertionIndex": 0,
                    "text": "[Image not available]",
                }
            }
            requests.append(insert_text_request)

            # Style the placeholder text to be centered
            style_request = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": {"alignment": "CENTER"},
                    "fields": "alignment",
                }
            }
            requests.append(style_request)

            # Style the placeholder text to be

            # Style the placeholder text to be centered vertically
            style_request2 = {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "fields": "contentAlignment",
                    "shapeProperties": {"contentAlignment": "MIDDLE"},
                }
            }
            requests.append(style_request2)

            # Add a light border to indicate it's a placeholder
            border_request = {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "fields": "outline.outlineFill.solidFill.color,outline.weight,outline.dashStyle",
                    "shapeProperties": {
                        "outline": {
                            "outlineFill": {
                                "solidFill": {
                                    "color": {
                                        "rgbColor": {
                                            "red": 0.7,
                                            "green": 0.7,
                                            "blue": 0.7,
                                        }
                                    }
                                }
                            },
                            "weight": {"magnitude": 1.0, "unit": "PT"},
                            "dashStyle": "DASH",
                        }
                    },
                }
            }
            requests.append(border_request)

            # Add light gray background
            bg_request = {
                "updateShapeProperties": {
                    "objectId": element.object_id,
                    "fields": "shapeBackgroundFill.solidFill.color",
                    "shapeProperties": {
                        "shapeBackgroundFill": {
                            "solidFill": {
                                "color": {
                                    "rgbColor": {
                                        "red": 0.95,
                                        "green": 0.95,
                                        "blue": 0.95,
                                    }
                                }
                            }
                        }
                    },
                }
            }
            requests.append(bg_request)

            return requests

        # Create image
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

        # FIXED: Add alt text correctly using updatePageElementAltText
        # Only add if both object_id is valid and alt_text is not empty
        if element.object_id and element.alt_text:
            alt_text_request = {
                "updatePageElementAltText": {
                    "objectId": element.object_id,
                    "title": "",  # Optional title for the alt text
                    "description": element.alt_text,  # The actual alt text
                }
            }
            requests.append(alt_text_request)
            logger.debug(f"Added alt text for image: {element.alt_text[:30]}")

        return requests

    def _is_valid_image_url(self, url: str) -> bool:
        """
        Validate if a URL is a valid image URL.

        This performs both format validation and image accessibility checking.
        Google Slides API requires images to be accessible and not too large.

        Args:
            url: The URL to validate

        Returns:
            bool: True if the URL is valid, accessible, and not too large
        """
        if not url:
            return False

        # Only allow http/https URLs
        if not (url.startswith("http://") or url.startswith("https://")):
            return False

        # Check for common image extensions
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]
        has_valid_extension = any(url.lower().endswith(ext) for ext in image_extensions)

        # If no extension, at least make sure it's a properly formed URL with a domain
        if not has_valid_extension and "." not in url.split("//", 1)[-1]:
            return False

        # Check if image actually exists and is accessible
        try:
            # Use HEAD request to check image existence and headers
            head_response = requests.head(url, timeout=5, allow_redirects=True)

            # Check status code first
            if head_response.status_code != 200:
                logger.warning(
                    f"Image URL returned status code {head_response.status_code}: {url}"
                )
                return False

            # Verify content type is an image
            content_type = head_response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    f"URL does not point to an image (content-type: {content_type}): {url}"
                )
                return False

            # Get content length from headers
            content_length = head_response.headers.get("content-length")

            # Check if content length is available and validate size
            # 25 MB limit (conservative, actual limit is higher but varies)
            if content_length and int(content_length) > 25 * 1024 * 1024:
                logger.warning(
                    f"Image URL too large ({int(content_length) / (1024 * 1024):.2f} MB): {url}"
                )
                return False

            return True
        except Exception as e:
            # If we can't access the image or verify it, log warning and reject it
            logger.warning(f"Image verification failed for {url}: {e}")
            return False
