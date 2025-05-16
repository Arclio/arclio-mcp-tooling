"""Slide request builder for Google Slides API requests."""

import logging
import requests

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import ElementType, Slide, SlideLayout

logger = logging.getLogger(__name__)


class SlideRequestBuilder(BaseRequestBuilder):
    """Builder for slide-related Google Slides API requests."""

    # Standard placeholder types for common layouts
    LAYOUT_PLACEHOLDERS = {
        SlideLayout.TITLE: [
            {
                "type": "CENTERED_TITLE",
                "index": 0,
            },  # Often TITLE is CENTERED_TITLE or TITLE placeholder
        ],
        SlideLayout.TITLE_AND_BODY: [
            {"type": "TITLE", "index": 0},
            {"type": "BODY", "index": 0},
        ],
        SlideLayout.TITLE_AND_TWO_COLUMNS: [
            {"type": "TITLE", "index": 0},
            {"type": "BODY", "index": 0},  # Left column
            {"type": "BODY", "index": 1},  # Right column
        ],
        SlideLayout.TITLE_ONLY: [
            {"type": "TITLE", "index": 0},  # Or CENTERED_TITLE
        ],
        SlideLayout.SECTION_HEADER: [  # Common placeholders for SECTION_HEADER
            {"type": "TITLE", "index": 0},
            # {"type": "SUBTITLE", "index": 0}, # Less common for SECTION_HEADER, but possible
        ],
        SlideLayout.CAPTION_ONLY: [  # Common placeholders for CAPTION_ONLY
            {
                "type": "BODY",
                "index": 0,
            }  # Or specific CAPTION placeholder if theme defines it
        ],
        SlideLayout.BIG_NUMBER: [  # Common placeholders for BIG_NUMBER
            {"type": "TITLE", "index": 0},  # Often a smaller title
            {"type": "SUBTITLE", "index": 0},  # For the big number itself
            # {"type": "BODY", "index": 0}, # For accompanying text
        ],
        SlideLayout.BLANK: [],  # Blank layout has no predefined placeholders typically mapped this way
    }

    ELEMENT_TO_PLACEHOLDER_TYPE_MAP: dict[ElementType, str] = {
        ElementType.TITLE: "TITLE",
        ElementType.SUBTITLE: "SUBTITLE",
        ElementType.TEXT: "BODY",
        ElementType.BULLET_LIST: "BODY",
        ElementType.ORDERED_LIST: "BODY",
    }

    def create_slide_request(self, slide: Slide) -> dict:
        if not slide.object_id:
            slide.object_id = self._generate_id("slide")

        placeholder_id_mappings = []
        slide.placeholder_mappings = {}

        layout_specific_placeholders = self.LAYOUT_PLACEHOLDERS.get(slide.layout, [])

        for placeholder_info in layout_specific_placeholders:
            placeholder_type_api = placeholder_info["type"]
            placeholder_index_api = placeholder_info["index"]
            generated_placeholder_object_id = self._generate_id(
                f"{slide.object_id}_{placeholder_type_api.lower()}_{placeholder_index_api}"
            )
            placeholder_id_mappings.append(
                {
                    "layoutPlaceholder": {
                        "type": placeholder_type_api,
                        "index": placeholder_index_api,
                    },
                    "objectId": generated_placeholder_object_id,
                }
            )
            for (
                md_element_type,
                api_ph_type_from_map,
            ) in self.ELEMENT_TO_PLACEHOLDER_TYPE_MAP.items():
                if api_ph_type_from_map == placeholder_type_api:
                    key_for_mapping = (
                        f"{md_element_type.value}_{placeholder_index_api}"
                        if placeholder_type_api == "BODY" and placeholder_index_api > 0
                        else md_element_type
                    )
                    if key_for_mapping not in slide.placeholder_mappings:
                        slide.placeholder_mappings[key_for_mapping] = (
                            generated_placeholder_object_id
                        )
                        if (
                            md_element_type == ElementType.TITLE
                        ):  # Prioritize mapping TITLE ElementType
                            break

        request = {
            "createSlide": {
                "objectId": slide.object_id,
                "slideLayoutReference": {"predefinedLayout": slide.layout.value},
                "placeholderIdMappings": placeholder_id_mappings,
            }
        }
        logger.debug(
            f"Created slide request with ID: {slide.object_id}, layout: {slide.layout.value}, "
            f"{len(placeholder_id_mappings)} placeholder mappings. Mapped to model: {slide.placeholder_mappings}"
        )
        return request

    def create_background_request(self, slide: Slide) -> dict:
        if not slide.background:
            return {}
        background_type = slide.background.get("type")
        background_value = slide.background.get("value")
        page_background_fill = {}
        fields_mask_parts = []

        if background_type == "color":
            if background_value.startswith("#"):
                try:
                    rgb = self._hex_to_rgb(background_value)
                    page_background_fill["solidFill"] = {"color": {"rgbColor": rgb}}
                    fields_mask_parts.append(
                        "pageBackgroundFill.solidFill.color.rgbColor"
                    )
                except ValueError:
                    logger.warning(
                        f"Invalid hex color for background: {background_value}. Using default color."
                    )
                    # Fallback to a default color on error
                    page_background_fill["solidFill"] = {
                        "color": {
                            "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                        }
                    }
                    fields_mask_parts.append(
                        "pageBackgroundFill.solidFill.color.rgbColor"
                    )
            else:
                # List of valid theme colors
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

                # Check if the value is a valid theme color
                if background_value.upper() in theme_colors:
                    page_background_fill["solidFill"] = {
                        "color": {"themeColor": background_value.upper()}
                    }
                    fields_mask_parts.append(
                        "pageBackgroundFill.solidFill.color.themeColor"
                    )
                else:
                    # If it looks like a URL, switch to image type
                    if background_value.startswith(("http://", "https://")):
                        logger.warning(
                            f"Value '{background_value}' looks like a URL but was provided as color type. "
                            f"Switching to image type."
                        )
                        background_type = "image"
                        # Continue to the image handling code below
                    else:
                        logger.warning(
                            f"Unknown theme color name: {background_value}. Using default color."
                        )
                        # Fallback to a default color
                        page_background_fill["solidFill"] = {
                            "color": {
                                "rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                            }
                        }
                        fields_mask_parts.append(
                            "pageBackgroundFill.solidFill.color.rgbColor"
                        )

        # Now handle image backgrounds (including those switched from invalid color type)
        if background_type == "image":
            # FIXED: Validate image URLs before including them in API requests
            if not self._is_valid_image_url(background_value):
                logger.warning(
                    f"Background image URL is invalid or inaccessible: {background_value}. "
                    f"Using a default solid color background instead."
                )
                # Use a light gray color as fallback
                page_background_fill["solidFill"] = {
                    "color": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
                }
                fields_mask_parts.append("pageBackgroundFill.solidFill.color.rgbColor")
            else:
                page_background_fill["stretchedPictureFill"] = {
                    "contentUrl": background_value
                }
                fields_mask_parts.append(
                    "pageBackgroundFill.stretchedPictureFill.contentUrl"
                )
        elif background_type != "color":  # Handle any other unknown background type
            logger.warning(
                f"Unknown background type: {background_type} for slide {slide.object_id}. "
                f"Using default color."
            )
            # Use a light gray color as fallback
            page_background_fill["solidFill"] = {
                "color": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
            }
            fields_mask_parts.append("pageBackgroundFill.solidFill.color.rgbColor")

        if not page_background_fill or not fields_mask_parts:
            logger.warning(
                f"No valid background properties generated for slide {slide.object_id}"
            )
            return {}

        request = {
            "updatePageProperties": {
                "objectId": slide.object_id,
                "pageProperties": {"pageBackgroundFill": page_background_fill},
                "fields": ",".join(fields_mask_parts),
            }
        }
        logger.debug(
            f"Created background request for slide: {slide.object_id} with fields: {request['updatePageProperties']['fields']}"
        )
        return request

    def create_notes_request(self, slide: Slide) -> list[dict]:
        """
        Create requests to add speaker notes to a slide.
        Only generates requests if there are actual notes and a speaker_notes_object_id.
        Avoids generating deleteText requests if notes content is empty (preventing API errors).

        Args:
            slide: The slide to add notes to

        Returns:
            List of request dictionaries
        """
        if not slide.notes:
            return []

        speaker_notes_shape_id = getattr(slide, "speaker_notes_object_id", None)
        if not speaker_notes_shape_id:
            # This is expected for newly created slides - the notes shape ID
            # isn't assigned until after the slide is created. Notes would need
            # to be added in a separate API call after slide creation.
            logger.warning(
                f"Cannot create notes request for slide {slide.object_id}: "
                "speaker_notes_object_id is missing. Notes content will be ignored."
            )
            return []

        # Since we know slide.notes is not empty at this point, we can safely
        # delete existing text and insert new text
        requests = [
            {
                "deleteText": {
                    "objectId": speaker_notes_shape_id,
                    "textRange": {"type": "ALL"},
                }
            },
            {
                "insertText": {
                    "objectId": speaker_notes_shape_id,
                    "insertionIndex": 0,
                    "text": slide.notes,
                }
            },
        ]

        logger.debug(
            f"Created delete and insert speaker notes requests for notesId: {speaker_notes_shape_id}"
        )
        return requests

    def _get_element_type_for_placeholder(
        self, placeholder_type: str
    ) -> ElementType | None:
        for element_type, api_ph_type in self.ELEMENT_TO_PLACEHOLDER_TYPE_MAP.items():
            if api_ph_type == placeholder_type:
                return element_type
        if (
            placeholder_type == "CENTERED_TITLE"
        ):  # Common API placeholder type for titles
            return ElementType.TITLE
        return None

    def _is_valid_image_url(self, url: str) -> bool:
        """
        Validate if a URL is a valid image URL.

        This performs both format validation and image accessibility checking.
        Google Slides API requires images to be accessible.

        Args:
            url: The URL to validate

        Returns:
            bool: True if the URL is valid and accessible
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
            # Use HEAD request to check image existence
            head_response = requests.head(url, timeout=3, allow_redirects=True)

            # Check status code
            if head_response.status_code != 200:
                logger.warning(
                    f"Background image URL returned status code {head_response.status_code}: {url}"
                )
                return False

            # Verify content type is an image
            content_type = head_response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    f"URL does not point to an image (content-type: {content_type}): {url}"
                )
                return False

            return True
        except Exception as e:
            # If we can't access the image, log warning and reject it
            logger.warning(f"Background image verification failed for {url}: {e}")
            return False
