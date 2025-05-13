"""Generator for Google Slides API requests."""

import logging
from typing import Any, Dict, List, Optional

from markdowndeck.models import (
    Deck,
    Element,
    ElementType,
    Slide,
)
from markdowndeck.api.request_builders import (
    SlideRequestBuilder,
    TextRequestBuilder,
    MediaRequestBuilder,
    ListRequestBuilder,
    TableRequestBuilder,
    CodeRequestBuilder,
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
            logger.debug(f"Generated batch for slide {i+1}/{len(deck.slides)}")

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
            element_requests = self._generate_element_requests(element, slide.object_id)
            requests.extend(element_requests)

        # Add speaker notes if present
        if slide.notes:
            notes_requests = self.slide_builder.create_notes_request(slide)
            # Handle both single request and list of requests
            if isinstance(notes_requests, list):
                requests.extend(notes_requests)
            elif notes_requests:
                requests.append(notes_requests)

        logger.debug(f"Generated {len(requests)} requests for slide {slide.object_id}")
        return {"presentationId": presentation_id, "requests": requests}

    def _generate_element_requests(self, element: Element, slide_id: str) -> list[dict]:
        """
        Generate requests for a specific element by delegating to appropriate builder.

        Args:
            element: The element to generate requests for
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        # Ensure element has a valid object_id
        if not getattr(element, "object_id", None):
            element_type_name = getattr(element, "element_type", "unknown").value
            element.object_id = self.slide_builder._generate_id(
                f"{element_type_name}_{slide_id}"
            )
            logger.debug(
                f"Generated missing object_id for element: {element.object_id}"
            )

        # Delegate to appropriate builder based on element type
        element_type = getattr(element, "element_type", None)

        if element_type == ElementType.TITLE or element_type == ElementType.SUBTITLE:
            return self.text_builder.generate_text_element_requests(element, slide_id)

        elif element_type == ElementType.TEXT:
            return self.text_builder.generate_text_element_requests(element, slide_id)

        elif element_type == ElementType.BULLET_LIST:
            return self.list_builder.generate_bullet_list_element_requests(
                element, slide_id
            )

        elif element_type == ElementType.ORDERED_LIST:
            return self.list_builder.generate_list_element_requests(
                element, slide_id, "NUMBERED_DIGIT_ALPHA_ROMAN"
            )

        elif element_type == ElementType.IMAGE:
            return self.media_builder.generate_image_element_requests(element, slide_id)

        elif element_type == ElementType.TABLE:
            return self.table_builder.generate_table_element_requests(element, slide_id)

        elif element_type == ElementType.CODE:
            return self.code_builder.generate_code_element_requests(element, slide_id)

        elif element_type == ElementType.QUOTE:
            return self.text_builder.generate_quote_element_requests(element, slide_id)

        elif element_type == ElementType.FOOTER:
            return self.text_builder.generate_footer_element_requests(element, slide_id)

        logger.warning(f"Unknown element type: {element_type}")
        return []
