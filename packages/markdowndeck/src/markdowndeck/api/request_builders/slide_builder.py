import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.api.validation import is_valid_image_url
from markdowndeck.layout.constants import DEFAULT_SLIDE_HEIGHT, DEFAULT_SLIDE_WIDTH
from markdowndeck.models import Slide, SlideLayout

logger = logging.getLogger(__name__)


class SlideRequestBuilder(BaseRequestBuilder):
    """Builder for slide-related Google Slides API requests."""

    def create_slide_request(self, slide: Slide) -> dict:
        """
        Create a request to make a new slide with a BLANK layout.
        """
        if not slide.object_id:
            slide.object_id = self._generate_id("slide")

        request = {
            "createSlide": {
                "objectId": slide.object_id,
                "slideLayoutReference": {"predefinedLayout": SlideLayout.BLANK.value},
            }
        }
        logger.debug(
            f"Created slide request with ID: {slide.object_id}, layout: {slide.layout.value}"
        )
        return request

    def create_background_request(self, slide: Slide) -> dict | None:
        """
        Creates a valid background update request for either a color or an image.
        """
        if not slide.background:
            return None

        background_type = slide.background.get("type")
        background_value = slide.background.get("value")
        page_background_fill = {}
        fields_mask_parts = []

        if background_type == "image":
            if not is_valid_image_url(background_value):
                from markdowndeck.api.placeholder import create_placeholder_image_url

                logger.warning(
                    f"Background image URL failed validation: {background_value}. Substituting with a placeholder URL."
                )
                width = int(DEFAULT_SLIDE_WIDTH)
                height = int(DEFAULT_SLIDE_HEIGHT)
                # REFACTORED: Use a short, public placeholder URL to avoid API length limits.
                background_value = create_placeholder_image_url(
                    width, height, "Invalid Background"
                )

            page_background_fill["stretchedPictureFill"] = {
                "contentUrl": background_value
            }
            fields_mask_parts.append(
                "pageBackgroundFill.stretchedPictureFill.contentUrl"
            )

        elif background_type == "color":
            if isinstance(background_value, dict):
                color_value_str = str(background_value.get("value")).strip()
            else:
                color_value_str = str(background_value).strip()

            if color_value_str.startswith("#"):
                rgb = self._hex_to_rgb(color_value_str)
                page_background_fill["solidFill"] = {"color": {"rgbColor": rgb}}
                fields_mask_parts.append("pageBackgroundFill.solidFill.color.rgbColor")
            else:
                named_colors = {
                    "black": "#000000",
                    "white": "#FFFFFF",
                    "red": "#FF0000",
                    "green": "#008000",
                    "blue": "#0000FF",
                }
                theme_colors = {
                    "TEXT1",
                    "BACKGROUND1",
                    "ACCENT1",
                }

                if color_value_str.lower() in named_colors:
                    rgb = self._hex_to_rgb(named_colors[color_value_str.lower()])
                    page_background_fill["solidFill"] = {"color": {"rgbColor": rgb}}
                    fields_mask_parts.append(
                        "pageBackgroundFill.solidFill.color.rgbColor"
                    )
                elif color_value_str.upper() in theme_colors:
                    page_background_fill["solidFill"] = {
                        "color": {"themeColor": color_value_str.upper()}
                    }
                    fields_mask_parts.append(
                        "pageBackgroundFill.solidFill.color.themeColor"
                    )
                else:
                    logger.warning(
                        f"Invalid color value for background: '{color_value_str}'."
                    )
                    return None
        else:
            return None

        if not page_background_fill:
            return None

        return {
            "updatePageProperties": {
                "objectId": slide.object_id,
                "pageProperties": {"pageBackgroundFill": page_background_fill},
                "fields": ",".join(fields_mask_parts),
            }
        }

    def create_notes_request(self, slide: Slide) -> list[dict]:
        """Create requests to add speaker notes to a slide."""
        if not slide.notes or not getattr(slide, "speaker_notes_object_id", None):
            return []

        return [
            {
                "deleteText": {
                    "objectId": slide.speaker_notes_object_id,
                    "textRange": {"type": "ALL"},
                }
            },
            {
                "insertText": {
                    "objectId": slide.speaker_notes_object_id,
                    "insertionIndex": 0,
                    "text": slide.notes,
                }
            },
        ]
