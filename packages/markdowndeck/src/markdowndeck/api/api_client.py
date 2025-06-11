"""API client for Google Slides API."""

import logging
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.api.validation import validate_batch_requests
from markdowndeck.models import Deck

logger = logging.getLogger(__name__)


class ApiClient:
    """
    Handles communication with the Google Slides API.
    """

    def __init__(
        self,
        credentials: Credentials | None = None,
        service: Resource | None = None,
    ):
        """
        Initialize with either credentials or an existing service.

        Args:
            credentials: Google OAuth credentials
            service: Existing Google API service

        Raises:
            ValueError: If neither credentials nor service is provided
        """
        self.credentials = credentials
        self.service = service
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.batch_size = 50  # Maximum number of requests per batch

        if service:
            self.slides_service = service
            logger.debug("Using provided Google API service")
        elif credentials:
            self.slides_service = build("slides", "v1", credentials=credentials)
            logger.debug("Created Google Slides API service from credentials")
        else:
            raise ValueError("Either credentials or service must be provided")

        self.request_generator = ApiRequestGenerator()
        logger.info("ApiClient initialized successfully")

    def create_presentation_from_deck(self, deck: Deck) -> dict:
        """
        Create a presentation from a deck model.

        Args:
            deck: The presentation deck

        Returns:
            Dictionary with presentation details
        """
        logger.info(
            f"Creating presentation: '{deck.title}' with {len(deck.slides)} slides"
        )

        # REFACTORED: Removed theme_id. create_presentation now creates a blank presentation.
        # JUSTIFICATION: Aligns with PRINCIPLES.md (Sec 6) and API_GEN_SPEC.md (Rule #5).
        presentation = self.create_presentation(deck.title)
        presentation_id = presentation["presentationId"]
        logger.info(f"Created presentation with ID: {presentation_id}")

        # REFACTORED: Removed call to _delete_default_slides. This is a theme-related
        # concept that is now obsolete under the "Blank Canvas First" principle.
        # MAINTAINS: The core pipeline flow of creating the presentation then adding content.

        # Generate and execute batched requests to create content
        batches = self.request_generator.generate_batch_requests(deck, presentation_id)
        logger.info(f"Generated {len(batches)} batch requests")

        for i, batch in enumerate(batches):
            logger.debug(f"Executing batch {i + 1} of {len(batches)}")
            if len(batch["requests"]) > self.batch_size:
                sub_batches = self._split_batch(batch)
                for _j, sub_batch in enumerate(sub_batches):
                    self.execute_batch_update(sub_batch)
            else:
                self.execute_batch_update(batch)

        # Get updated presentation to retrieve speaker notes IDs
        updated_presentation = self.get_presentation(
            presentation_id,
            fields="slides(objectId,slideProperties.notesPage.pageElements)",
        )
        # Create a second batch of requests for speaker notes
        notes_batches = []
        slides_with_notes = 0

        for i, slide in enumerate(deck.slides):
            if slide.notes and i < len(updated_presentation.get("slides", [])):
                actual_slide = updated_presentation["slides"][i]
                speaker_notes_id = self._find_speaker_notes_id(actual_slide)
                if speaker_notes_id:
                    slide.speaker_notes_object_id = speaker_notes_id
                    notes_batch = {
                        "presentationId": presentation_id,
                        "requests": [
                            {
                                "insertText": {
                                    "objectId": speaker_notes_id,
                                    "insertionIndex": 0,
                                    "text": slide.notes,
                                }
                            }
                        ],
                    }
                    notes_batches.append(notes_batch)
                    slides_with_notes += 1

        if notes_batches:
            logger.info(f"Adding speaker notes to {slides_with_notes} slides")
            for i, batch in enumerate(notes_batches):
                self.execute_batch_update(batch)

        final_presentation = self.get_presentation(
            presentation_id, fields="presentationId,title,slides.objectId"
        )
        result = {
            "presentationId": presentation_id,
            "presentationUrl": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            "title": final_presentation.get("title", deck.title),
            "slideCount": len(final_presentation.get("slides", [])),
        }

        logger.info(
            f"Presentation creation complete. Slide count: {result['slideCount']}"
        )
        return result

    def _find_speaker_notes_id(self, slide: dict) -> str | None:
        """Find the speaker notes shape ID in a slide."""
        try:
            if "slideProperties" in slide and "notesPage" in slide["slideProperties"]:
                notes_page = slide["slideProperties"]["notesPage"]
                if "pageElements" in notes_page:
                    for element in notes_page["pageElements"]:
                        if element.get("shape", {}).get("shapeType") == "TEXT_BOX":
                            return element.get("objectId")
            logger.warning(
                f"Could not find speaker notes ID for slide {slide.get('objectId')}"
            )
            return None
        except Exception as e:
            logger.warning(f"Error finding speaker notes object ID: {e}")
            return None

    def create_presentation(self, title: str) -> dict:
        """
        Create a new, blank Google Slides presentation.

        Args:
            title: Presentation title

        Returns:
            Dictionary with presentation data

        Raises:
            HttpError: If API call fails
        """
        # REFACTORED: Removed all theme-related logic.
        # MAINTAINS: Core functionality of creating a presentation.
        # JUSTIFICATION: Aligns with "Blank Canvas First" principle.
        try:
            body = {"title": title}
            logger.debug("Creating presentation without theme")
            presentation = (
                self.slides_service.presentations().create(body=body).execute()
            )
            logger.info(
                f"Created presentation with ID: {presentation['presentationId']}"
            )
            return presentation
        except HttpError as error:
            logger.error(f"Failed to create presentation: {error}")
            raise

    def get_presentation(self, presentation_id: str, fields: str = None) -> dict:
        """Get a presentation by ID."""
        try:
            kwargs = {}
            if fields:
                kwargs["fields"] = fields
            return (
                self.slides_service.presentations()
                .get(presentationId=presentation_id, **kwargs)
                .execute()
            )
        except HttpError as error:
            logger.error(f"Failed to get presentation: {error}")
            raise

    def execute_batch_update(self, batch: dict) -> dict:
        """Execute a batch update request with retry logic."""
        batch = validate_batch_requests(batch)
        retries = 0
        while retries <= self.max_retries:
            try:
                return (
                    self.slides_service.presentations()
                    .batchUpdate(
                        presentationId=batch["presentationId"],
                        body={"requests": batch["requests"]},
                    )
                    .execute()
                )
            except HttpError as error:
                if error.resp.status in [429, 500, 503]:
                    retries += 1
                    if retries <= self.max_retries:
                        wait_time = self.retry_delay * (2 ** (retries - 1))
                        logger.warning(
                            f"Rate limit or server error. Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                logger.error(
                    f"Unrecoverable batch update failed: {error}", exc_info=True
                )
                raise
        return {}

    def _split_batch(self, batch: dict) -> list[dict]:
        """Split a large batch into smaller batches."""
        requests = batch["requests"]
        presentation_id = batch["presentationId"]
        num_batches = (len(requests) + self.batch_size - 1) // self.batch_size
        sub_batches = []
        for i in range(num_batches):
            start_idx = i * self.batch_size
            end_idx = min((i + 1) * self.batch_size, len(requests))
            sub_batches.append(
                {
                    "presentationId": presentation_id,
                    "requests": requests[start_idx:end_idx],
                }
            )
        return sub_batches
