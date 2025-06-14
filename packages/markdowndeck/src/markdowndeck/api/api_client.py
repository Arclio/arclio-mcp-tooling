"""API client for Google Slides API."""

import logging
import random
import time
from collections.abc import Callable
from typing import Any

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
        # PRESERVED: The retry logic is preserved but its parameters are enhanced for production readiness.
        # ENHANCED: Increased retries and delay to make the client more resilient.
        self.max_retries = 5
        self.retry_delay = 5  # seconds
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

    def _execute_request_with_retry(self, request_func: Callable[[], Any]) -> Any:
        """
        Executes a Google API request with a retry mechanism for transient errors.

        # REFACTORED: This is a new private method to centralize retry logic.
        # MAINTAINS: The exponential backoff strategy from the original `execute_batch_update`.
        # JUSTIFICATION: Prevents code duplication and ensures all critical API calls
        # are resilient to transient errors like 503 Service Unavailable and 429 Rate Limit Exceeded.

        Args:
            request_func: A callable (e.g., a lambda) that executes the Google API request.

        Returns:
            The result of the API request execution.

        Raises:
            HttpError: If the request fails after all retries or for a non-retryable reason.
        """
        retries = 0
        while True:
            try:
                return request_func()
            except HttpError as error:
                # Retry on 429 (Rate Limit), 500 (Internal Error), 503 (Service Unavailable)
                if error.resp.status in [429, 500, 503] and retries < self.max_retries:
                    retries += 1
                    # ENHANCED: Added jitter to the exponential backoff to prevent synchronized retries.
                    wait_time = self.retry_delay * (2 ** (retries - 1))
                    jitter = random.uniform(0, 1)  # Add up to 1 second of random jitter
                    total_wait = wait_time + jitter
                    # ENHANCED: Improved logging to include the error reason.
                    error_reason = getattr(error, "_get_reason", lambda: "Unknown")()
                    logger.warning(
                        f'API request failed with status {error.resp.status}: "{error_reason}". '
                        f"Retrying in {total_wait:.2f}s... (Attempt {retries}/{self.max_retries})"
                    )
                    time.sleep(total_wait)
                else:
                    logger.error(
                        f"Unrecoverable API request failed: {error}", exc_info=True
                    )
                    raise

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

        presentation = self.create_presentation(deck.title)
        presentation_id = presentation["presentationId"]
        logger.info(f"Created presentation with ID: {presentation_id}")

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

        updated_presentation = self.get_presentation(
            presentation_id,
            fields="slides(objectId,slideProperties.notesPage.pageElements)",
        )
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
            for _i, batch in enumerate(notes_batches):
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
        body = {"title": title}
        logger.debug("Creating presentation without theme")

        def request_func():
            return self.slides_service.presentations().create(body=body).execute()

        presentation = self._execute_request_with_retry(request_func)

        logger.info(f"Created presentation with ID: {presentation['presentationId']}")
        return presentation

    def get_presentation(self, presentation_id: str, fields: str = None) -> dict:
        """Get a presentation by ID."""
        try:
            kwargs = {}
            if fields:
                kwargs["fields"] = fields

            def request_func():
                return (
                    self.slides_service.presentations()
                    .get(presentationId=presentation_id, **kwargs)
                    .execute()
                )

            return self._execute_request_with_retry(request_func)

        except HttpError as error:
            logger.error(f"Failed to get presentation: {error}")
            raise

    def execute_batch_update(self, batch: dict) -> dict:
        """
        Execute a batch update request with retry logic.
        """
        batch = validate_batch_requests(batch)

        def request_func():
            return (
                self.slides_service.presentations()
                .batchUpdate(
                    presentationId=batch["presentationId"],
                    body={"requests": batch["requests"]},
                )
                .execute()
            )

        return self._execute_request_with_retry(request_func)

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
