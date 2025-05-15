"""Generator for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders import (
    CodeRequestBuilder,
    ListRequestBuilder,
    MediaRequestBuilder,
    SlideRequestBuilder,
    TableRequestBuilder,
    TextRequestBuilder,
)
from markdowndeck.models import (
    Deck,
    Element,
    ElementType,
    Slide,
)

logger = logging.getLogger(__name__)


class ApiRequestGenerator:
    """Generates Google Slides API requests from the Intermediate Representation."""

    def __init__(self):
        """Initialize the request generator with all builders."""
        logger.debug("Initializing API request generator")
        self.slide_builder = SlideRequestBuilder()
        self.text_builder = TextRequestBuilder()
        self.media_builder = MediaRequestBuilder()
        self.list_builder = ListRequestBuilder()
        self.table_builder = TableRequestBuilder()
        self.code_builder = CodeRequestBuilder()

    def generate_batch_requests(self, deck: Deck, presentation_id: str) -> list[dict]:
        """
        Generate all batch requests needed to create a presentation.

        Args:
            deck: The presentation deck
            presentation_id: The presentation ID

        Returns:
            List of batch request dictionaries
        """
        batches = []

        for i, slide in enumerate(deck.slides):
            # Generate a batch for each slide
            slide_batch = self.generate_slide_batch(slide, presentation_id)
            batches.append(slide_batch)
            logger.debug(f"Generated batch for slide {i + 1}/{len(deck.slides)}")

        logger.info(f"Generated {len(batches)} batch requests")
        return batches

    def generate_slide_batch(self, slide: Slide, presentation_id: str) -> dict:
        """
        Generate a batch of requests for a single slide.

        Args:
            slide: The slide to generate requests for
            presentation_id: The presentation ID

        Returns:
            Dictionary with presentationId and requests
        """
        requests = []

        # Create the slide
        slide_request = self.slide_builder.create_slide_request(slide)
        requests.append(slide_request)

        # Set slide background if present
        if slide.background:
            background_request = self.slide_builder.create_background_request(slide)
            requests.append(background_request)

        # Process elements with awareness of related elements
        i = 0
        while i < len(slide.elements):
            current_element = slide.elements[i]

            # Check if this is a subheading element that precedes a list
            is_subheading_for_list = False
            subheading_data = None
            next_element = None

            if (
                i < len(slide.elements) - 1
                and hasattr(current_element, "element_type")
                and current_element.element_type == ElementType.TEXT
                and hasattr(current_element, "related_to_next")
                and current_element.related_to_next
            ):
                next_element = slide.elements[i + 1]

                # Check if next element is a list type
                if (
                    hasattr(next_element, "element_type")
                    and next_element.element_type
                    in (ElementType.BULLET_LIST, ElementType.ORDERED_LIST)
                    and hasattr(next_element, "related_to_prev")
                    and next_element.related_to_prev
                ):
                    # Check if the list will use a placeholder
                    will_use_placeholder = False
                    placeholder_id = None

                    if slide.placeholder_mappings:
                        # Determine the appropriate placeholder for this list
                        # Based on position (left half = BODY_0, right half = BODY_1)
                        if next_element.element_type in slide.placeholder_mappings:
                            will_use_placeholder = True
                            placeholder_id = slide.placeholder_mappings[
                                next_element.element_type
                            ]
                        # Also check for generic BODY placeholders
                        elif ElementType.TEXT in slide.placeholder_mappings:
                            will_use_placeholder = True
                            placeholder_id = slide.placeholder_mappings[
                                ElementType.TEXT
                            ]
                        # For multi-column layouts, choose the correct BODY placeholder
                        # based on the horizontal position
                        elif (
                            hasattr(next_element, "position") and next_element.position
                        ):
                            slide_midpoint = (
                                slide.size[0] / 2 if hasattr(slide, "size") else 360
                            )
                            is_left_column = next_element.position[0] < slide_midpoint

                            # Try column-specific placeholders
                            column_key = (
                                f"{ElementType.TEXT.value}_0"
                                if is_left_column
                                else f"{ElementType.TEXT.value}_1"
                            )
                            if column_key in slide.placeholder_mappings:
                                will_use_placeholder = True
                                placeholder_id = slide.placeholder_mappings[column_key]

                    if will_use_placeholder:
                        is_subheading_for_list = True
                        # Prepare subheading data to pass to the list builder
                        subheading_data = {
                            "text": current_element.text,
                            "formatting": getattr(current_element, "formatting", []),
                            "element_type": current_element.element_type,
                            "horizontal_alignment": getattr(
                                current_element, "horizontal_alignment", None
                            ),
                            "placeholder_id": placeholder_id,
                        }

                        logger.debug(
                            f"Combining subheading with list in placeholder: "
                            f"{getattr(current_element, 'object_id', 'unknown')} + "
                            f"{getattr(next_element, 'object_id', 'unknown')}"
                        )

            if is_subheading_for_list and next_element:
                # Skip this element (subheading) as it will be combined with the list
                i += 1

                # Now process the list element with the subheading data
                element_requests = []  # Initialize with empty list

                if next_element.element_type == ElementType.BULLET_LIST:
                    list_requests = (
                        self.list_builder.generate_bullet_list_element_requests(
                            next_element,
                            slide.object_id,
                            slide.placeholder_mappings,
                            subheading_data,
                        )
                    )
                    if list_requests is not None:  # Defensive check
                        element_requests = list_requests
                else:  # ORDERED_LIST
                    list_requests = self.list_builder.generate_list_element_requests(
                        next_element,
                        slide.object_id,
                        "NUMBERED_DIGIT_ALPHA_ROMAN",
                        slide.placeholder_mappings,
                        subheading_data,
                    )
                    if list_requests is not None:  # Defensive check
                        element_requests = list_requests

                # Ensure we're not extending with None
                if element_requests:
                    requests.extend(element_requests)
            else:
                # Process element normally
                element_requests = self._generate_element_requests(
                    current_element, slide.object_id, slide.placeholder_mappings
                )

                # Ensure we're not extending with None
                if element_requests is not None:
                    requests.extend(element_requests)

            i += 1

        # Add speaker notes if present
        # Note: speaker_notes_object_id must be populated on the slide model
        # by the ApiClient after the slide is created and its ID is known.
        if slide.notes and slide.speaker_notes_object_id:
            notes_requests = self.slide_builder.create_notes_request(slide)
            # Handle both single request and list of requests
            if isinstance(notes_requests, list):
                requests.extend(notes_requests)
            elif notes_requests:  # Ensure it's not an empty dict
                requests.append(notes_requests)
        elif slide.notes and not slide.speaker_notes_object_id:
            # This is expected for newly created slides - the notes shape ID
            # isn't assigned until after the slide is created. Notes will be
            # added in a separate operation after initial slide creation.
            logger.debug(
                f"Slide {slide.object_id} has notes but no speaker_notes_object_id yet. "
                "Notes will be added in a second pass."
            )

        logger.debug(f"Generated {len(requests)} requests for slide {slide.object_id}")
        return {"presentationId": presentation_id, "requests": requests}

    def _generate_element_requests(
        self, element: Element, slide_id: str, theme_placeholders: dict[str, str] = None
    ) -> list[dict]:
        """
        Generate requests for a specific element by delegating to appropriate builder.

        Args:
            element: The element to generate requests for
            slide_id: The slide ID
            theme_placeholders: Placeholder mappings for the current slide

        Returns:
            List of request dictionaries (empty list if no requests can be generated)
        """
        # Skip None elements
        if element is None:
            logger.warning(f"Skipping None element for slide {slide_id}")
            return []  # Return empty list, not None

        # Ensure element has a valid object_id (unless it's using a theme placeholder)
        element_type = getattr(element, "element_type", None)
        use_theme_placeholder = (
            theme_placeholders and element_type in theme_placeholders
        )

        if not getattr(element, "object_id", None) and not use_theme_placeholder:
            element_type_name = getattr(element_type, "value", "unknown_element")
            element.object_id = self.slide_builder._generate_id(
                f"{element_type_name}_{slide_id}"
            )
            logger.debug(
                f"Generated missing object_id for element: {element.object_id}"
            )

        # Delegate to appropriate builder based on element type
        requests = []  # Initialize with empty list

        try:
            if (
                element_type == ElementType.TITLE
                or element_type == ElementType.SUBTITLE
                or element_type == ElementType.TEXT
            ):
                builder_requests = self.text_builder.generate_text_element_requests(
                    element, slide_id, theme_placeholders
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.BULLET_LIST:
                builder_requests = (
                    self.list_builder.generate_bullet_list_element_requests(
                        element, slide_id, theme_placeholders
                    )
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.ORDERED_LIST:
                builder_requests = self.list_builder.generate_list_element_requests(
                    element, slide_id, "NUMBERED_DIGIT_ALPHA_ROMAN", theme_placeholders
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.IMAGE:
                builder_requests = self.media_builder.generate_image_element_requests(
                    element, slide_id
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.TABLE:
                builder_requests = self.table_builder.generate_table_element_requests(
                    element, slide_id
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.CODE:
                builder_requests = self.code_builder.generate_code_element_requests(
                    element, slide_id
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.QUOTE:
                # Quotes are handled by TextRequestBuilder with specific styling
                builder_requests = self.text_builder.generate_text_element_requests(
                    element, slide_id, theme_placeholders
                )
                if builder_requests is not None:
                    requests = builder_requests

            elif element_type == ElementType.FOOTER:
                # Footers are essentially text elements; special handling is in layout/parsing
                builder_requests = self.text_builder.generate_text_element_requests(
                    element, slide_id, theme_placeholders
                )
                if builder_requests is not None:
                    requests = builder_requests

            else:
                logger.warning(
                    f"Unknown or unhandled element type: {element_type} for element id {getattr(element, 'object_id', 'N/A')}"
                )
        except Exception as e:
            logger.error(
                f"Error generating requests for element type {element_type}: {e}",
                exc_info=True,
            )

        return requests  # Always return the list, even if empty
