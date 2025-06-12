import logging
from copy import deepcopy

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
        from markdowndeck.parser.content.element_factory import ElementFactory

        element_factory = ElementFactory()

        self.slide_builder = SlideRequestBuilder()
        self.text_builder = TextRequestBuilder()
        self.media_builder = MediaRequestBuilder()
        self.list_builder = ListRequestBuilder(element_factory)
        self.table_builder = TableRequestBuilder()
        self.code_builder = CodeRequestBuilder()

    def generate_batch_requests(self, deck: Deck, presentation_id: str) -> list[dict]:
        """Generate all batch requests needed to create a presentation."""
        batches = []
        for i, slide in enumerate(deck.slides):
            slide_batch = self.generate_slide_batch(slide, presentation_id)
            batches.append(slide_batch)
            logger.debug(f"Generated batch for slide {i + 1}/{len(deck.slides)}")
        logger.info(f"Generated {len(batches)} batch requests")
        return batches

    def generate_slide_batch(self, slide: Slide, presentation_id: str) -> dict:
        """
        Generate a batch of requests for a single slide.
        """
        requests = []
        slide_request = self.slide_builder.create_slide_request(slide)
        requests.append(slide_request)

        if slide.background:
            background_request = self.slide_builder.create_background_request(slide)
            if background_request:
                requests.append(background_request)

        for element in slide.renderable_elements:
            element_requests = self._generate_element_requests(element, slide)
            if element_requests:
                requests.extend(element_requests)

        if slide.notes and slide.speaker_notes_object_id:
            notes_requests = self.slide_builder.create_notes_request(slide)
            if isinstance(notes_requests, list):
                requests.extend(notes_requests)
            elif notes_requests:
                requests.append(notes_requests)
        elif slide.notes:
            logger.debug(
                f"Slide {slide.object_id} has notes but no speaker_notes_object_id yet. Notes will be added in a second pass."
            )

        logger.debug(f"Generated {len(requests)} requests for slide {slide.object_id}")
        return {"presentationId": presentation_id, "requests": requests}

    def _generate_element_requests(self, element: Element, slide: Slide) -> list[dict]:
        """
        Generate requests for a specific element by delegating to appropriate builder.
        """
        if element is None:
            logger.warning(f"Skipping None element for slide {slide.object_id}")
            return []

        element = deepcopy(element)

        # REFACTORED: Removed obsolete logic for merging slide.title_directives and subtitle_directives.
        # Directives are now self-contained within each element, making this logic unnecessary and non-compliant.
        # MAINTAINS: The principle of statelessness via deepcopy.
        # JUSTIFICATION: Aligns with the new architecture where directives are parsed directly onto elements.

        # ADDED: Handle continuation titles per API_GEN_SPEC.md Rule #3.
        if (
            slide.is_continuation
            and element.element_type == ElementType.TITLE
            and hasattr(element, "text")
        ):
            element.text = f"{element.text} (continued)"
            logger.debug(
                f"Appended continuation suffix to title for slide {slide.object_id}"
            )

        # ADDED: Safety check for zero-dimension elements per API_GEN_SPEC.md Rule #4.
        if (
            hasattr(element, "size")
            and element.size == (0, 0)
            and (
                element.directives.get("background") or element.directives.get("border")
            )
        ):
            logger.warning(
                f"Skipping createShape for element {element.object_id} on slide {slide.object_id} "
                "due to zero dimensions with visual directives. This prevents an API error."
            )
            return []

        if not getattr(element, "object_id", None):
            element_type_name = getattr(element.element_type, "value", "unknown")
            element.object_id = self.slide_builder._generate_id(
                f"{element_type_name}_{slide.object_id}"
            )

        element_type = getattr(element, "element_type", None)
        requests = []
        slide_id = slide.object_id

        try:
            if element_type in [
                ElementType.TITLE,
                ElementType.SUBTITLE,
                ElementType.TEXT,
                ElementType.QUOTE,
                ElementType.FOOTER,
            ]:
                builder_requests = self.text_builder.generate_text_element_requests(
                    element, slide_id
                )
            elif element_type == ElementType.BULLET_LIST:
                builder_requests = (
                    self.list_builder.generate_bullet_list_element_requests(
                        element, slide_id
                    )
                )
            elif element_type == ElementType.ORDERED_LIST:
                builder_requests = self.list_builder.generate_list_element_requests(
                    element, slide_id, "NUMBERED_DIGIT_ALPHA_ROMAN"
                )
            elif element_type == ElementType.IMAGE:
                builder_requests = self.media_builder.generate_image_element_requests(
                    element, slide_id
                )
            elif element_type == ElementType.TABLE:
                builder_requests = self.table_builder.generate_table_element_requests(
                    element, slide_id
                )
            elif element_type == ElementType.CODE:
                builder_requests = self.code_builder.generate_code_element_requests(
                    element, slide_id
                )
            else:
                logger.warning(
                    f"Unknown or unhandled element type: {element_type} for element id {getattr(element, 'object_id', 'N/A')}"
                )
                builder_requests = []

            if builder_requests:
                requests = builder_requests

        except Exception as e:
            logger.error(
                f"Error generating requests for element type {element_type}: {e}",
                exc_info=True,
            )

        return requests
