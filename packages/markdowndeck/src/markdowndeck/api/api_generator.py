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

        # Process elements
        for element in slide.elements:
            element_requests = self._generate_element_requests(
                element, slide.object_id, slide.placeholder_mappings
            )
            requests.extend(element_requests)

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
            logger.warning(
                f"Slide {slide.object_id} has notes but no speaker_notes_object_id; notes will not be added."
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
            List of request dictionaries
        """
        # Ensure element has a valid object_id (unless it's using a theme placeholder)
        element_type = getattr(element, "element_type", None)
        use_theme_placeholder = theme_placeholders and element_type in theme_placeholders

        if not getattr(element, "object_id", None) and not use_theme_placeholder:
            element_type_name = getattr(element_type, "value", "unknown_element")
            element.object_id = self.slide_builder._generate_id(f"{element_type_name}_{slide_id}")
            logger.debug(f"Generated missing object_id for element: {element.object_id}")

        # Delegate to appropriate builder based on element type
        if (
            element_type == ElementType.TITLE
            or element_type == ElementType.SUBTITLE
            or element_type == ElementType.TEXT
        ):
            return self.text_builder.generate_text_element_requests(
                element, slide_id, theme_placeholders
            )

        if element_type == ElementType.BULLET_LIST:
            return self.list_builder.generate_bullet_list_element_requests(element, slide_id)

        if element_type == ElementType.ORDERED_LIST:
            return self.list_builder.generate_list_element_requests(
                element,
                slide_id,
                "NUMBERED_DIGIT_ALPHA_ROMAN",  # Example preset
            )

        if element_type == ElementType.IMAGE:
            return self.media_builder.generate_image_element_requests(element, slide_id)

        if element_type == ElementType.TABLE:
            return self.table_builder.generate_table_element_requests(element, slide_id)

        if element_type == ElementType.CODE:
            return self.code_builder.generate_code_element_requests(element, slide_id)

        if element_type == ElementType.QUOTE:
            # Quotes are handled by TextRequestBuilder with specific styling
            return self.text_builder.generate_text_element_requests(
                element, slide_id, theme_placeholders
            )

        if element_type == ElementType.FOOTER:
            # Footers are essentially text elements; special handling is in layout/parsing
            return self.text_builder.generate_text_element_requests(
                element, slide_id, theme_placeholders
            )

        logger.warning(
            f"Unknown or unhandled element type: {element_type} for element id {getattr(element, 'object_id', 'N/A')}"
        )
        return []
