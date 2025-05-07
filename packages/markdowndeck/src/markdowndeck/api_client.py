"""
API client for MarkdownDeck.

This module handles communication with the Google Slides API for creating presentations
from markdown content. It manages authentication, API requests, and error handling.
"""

import logging
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from .api_generator import ApiRequestGenerator
from .models import Deck

logger = logging.getLogger(__name__)


class ApiClient:
    """
    Handles communication with the Google Slides API.

    This class is used internally by markdowndeck.create_presentation() and should
    not be used directly by external code. For integration with other packages,
    use the ApiRequestGenerator instead.
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
        logger.info(f"Creating presentation: '{deck.title}' with {len(deck.slides)} slides")

        # Step 1: Create the presentation
        presentation = self.create_presentation(deck.title, deck.theme_id)
        presentation_id = presentation["presentationId"]
        logger.info(f"Created presentation with ID: {presentation_id}")

        # Step 2: Delete the default slide if it exists
        self._delete_default_slides(presentation_id, presentation)
        logger.debug("Deleted default slides")

        # Step 3: Generate and execute batched requests to create content
        batches = self.request_generator.generate_batch_requests(deck, presentation_id)
        logger.info(f"Generated {len(batches)} batch requests")

        # Step 4: Execute each batch
        for i, batch in enumerate(batches):
            logger.debug(f"Executing batch {i + 1} of {len(batches)}")

            # Check batch size and split if needed
            if len(batch["requests"]) > self.batch_size:
                sub_batches = self._split_batch(batch)
                logger.debug(f"Split large batch into {len(sub_batches)} sub-batches")

                for j, sub_batch in enumerate(sub_batches):
                    logger.debug(f"Executing sub-batch {j + 1} of {len(sub_batches)}")
                    self.execute_batch_update(sub_batch)
            else:
                self.execute_batch_update(batch)

        # Step 5: Get the updated presentation
        updated_presentation = self.get_presentation(presentation_id)

        result = {
            "presentationId": presentation_id,
            "presentationUrl": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            "title": updated_presentation.get("title", deck.title),
            "slideCount": len(updated_presentation.get("slides", [])),
        }

        logger.info(f"Presentation creation complete. Slide count: {result['slideCount']}")
        return result

    def create_presentation(self, title: str, theme_id: str | None = None) -> dict:
        """
        Create a new Google Slides presentation.

        Args:
            title: Presentation title
            theme_id: Optional theme ID to apply to the presentation

        Returns:
            Dictionary with presentation data

        Raises:
            HttpError: If API call fails
        """
        try:
            body = {"title": title}

            # Include theme ID if provided
            if theme_id:
                logger.debug(f"Creating presentation with theme ID: {theme_id}")
                presentation = self.slides_service.presentations().create(body=body).execute()

                # Apply theme in a separate request
                self.slides_service.presentations().batchUpdate(
                    presentationId=presentation["presentationId"],
                    body={
                        "requests": [
                            {
                                "applyTheme": {
                                    "themeId": theme_id,
                                }
                            }
                        ]
                    },
                ).execute()
            else:
                logger.debug("Creating presentation without theme")
                presentation = self.slides_service.presentations().create(body=body).execute()

            logger.info(f"Created presentation with ID: {presentation['presentationId']}")
            return presentation
        except HttpError as error:
            logger.error(f"Failed to create presentation: {error}")
            raise

    def get_presentation(self, presentation_id: str) -> dict:
        """
        Get a presentation by ID.

        Args:
            presentation_id: The presentation ID

        Returns:
            Dictionary with presentation data

        Raises:
            HttpError: If API call fails
        """
        try:
            logger.debug(f"Getting presentation: {presentation_id}")
            return self.slides_service.presentations().get(presentationId=presentation_id).execute()
        except HttpError as error:
            logger.error(f"Failed to get presentation: {error}")
            raise

    def execute_batch_update(self, batch: dict) -> dict:
        """
        Execute a batch update with retries.

        Args:
            batch: Dictionary with presentationId and requests

        Returns:
            Dictionary with batch update response

        Raises:
            HttpError: If API call fails after max retries
        """
        retries = 0
        request_count = len(batch["requests"])
        logger.debug(f"Executing batch update with {request_count} requests")

        while retries <= self.max_retries:
            try:
                response = (
                    self.slides_service.presentations()
                    .batchUpdate(
                        presentationId=batch["presentationId"],
                        body={"requests": batch["requests"]},
                    )
                    .execute()
                )
                logger.debug("Batch update successful")
                return response
            except HttpError as error:
                if error.resp.status in [429, 500, 503]:  # Rate limit or server error
                    retries += 1
                    if retries <= self.max_retries:
                        wait_time = self.retry_delay * (2 ** (retries - 1))  # Exponential backoff
                        logger.warning(
                            f"Rate limit or server error hit. Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries exceeded: {error}")
                        raise
                else:
                    logger.error(f"Batch update failed: {error}")
                    raise
        return None

    def _delete_default_slides(self, presentation_id: str, presentation: dict) -> None:
        """
        Delete the default slides that are created with a new presentation.

        Args:
            presentation_id: The presentation ID
            presentation: Presentation data dictionary
        """
        logger.debug("Checking for default slides to delete")
        default_slides = presentation.get("slides", [])
        if default_slides:
            logger.debug(f"Found {len(default_slides)} default slides to delete")
            for slide in default_slides:
                slide_id = slide.get("objectId")
                if slide_id:
                    try:
                        self.slides_service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={"requests": [{"deleteObject": {"objectId": slide_id}}]},
                        ).execute()
                        logger.debug(f"Deleted default slide: {slide_id}")
                    except HttpError as error:
                        logger.warning(f"Failed to delete default slide: {error}")

    def _split_batch(self, batch: dict) -> list[dict]:
        """
        Split a large batch into smaller batches.

        Args:
            batch: Original batch dictionary

        Returns:
            List of smaller batch dictionaries
        """
        requests = batch["requests"]
        presentation_id = batch["presentationId"]

        # Calculate number of sub-batches needed
        num_batches = (len(requests) + self.batch_size - 1) // self.batch_size
        sub_batches = []

        for i in range(num_batches):
            start_idx = i * self.batch_size
            end_idx = min((i + 1) * self.batch_size, len(requests))

            sub_batch = {
                "presentationId": presentation_id,
                "requests": requests[start_idx:end_idx],
            }

            sub_batches.append(sub_batch)

        return sub_batches

    def get_available_themes(self) -> list[dict]:
        """
        Get a list of available presentation themes.

        Returns:
            List of theme dictionaries with id and name

        Raises:
            HttpError: If API call fails
        """
        try:
            logger.debug("Fetching available presentation themes")
            (self.slides_service.presentations().get(presentationId="p").execute())

            # Themes are not directly accessible via the API
            # This is a stub for future implementation if Google adds this capability
            logger.warning("Theme listing not fully supported by Google Slides API")

            # Return a list of basic themes as a fallback
            return [
                {"id": "THEME_1", "name": "Simple Light"},
                {"id": "THEME_2", "name": "Simple Dark"},
                {"id": "THEME_3", "name": "Material Light"},
                {"id": "THEME_4", "name": "Material Dark"},
            ]
        except HttpError as error:
            logger.error(f"Failed to get themes: {error}")
            raise
