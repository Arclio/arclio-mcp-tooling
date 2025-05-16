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
        updated_presentation = self.get_presentation(
            presentation_id,
            fields="slides(objectId,slideProperties.notesPage.pageElements)",
        )
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
                        logger.debug(f"Created notes requests for slide {i + 1}")

        # Step 7: Execute the notes batches if any exist
        if notes_batches:
            logger.info(f"Adding speaker notes to {slides_with_notes} slides")
            for i, batch in enumerate(notes_batches):
                logger.debug(f"Executing notes batch {i + 1} of {len(notes_batches)}")
                self.execute_batch_update(batch)

        # Step 8: Get the final presentation
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

            return (
                self.slides_service.presentations()
                .get(presentationId=presentation_id, **kwargs)
                .execute()
            )
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

        # Additional validation for wildcard fields and other problematic patterns
        if "requests" in batch:
            for i, request in enumerate(batch["requests"]):
                # Check for wildcard field mask
                if "updateShapeProperties" in request:
                    fields = request["updateShapeProperties"].get("fields", "")
                    logger.debug(
                        f"Request {i} updateShapeProperties fields: '{fields}', "
                        f"properties: {request['updateShapeProperties'].get('shapeProperties', {})}"
                    )

                    # Check for wildcard field mask which will cause errors
                    if fields == "*":
                        logger.warning(
                            f"Replacing wildcard field mask '*' in request {i} with specific fields"
                        )
                        # Replace with common safe fields
                        request["updateShapeProperties"][
                            "fields"
                        ] = "shapeBackgroundFill,contentAlignment"

                    # Check for autofit property without proper fields
                    if "autofit" in request["updateShapeProperties"].get(
                        "shapeProperties", {}
                    ):
                        autofit_type = request["updateShapeProperties"][
                            "shapeProperties"
                        ]["autofit"].get("autofitType")
                        if autofit_type != "NONE":
                            logger.warning(
                                f"Invalid autofitType '{autofit_type}' found in request {i}. "
                                f"Only 'NONE' is supported. Changing to 'NONE'."
                            )
                            request["updateShapeProperties"]["shapeProperties"][
                                "autofit"
                            ]["autofitType"] = "NONE"

                        if fields != "autofit.autofitType":
                            logger.warning(
                                f"Fixing autofit field mask in request {i}, was: '{fields}'"
                            )
                            request["updateShapeProperties"][
                                "fields"
                            ] = "autofit.autofitType"

        logger.debug(
            f"Executing batch update with {len(batch.get('requests', []))} requests"
        )
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
                error_str = str(error)
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
                # Check specifically for text range index errors
                elif (
                    (
                        "endIndex" in error_str
                        and "greater than the existing text length" in error_str
                    )
                    or "Invalid requests" in error_str
                    and "updateParagraphStyle" in error_str
                ):
                    # Extract information from the error message
                    import re

                    # Try pattern 1: match our specific error case directly
                    request_index_match = re.search(
                        r"Invalid requests\[(\d+)\]\.(\w+): The end index \((\d+)\) should not be greater than the existing text length \((\d+)\)",
                        error_str,
                    )

                    if request_index_match:
                        # Direct match to the specific error format
                        problem_index = int(request_index_match.group(1))
                        request_type = request_index_match.group(2)
                        attempted_end_index = int(request_index_match.group(3))
                        actual_text_length = int(request_index_match.group(4))

                        logger.warning(
                            f"Text range error: request {problem_index} ({request_type}) tried to use end index {attempted_end_index} "
                            f"but text length is {actual_text_length}"
                        )
                    else:
                        # Try pattern 2: more general pattern
                        request_index_match = re.search(
                            r"requests\[(\d+)\]\.(\w+)", error_str
                        )
                        length_match = re.search(
                            r"end index \((\d+)\).*text length \((\d+)\)", error_str
                        )

                        if request_index_match:
                            problem_index = int(request_index_match.group(1))
                            request_type = request_index_match.group(2)

                            if length_match:
                                attempted_end_index = int(length_match.group(1))
                                actual_text_length = int(length_match.group(2))
                                logger.warning(
                                    f"Text range error: request {problem_index} ({request_type}) tried to use end index {attempted_end_index} "
                                    f"but text length is {actual_text_length}"
                                )
                            else:
                                # Just log the basic info if we can't extract details
                                logger.warning(
                                    f"Text range error in request {problem_index} ({request_type})"
                                )
                                attempted_end_index = 999999  # Placeholder value
                                actual_text_length = 0  # Placeholder value
                        else:
                            # We can't identify the specific request, but we'll try a blanket fix
                            logger.warning(
                                f"Unidentified text range error: {error_str}"
                            )
                            problem_index = (
                                -1
                            )  # Flag that we couldn't identify the problem index

                    # Create a new batch without the problematic request
                    modified_requests = []
                    for i, req in enumerate(current_batch["requests"]):
                        if problem_index >= 0 and i == problem_index:
                            logger.info(
                                f"Skipping request at index {problem_index} with invalid text range"
                            )
                        else:
                            # Also fix any updateParagraphStyle or updateTextStyle requests with text ranges
                            for req_type in [
                                "updateParagraphStyle",
                                "updateTextStyle",
                                "createParagraphBullets",
                            ]:
                                if req_type in req and "textRange" in req[req_type]:
                                    text_range = req[req_type]["textRange"]
                                    if (
                                        "endIndex" in text_range
                                        and "startIndex" in text_range
                                    ):
                                        # Ensure end_index is never greater than start_index + reasonable length
                                        start_index = text_range["startIndex"]
                                        old_end = text_range["endIndex"]

                                        # If we have actual text length info, use it to cap the end index
                                        if (
                                            problem_index >= 0
                                            and actual_text_length > 0
                                        ):
                                            # For any request that's after the one that failed, be extra cautious
                                            if i > problem_index:
                                                text_range["endIndex"] = min(
                                                    text_range["endIndex"],
                                                    actual_text_length - 1,
                                                )

                                        # Apply a general safety limit
                                        if text_range["endIndex"] > start_index + 500:
                                            text_range["endIndex"] = start_index + 500

                                        # Ensure endIndex is always at least startIndex + 1
                                        if (
                                            text_range["endIndex"]
                                            <= text_range["startIndex"]
                                        ):
                                            text_range["endIndex"] = (
                                                text_range["startIndex"] + 1
                                            )

                                        if old_end != text_range["endIndex"]:
                                            logger.warning(
                                                f"Fixed text range in request {i}: endIndex {old_end} -> {text_range['endIndex']}"
                                            )

                            # Add the fixed request
                            modified_requests.append(req)

                    # Update the batch with the modified requests
                    current_batch = {
                        "presentationId": current_batch["presentationId"],
                        "requests": modified_requests,
                    }
                    logger.info(
                        f"Retrying with modified batch ({len(modified_requests)} requests)"
                    )
                    retries += 1
                    continue
                elif "createImage" in error_str and (
                    "not found" in error_str or "too large" in error_str
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
