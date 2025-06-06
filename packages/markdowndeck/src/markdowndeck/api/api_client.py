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

        # Step 5: Get the updated presentation to retrieve speaker notes IDs
        updated_presentation = self.get_presentation(
            presentation_id,
            fields="slides(objectId,slideProperties.notesPage.pageElements)",
        )
        # Step 6: Create a second batch of requests for speaker notes
        notes_batches = []
        slides_with_notes = 0

        # Process each slide that has notes
        for i, slide in enumerate(deck.slides):
            if slide.notes and i < len(updated_presentation.get("slides", [])):
                # Get the actual slide from the API response
                actual_slide = updated_presentation["slides"][i]

                # Extract the speaker notes ID from the slide
                speaker_notes_id = self._find_speaker_notes_id(actual_slide)

                if speaker_notes_id:
                    # Update the slide model with the speaker notes ID
                    slide.speaker_notes_object_id = speaker_notes_id

                    # Create notes requests
                    notes_batch = {
                        "presentationId": presentation_id,
                        "requests": [
                            # Insert the notes text (will replace any existing text)
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
                    logger.debug(f"Created notes requests for slide {i + 1}")

        # Step 7: Execute the notes batches if any exist
        if notes_batches:
            logger.info(f"Adding speaker notes to {slides_with_notes} slides")
            for i, batch in enumerate(notes_batches):
                logger.debug(f"Executing notes batch {i + 1} of {len(notes_batches)}")
                self.execute_batch_update(batch)

        # Step 8: Get the final presentation
        final_presentation = self.get_presentation(presentation_id, fields="presentationId,title,slides.objectId")
        result = {
            "presentationId": presentation_id,
            "presentationUrl": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            "title": final_presentation.get("title", deck.title),
            "slideCount": len(final_presentation.get("slides", [])),
        }

        logger.info(f"Presentation creation complete. Slide count: {result['slideCount']}")
        return result

    def _find_speaker_notes_id(self, slide: dict) -> str | None:
        """
        Find the speaker notes shape ID in a slide.

        Args:
            slide: The slide data from the API

        Returns:
            Speaker notes shape ID or None if not found
        """
        try:
            # Check if the slide has a notesPage
            if "slideProperties" in slide and "notesPage" in slide["slideProperties"]:
                notes_page = slide["slideProperties"]["notesPage"]

                # Look for the speaker notes text box in the notes page elements
                if "pageElements" in notes_page:
                    for element in notes_page["pageElements"]:
                        # Speaker notes are typically in a shape with type TEXT_BOX
                        if element.get("shape", {}).get("shapeType") == "TEXT_BOX":
                            return element.get("objectId")

            # If we can't find it using the above methods, try looking for a specific
            # element that matches the pattern of speaker notes
            if "pageElements" in slide:
                for element in slide["pageElements"]:
                    # Speaker notes sometimes have a specific naming pattern
                    element_id = element.get("objectId", "")
                    if "speakerNotes" in element_id or "notes" in element_id:
                        return element_id

            logger.warning(f"Could not find speaker notes ID for slide {slide.get('objectId')}")
            return None

        except Exception as e:
            logger.warning(f"Error finding speaker notes object ID: {e}")
            return None

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

    def get_presentation(self, presentation_id: str, fields: str = None) -> dict:
        """
        Get a presentation by ID.

        Args:
            presentation_id: The presentation ID
            fields: Optional field mask string to limit response size

        Returns:
            Dictionary with presentation data

        Raises:
            HttpError: If API call fails
        """
        try:
            logger.debug(f"Getting presentation: {presentation_id}")

            # Use fields parameter if provided to limit response size
            kwargs = {}
            if fields:
                kwargs["fields"] = fields
                logger.debug(f"Using field mask: {fields}")

            return self.slides_service.presentations().get(presentationId=presentation_id, **kwargs).execute()
        except HttpError as error:
            logger.error(f"Failed to get presentation: {error}")
            raise

    def execute_batch_update(self, batch: dict) -> dict:
        """
        Execute a batch update request.
        Includes retry logic and error handling for common errors.

        Args:
            batch: The batch update request

        Returns:
            The response from the API

        Raises:
            googleapiclient.errors.HttpError: If API calls fail after retries
        """
        # Validate and fix the batch
        batch = validate_batch_requests(batch)

        logger.debug(f"Executing batch update with {len(batch.get('requests', []))} requests")
        retries = 0
        current_batch = batch

        while retries <= self.max_retries:
            try:
                response = (
                    self.slides_service.presentations()
                    .batchUpdate(
                        presentationId=current_batch["presentationId"],
                        body={"requests": current_batch["requests"]},
                    )
                    .execute()
                )
                logger.debug("Batch update successful")
                return response
            except HttpError as error:
                # Retry only on transient server errors or rate limiting
                if error.resp.status in [429, 500, 503]:
                    retries += 1
                    if retries <= self.max_retries:
                        wait_time = self.retry_delay * (2 ** (retries - 1))
                        logger.warning(
                            f"Rate limit or server error hit (Status: {error.resp.status}). Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                        continue  # Continue to the next iteration of the while loop
                    logger.error(f"Max retries exceeded for transient error: {error}")
                    raise  # Re-raise the exception after max retries
                # For all other API errors, log the details and fail immediately.
                # This indicates a bug in request generation that must be fixed.
                import json

                try:
                    # Pretty-print the failing batch for easier debugging
                    failing_batch_str = json.dumps(current_batch, indent=2)
                    logger.error(f"Unrecoverable API error. Failing batch data:\n{failing_batch_str}")
                except TypeError:
                    logger.error(f"Unrecoverable API error. Failing batch data (raw):\n{current_batch}")

                logger.error(f"Batch update failed permanently with status {error.resp.status}: {error}")
                raise  # Re-raise the exception to halt execution

        return {}  # Should never reach here but satisfies type checker

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

            # Collect all delete requests into a single batch
            delete_requests = []
            for slide in default_slides:
                slide_id = slide.get("objectId")
                if slide_id:
                    delete_requests.append({"deleteObject": {"objectId": slide_id}})
                    logger.debug(f"Prepared delete request for slide: {slide_id}")

            # Send all delete requests in a single batch update
            if delete_requests:
                try:
                    self.slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": delete_requests},
                    ).execute()
                    logger.debug(f"Successfully deleted {len(delete_requests)} default slides in single batch")
                except HttpError as error:
                    logger.warning(f"Failed to delete default slides: {error}")

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

            # Note: Google Slides API doesn't directly provide a list of available themes
            # This is a stub that returns a limited set of common themes

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
