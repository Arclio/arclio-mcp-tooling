"""Slide request builder for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.api.validation import is_valid_image_url
from markdowndeck.models import Slide, SlideLayout

logger = logging.getLogger(__name__)


class SlideRequestBuilder(BaseRequestBuilder):
    """Builder for slide-related Google Slides API requests."""

    def create_slide_request(self, slide: Slide) -> dict:
        """
        Create a request to make a new slide with a BLANK layout.
        """
        # REFACTORED: Removed all placeholder mapping logic.
        # JUSTIFICATION: Aligns with API_GEN_SPEC.md Rule #5 ("Blank Canvas First").
        # The generator no longer uses theme placeholders. This also fixes the statelessness
        # bug where the slide's placeholder_mappings attribute was being mutated.
        if not slide.object_id:
            slide.object_id = self._generate_id("slide")

        request = {
            "createSlide": {
                "objectId": slide.object_id,
                # Per spec, all slides are created with a BLANK layout.
                "slideLayoutReference": {"predefinedLayout": SlideLayout.BLANK.value},
            }
        }
        logger.debug(
            f"Created slide request with ID: {slide.object_id}, layout: {slide.layout.value}"
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
                rgb = self._hex_to_rgb(background_value)
                page_background_fill["solidFill"] = {"color": {"rgbColor": rgb}}
                fields_mask_parts.append("pageBackgroundFill.solidFill.color.rgbColor")
            else:
                page_background_fill["solidFill"] = {
                    "color": {"themeColor": background_value.upper()}
                }
                fields_mask_parts.append(
                    "pageBackgroundFill.solidFill.color.themeColor"
                )

        elif background_type == "image":
            if not is_valid_image_url(background_value):
                logger.warning(f"Background image URL is invalid: {background_value}")
                return {}
            page_background_fill["stretchedPictureFill"] = {
                "contentUrl": background_value
            }
            fields_mask_parts.append(
                "pageBackgroundFill.stretchedPictureFill.contentUrl"
            )
        else:
            return {}

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
