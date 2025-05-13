"""Slide request builder for Google Slides API requests."""

import logging
from typing import Any, Dict, List, Optional

from markdowndeck.models import ElementType, Slide, SlideLayout
from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder

logger = logging.getLogger(__name__)


class SlideRequestBuilder(BaseRequestBuilder):
    """Builder for slide-related Google Slides API requests."""

    # Standard placeholder types for common layouts
    LAYOUT_PLACEHOLDERS = {
        SlideLayout.TITLE: [
            {"type": "TITLE", "index": 0},
        ],
        SlideLayout.TITLE_AND_BODY: [
            {"type": "TITLE", "index": 0},
            {"type": "BODY", "index": 0},
        ],
        SlideLayout.TITLE_AND_TWO_COLUMNS: [
            {"type": "TITLE", "index": 0},
            {"type": "BODY", "index": 0},
            {"type": "BODY", "index": 1},
        ],
        SlideLayout.TITLE_ONLY: [
            {"type": "TITLE", "index": 0},
        ],
        SlideLayout.SECTION_HEADER: [
            {"type": "TITLE", "index": 0},
            {"type": "SUBTITLE", "index": 0},
        ],
        SlideLayout.CAPTION_ONLY: [
            {"type": "TITLE", "index": 0},
            {"type": "CENTERED_TITLE", "index": 0},
        ],
        SlideLayout.BIG_NUMBER: [
            {"type": "TITLE", "index": 0},
            {"type": "BIG_NUMBER", "index": 0},
            {"type": "BODY", "index": 0},
        ],
    }

    # Map our ElementType to standard placeholder types
    ELEMENT_TO_PLACEHOLDER = {
        ElementType.TITLE: "TITLE",
        ElementType.SUBTITLE: "SUBTITLE",
        ElementType.TEXT: "BODY",
        ElementType.BULLET_LIST: "BODY",
        ElementType.ORDERED_LIST: "BODY",
    }

    def create_slide_request(self, slide: Slide) -> dict:
        """
        Create a request to add a new slide with the specified layout.

        Args:
            slide: The slide to create

        Returns:
            Dictionary with the create slide request
        """
        # Generate a unique ID for the slide if not present
        if not slide.object_id:
            slide.object_id = self._generate_id("slide")

        # ENHANCEMENT: Map placeholders for this layout to specific IDs
        placeholder_mappings = []

        # Get standard placeholders for this layout if available
        standard_placeholders = self.LAYOUT_PLACEHOLDERS.get(slide.layout, [])

        # Generate placeholder IDs and add mappings
        slide.placeholder_mappings = {}

        for placeholder in standard_placeholders:
            placeholder_type = placeholder["type"]
            placeholder_index = placeholder["index"]
            placeholder_id = (
                f"{slide.object_id}_{placeholder_type.lower()}_{placeholder_index}"
            )

            # Add to slide's placeholder mapping for element builders to use
            element_type = self._get_element_type_for_placeholder(placeholder_type)
            if element_type:
                slide.placeholder_mappings[element_type] = placeholder_id

            # Create the placeholder ID mapping for the createSlide request
            placeholder_mappings.append(
                {
                    "layoutPlaceholder": {
                        "type": placeholder_type,
                        "index": placeholder_index,
                    },
                    "objectId": placeholder_id,
                }
            )

        # Create the slide request
        request = {
            "createSlide": {
                "objectId": slide.object_id,
                "slideLayoutReference": {"predefinedLayout": slide.layout.value},
                "placeholderIdMappings": placeholder_mappings,
            }
        }

        logger.debug(
            f"Created slide request with ID: {slide.object_id}, layout: {slide.layout.value}, "
            f"and {len(placeholder_mappings)} placeholder mappings"
        )
        return request

    def create_background_request(self, slide: Slide) -> dict:
        """
        Create a request to set the slide background.

        Args:
            slide: The slide to set background for

        Returns:
            Dictionary with the update slide background request
        """
        if not slide.background:
            return {}

        background_type = slide.background.get("type")
        background_value = slide.background.get("value")

        # FIXED: Use updatePageProperties instead of updateSlideProperties
        # and use correct field masks
        request = {
            "updatePageProperties": {
                "objectId": slide.object_id,
                "pageProperties": {"pageBackgroundFill": {}},
                "fields": "",  # Will be set based on type
            }
        }

        if background_type == "color":
            if background_value.startswith("#"):
                # Convert hex to RGB
                rgb = self._hex_to_rgb(background_value)
                request["updatePageProperties"]["pageProperties"][
                    "pageBackgroundFill"
                ] = {"solidFill": {"color": {"rgbColor": rgb}}}
                request["updatePageProperties"][
                    "fields"
                ] = "pageBackgroundFill.solidFill.color.rgbColor"
            else:
                # ENHANCEMENT: Check if this is a theme color
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

                if background_value.upper() in theme_colors:
                    # Use theme color reference
                    request["updatePageProperties"]["pageProperties"][
                        "pageBackgroundFill"
                    ] = {
                        "solidFill": {"color": {"themeColor": background_value.upper()}}
                    }
                    request["updatePageProperties"][
                        "fields"
                    ] = "pageBackgroundFill.solidFill.color.themeColor"
                else:
                    # Named colors (legacy support)
                    request["updatePageProperties"]["pageProperties"][
                        "pageBackgroundFill"
                    ] = {
                        "solidFill": {"color": {"themeColor": background_value.upper()}}
                    }
                    request["updatePageProperties"][
                        "fields"
                    ] = "pageBackgroundFill.solidFill.color.themeColor"
        elif background_type == "image":
            request["updatePageProperties"]["pageProperties"]["pageBackgroundFill"] = {
                "stretchedPictureFill": {"contentUrl": background_value}
            }
            request["updatePageProperties"][
                "fields"
            ] = "pageBackgroundFill.stretchedPictureFill.contentUrl"

        logger.debug(f"Created background request for slide: {slide.object_id}")
        return request

    def create_notes_request(self, slide: Slide) -> dict:
        """
        Create a request to add notes to a slide.

        Args:
            slide: The slide to add notes to

        Returns:
            Dictionary or list of dictionaries with the update speaker notes request
        """
        # Safety check - ensure slide notes and object_id are valid
        if not slide.notes or not slide.object_id:
            logger.warning(
                f"Skipping notes request for slide {slide.object_id} - notes are empty or slide ID is invalid"
            )
            return {}

        # FIXED: Use the correct approach for speaker notes
        # Get speakerNotesObjectId if available, otherwise use the standard format
        speaker_notes_id = getattr(slide, "speaker_notes_object_id", None)

        if speaker_notes_id:
            # If we have an explicit speaker notes ID, first clear existing notes then insert new ones
            delete_request = {
                "deleteText": {
                    "objectId": speaker_notes_id,
                    "textRange": {"type": "ALL"},
                }
            }

            insert_request = {
                "insertText": {
                    "objectId": speaker_notes_id,
                    "insertionIndex": 0,
                    "text": slide.notes,
                }
            }

            logger.debug(
                f"Created speaker notes requests with explicit ID: {speaker_notes_id}"
            )
            return [delete_request, insert_request]
        else:
            # Use standard format with speakerNotes path
            logger.debug(
                f"Created speaker notes request using standard path: {slide.object_id}/speakerNotes"
            )
            return {
                "insertText": {
                    "objectId": f"{slide.object_id}/speakerNotes",
                    "insertionIndex": 0,
                    "text": slide.notes,
                }
            }

    def _get_element_type_for_placeholder(
        self, placeholder_type: str
    ) -> Optional[ElementType]:
        """
        Get the corresponding ElementType for a placeholder type.

        Args:
            placeholder_type: Google Slides placeholder type

        Returns:
            Corresponding ElementType or None if no match
        """
        # Reverse lookup in ELEMENT_TO_PLACEHOLDER
        for element_type, ph_type in self.ELEMENT_TO_PLACEHOLDER.items():
            if ph_type == placeholder_type:
                return element_type
        return None
