"""API client for Google Slides API."""

import logging
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from markdowndeck.api.api_generator import ApiRequestGenerator
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
        logger.info(
            f"Creating presentation: '{deck.title}' with {len(deck.slides)} slides"
        )

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
        updated_presentation = self.get_presentation(presentation_id)

        # Step 6: Create a second batch of requests for speaker notes
        notes_batches = []
        slides_with_notes = 0

        # Process each slide that has notes
        for i, slide in enumerate(deck.slides):
            if slide.notes:
                if i < len(updated_presentation.get("slides", [])):
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
                        logger.debug(f"Created notes requests for slide {i+1}")

        # Step 7: Execute the notes batches if any exist
        if notes_batches:
            logger.info(f"Adding speaker notes to {slides_with_notes} slides")
            for i, batch in enumerate(notes_batches):
                logger.debug(f"Executing notes batch {i + 1} of {len(notes_batches)}")
                self.execute_batch_update(batch)

        # Step 8: Get the final presentation
        final_presentation = self.get_presentation(presentation_id)

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

            # Alternative lookup: directly in notesProperties if available
            if (
                "slideProperties" in slide
                and "notesProperties" in slide["slideProperties"]
            ):
                notes_props = slide["slideProperties"]["notesProperties"]
                if "speakerNotesObjectId" in notes_props:
                    return notes_props["speakerNotesObjectId"]

            # If we can't find it using the above methods, try looking for a specific
            # element that matches the pattern of speaker notes
            if "pageElements" in slide:
                for element in slide["pageElements"]:
                    # Speaker notes sometimes have a specific naming pattern
                    element_id = element.get("objectId", "")
                    if "speakerNotes" in element_id or "notes" in element_id:
                        return element_id

            logger.warning(
                f"Could not find speaker notes ID for slide {slide.get('objectId')}"
            )
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
                presentation = (
                    self.slides_service.presentations().create(body=body).execute()
                )

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
            return (
                self.slides_service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )
        except HttpError as error:
            logger.error(f"Failed to get presentation: {error}")
            raise

    def execute_batch_update(self, batch: dict) -> dict:
        """
        Execute a batch update with retries and error handling for images.

        This implementation specifically handles image-related errors by:
        1. Attempting the full batch
        2. On failure, identifying problematic image requests
        3. Either removing or replacing them with placeholder text
        4. Retrying the modified batch

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
        current_batch = batch.copy()

        # REMOVED TEMPORARY FIX FOR table_cell_properties
        # The fix is now in table_builder.py for the FieldMask

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
                if error.resp.status in [429, 500, 503]:  # Rate limit or server error
                    retries += 1
                    if retries <= self.max_retries:
                        wait_time = self.retry_delay * (
                            2 ** (retries - 1)
                        )  # Exponential backoff
                        logger.warning(
                            f"Rate limit or server error hit. Retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Max retries exceeded: {error}")
                        raise
                elif "createImage" in str(error) and (
                    "not found" in str(error) or "too large" in str(error)
                ):
                    # Handle image-specific errors
                    logger.warning(f"Image error in batch: {error}")

                    # Extract the problematic request index
                    error_msg = str(error)
                    try:
                        # Parse index from error message like "Invalid requests[4].createImage"
                        import re

                        index_match = re.search(
                            r"requests\[(\d+)\]\.createImage", error_msg
                        )
                        if index_match:
                            problem_index = int(index_match.group(1))

                            # Create a new batch without the problematic request
                            modified_requests = []
                            for i, req in enumerate(current_batch["requests"]):
                                if i == problem_index and "createImage" in req:
                                    # Skip the problematic image or replace with text placeholder
                                    if "objectId" in req["createImage"]:
                                        # Get information from the original request
                                        obj_id = req["createImage"]["objectId"]
                                        page_id = req["createImage"][
                                            "elementProperties"
                                        ]["pageObjectId"]
                                        position = (
                                            req["createImage"]["elementProperties"][
                                                "transform"
                                            ]["translateX"],
                                            req["createImage"]["elementProperties"][
                                                "transform"
                                            ]["translateY"],
                                        )
                                        size = (
                                            req["createImage"]["elementProperties"][
                                                "size"
                                            ]["width"]["magnitude"],
                                            req["createImage"]["elementProperties"][
                                                "size"
                                            ]["height"]["magnitude"],
                                        )

                                        # Create placeholder text box instead
                                        modified_requests.append(
                                            {
                                                "createShape": {
                                                    "objectId": obj_id,
                                                    "shapeType": "TEXT_BOX",
                                                    "elementProperties": {
                                                        "pageObjectId": page_id,
                                                        "size": {
                                                            "width": {
                                                                "magnitude": size[0],
                                                                "unit": "PT",
                                                            },
                                                            "height": {
                                                                "magnitude": size[1],
                                                                "unit": "PT",
                                                            },
                                                        },
                                                        "transform": {
                                                            "scaleX": 1,
                                                            "scaleY": 1,
                                                            "translateX": position[0],
                                                            "translateY": position[1],
                                                            "unit": "PT",
                                                        },
                                                    },
                                                }
                                            }
                                        )

                                        # Add text to say image couldn't be loaded
                                        modified_requests.append(
                                            {
                                                "insertText": {
                                                    "objectId": obj_id,
                                                    "insertionIndex": 0,
                                                    "text": "[Image not available]",
                                                }
                                            }
                                        )

                                        logger.info(
                                            f"Replaced problematic image request at index {problem_index} with text placeholder"
                                        )
                                    else:
                                        logger.info(
                                            f"Skipped problematic image request at index {problem_index}"
                                        )
                                else:
                                    modified_requests.append(req)

                            # Update the batch with the modified requests
                            current_batch = {
                                "presentationId": current_batch["presentationId"],
                                "requests": modified_requests,
                            }
                            logger.info(
                                f"Retrying with modified batch ({len(modified_requests)} requests)"
                            )
                            continue
                    except Exception as parse_error:
                        logger.error(f"Failed to parse error message: {parse_error}")

                # Handle deleteText with invalid indices
                elif (
                    "deleteText" in str(error)
                    and "startIndex" in str(error)
                    and "endIndex" in str(error)
                ):
                    logger.warning(f"DeleteText error in batch: {error}")

                    # Extract the problematic request index
                    error_msg = str(error)
                    try:
                        # Parse index from error message like "Invalid requests[4].deleteText"
                        import re

                        index_match = re.search(
                            r"requests\[(\d+)\]\.deleteText", error_msg
                        )
                        if index_match:
                            problem_index = int(index_match.group(1))

                            # Create a new batch without the problematic request
                            modified_requests = []
                            for i, req in enumerate(current_batch["requests"]):
                                if i == problem_index and "deleteText" in req:
                                    # Skip the problematic deleteText request
                                    logger.info(
                                        f"Skipped problematic deleteText request at index {problem_index}"
                                    )
                                else:
                                    modified_requests.append(req)

                            # Update the batch with the modified requests
                            current_batch = {
                                "presentationId": current_batch["presentationId"],
                                "requests": modified_requests,
                            }
                            logger.info(
                                f"Retrying with modified batch ({len(modified_requests)} requests)"
                            )
                            continue
                    except Exception as parse_error:
                        logger.error(f"Failed to parse error message: {parse_error}")

                # For other errors, fail the batch
                # log the data that was sent
                logger.error(f"Batch data that failed: {current_batch}")
                logger.error(f"Batch update failed: {error}")
                raise

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
            for slide in default_slides:
                slide_id = slide.get("objectId")
                if slide_id:
                    try:
                        self.slides_service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={
                                "requests": [{"deleteObject": {"objectId": slide_id}}]
                            },
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
