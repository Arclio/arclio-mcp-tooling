"""Slide request builder for Google Slides API requests."""

import logging

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
            page_background_fill["stretchedPictureFill"] = {
                "contentUrl": background_value
            }
            fields_mask_parts.append(
                "pageBackgroundFill.stretchedPictureFill.contentUrl"
            )
        else:
            logger.warning(
                f"Unknown background type: {background_type} for slide {slide.object_id}"
            )
            return {}

        if not page_background_fill:
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
        if not slide.notes:
            return []
        speaker_notes_shape_id = getattr(slide, "speaker_notes_object_id", None)
        if not speaker_notes_shape_id:
            logger.warning(
                f"Cannot create notes request for slide {slide.object_id}: "
                "speaker_notes_object_id is missing. Notes content will be ignored."
            )
            return []
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
