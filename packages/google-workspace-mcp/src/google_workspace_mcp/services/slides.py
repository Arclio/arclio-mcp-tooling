"""
Google Slides service implementation.
"""

import json
import logging
import re
from typing import Any

from markdowndeck import create_presentation

from google_workspace_mcp.auth import gauth
from google_workspace_mcp.services.base import BaseGoogleService
from google_workspace_mcp.services.drive import DriveService
from google_workspace_mcp.utils.markdown_slides import MarkdownSlidesConverter
from google_workspace_mcp.utils.unit_conversion import convert_template_zones

logger = logging.getLogger(__name__)


class SlidesService(BaseGoogleService):
    """
    Service for interacting with Google Slides API.
    """

    def __init__(self):
        """Initialize the Slides service."""
        super().__init__("slides", "v1")
        self.markdown_converter = MarkdownSlidesConverter()

    def get_presentation(self, presentation_id: str) -> dict[str, Any]:
        """
        Get a presentation by ID with its metadata and content.

        Args:
            presentation_id: The ID of the presentation to retrieve

        Returns:
            Presentation data dictionary or error information
        """
        try:
            return (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )
        except Exception as e:
            return self.handle_api_error("get_presentation", e)

    def create_presentation(
        self,
        title: str,
        parent_folder_id: str | None = None,
        shared_drive_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new presentation with a title, optionally in a specific folder.

        Args:
            title: The title of the new presentation
            parent_folder_id: Optional parent folder ID to create the presentation within
            shared_drive_id: Optional shared drive ID to create the presentation in a shared drive

        Returns:
            Created presentation data or error information
        """
        try:
            # First create the presentation (Google Slides API doesn't support folder creation directly)
            body = {"title": title}
            presentation = self.service.presentations().create(body=body).execute()

            # Initialize folder move status
            folder_move_status = None

            # If folder parameters are specified, move the presentation using Drive API
            if parent_folder_id or shared_drive_id:
                from .drive import DriveService

                drive_service = DriveService()
                presentation_id = presentation["presentationId"]

                logger.info(
                    f"Attempting to move presentation {presentation_id} to folder. parent_folder_id: {parent_folder_id}, shared_drive_id: {shared_drive_id}"
                )

                # Move the presentation to the specified folder
                move_result = drive_service._move_file_to_folder(
                    file_id=presentation_id,
                    parent_folder_id=parent_folder_id,
                    shared_drive_id=shared_drive_id,
                )

                if move_result.get("error"):
                    # If move fails, log warning but don't fail the presentation creation
                    logger.warning(
                        f"Failed to move presentation to folder: {move_result.get('message')}"
                    )
                    folder_move_status = {
                        "success": False,
                        "error": move_result.get(
                            "message", "Unknown error occurred during folder move"
                        ),
                    }
                else:
                    logger.info(
                        f"Successfully moved presentation {presentation_id} to folder"
                    )
                    folder_move_status = {
                        "success": True,
                        "moved_to_folder_id": parent_folder_id or shared_drive_id,
                    }

            # Add folder move status to presentation result
            if folder_move_status:
                presentation["folder_move_status"] = folder_move_status

            return presentation
        except Exception as e:
            return self.handle_api_error("create_presentation", e)

    def create_slide(
        self, presentation_id: str, layout: str = "TITLE_AND_BODY"
    ) -> dict[str, Any]:
        """
        Add a new slide to an existing presentation.

        Args:
            presentation_id: The ID of the presentation
            layout: The layout type for the new slide
                (e.g., 'TITLE_AND_BODY', 'TITLE_ONLY', 'BLANK')

        Returns:
            Response data or error information
        """
        try:
            # Define the slide creation request
            requests = [
                {
                    "createSlide": {
                        "slideLayoutReference": {"predefinedLayout": layout},
                        "placeholderIdMappings": [],
                    }
                }
            ]

            logger.info(
                f"Sending API request to create slide: {json.dumps(requests[0], indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"API response: {json.dumps(response, indent=2)}")

            # Return information about the created slide
            if "replies" in response and len(response["replies"]) > 0:
                slide_id = response["replies"][0]["createSlide"]["objectId"]
                return {
                    "presentationId": presentation_id,
                    "slideId": slide_id,
                    "layout": layout,
                }
            return response
        except Exception as e:
            return self.handle_api_error("create_slide", e)

    def add_text(
        self,
        presentation_id: str,
        slide_id: str,
        text: str,
        shape_type: str = "TEXT_BOX",
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] = (400, 100),
    ) -> dict[str, Any]:
        """
        Add text to a slide by creating a text box.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            text: The text content to add
            shape_type: The type of shape for the text (default is TEXT_BOX)
            position: Tuple of (x, y) coordinates for position
            size: Tuple of (width, height) for the text box

        Returns:
            Response data or error information
        """
        try:
            # Create a unique element ID
            element_id = f"text_{slide_id}_{hash(text) % 10000}"

            # Define the text insertion requests
            requests = [
                # First create the shape
                {
                    "createShape": {
                        "objectId": element_id,  # Important: Include the objectId here
                        "shapeType": shape_type,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size[0], "unit": "PT"},
                                "height": {"magnitude": size[1], "unit": "PT"},
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
                },
                # Then insert text into the shape
                {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": text,
                    }
                },
            ]

            logger.info(
                f"Sending API request to create shape: {json.dumps(requests[0], indent=2)}"
            )
            logger.info(
                f"Sending API request to insert text: {json.dumps(requests[1], indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"API response: {json.dumps(response, indent=2)}")

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "elementId": element_id,
                "operation": "add_text",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("add_text", e)

    def add_formatted_text(
        self,
        presentation_id: str,
        slide_id: str,
        formatted_text: str,
        shape_type: str = "TEXT_BOX",
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] = (400, 100),
    ) -> dict[str, Any]:
        """
        Add rich-formatted text to a slide with styling.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            formatted_text: Text with formatting markers (**, *, etc.)
            shape_type: The type of shape for the text (default is TEXT_BOX)
            position: Tuple of (x, y) coordinates for position
            size: Tuple of (width, height) for the text box

        Returns:
            Response data or error information
        """
        try:
            logger.info(
                f"Adding formatted text to slide {slide_id}, position={position}, size={size}"
            )
            logger.info(f"Text content: '{formatted_text[:100]}...'")
            logger.info(
                f"Checking for formatting: bold={'**' in formatted_text}, italic={'*' in formatted_text}, code={'`' in formatted_text}"
            )

            # Create a unique element ID
            element_id = f"text_{slide_id}_{hash(formatted_text) % 10000}"

            # First create the text box
            create_requests = [
                # Create the shape
                {
                    "createShape": {
                        "objectId": element_id,  # FIX: Include the objectId
                        "shapeType": shape_type,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size[0], "unit": "PT"},
                                "height": {"magnitude": size[1], "unit": "PT"},
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
            ]

            # Log the shape creation request
            logger.info(
                f"Sending API request to create shape: {json.dumps(create_requests[0], indent=2)}"
            )

            # Execute creation request
            creation_response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": create_requests}
                )
                .execute()
            )

            # Log the response
            logger.info(
                f"API response for shape creation: {json.dumps(creation_response, indent=2)}"
            )

            # Process the formatted text
            # First, remove formatting markers to get plain text
            plain_text = formatted_text
            # Remove bold markers
            plain_text = re.sub(r"\*\*(.*?)\*\*", r"\1", plain_text)
            # Remove italic markers
            plain_text = re.sub(r"\*(.*?)\*", r"\1", plain_text)
            # Remove code markers if present
            plain_text = re.sub(r"`(.*?)`", r"\1", plain_text)

            # Insert the plain text
            text_request = [
                {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": plain_text,
                    }
                }
            ]

            # Log the text insertion request
            logger.info(
                f"Sending API request to insert plain text: {json.dumps(text_request[0], indent=2)}"
            )

            # Execute text insertion
            text_response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": text_request},
                )
                .execute()
            )

            # Log the response
            logger.info(
                f"API response for plain text insertion: {json.dumps(text_response, indent=2)}"
            )

            # Now generate style requests if there's formatting to apply
            if "**" in formatted_text or "*" in formatted_text:
                style_requests = []

                # Process bold text
                bold_pattern = r"\*\*(.*?)\*\*"
                bold_matches = list(re.finditer(bold_pattern, formatted_text))

                for match in bold_matches:
                    content = match.group(1)

                    # Find where this content appears in the plain text
                    start_pos = plain_text.find(content)
                    if start_pos >= 0:  # Found the text
                        end_pos = start_pos + len(content)

                        # Create style request for bold
                        style_requests.append(
                            {
                                "updateTextStyle": {
                                    "objectId": element_id,
                                    "textRange": {
                                        "startIndex": start_pos,
                                        "endIndex": end_pos,
                                    },
                                    "style": {"bold": True},
                                    "fields": "bold",
                                }
                            }
                        )

                # Process italic text (making sure not to process text inside bold markers)
                italic_pattern = r"\*(.*?)\*"
                italic_matches = list(re.finditer(italic_pattern, formatted_text))

                for match in italic_matches:
                    # Skip if this is part of a bold marker
                    is_part_of_bold = False
                    match_start = match.start()
                    match_end = match.end()

                    for bold_match in bold_matches:
                        bold_start = bold_match.start()
                        bold_end = bold_match.end()
                        if bold_start <= match_start and match_end <= bold_end:
                            is_part_of_bold = True
                            break

                    if not is_part_of_bold:
                        content = match.group(1)

                        # Find where this content appears in the plain text
                        start_pos = plain_text.find(content)
                        if start_pos >= 0:  # Found the text
                            end_pos = start_pos + len(content)

                            # Create style request for italic
                            style_requests.append(
                                {
                                    "updateTextStyle": {
                                        "objectId": element_id,
                                        "textRange": {
                                            "startIndex": start_pos,
                                            "endIndex": end_pos,
                                        },
                                        "style": {"italic": True},
                                        "fields": "italic",
                                    }
                                }
                            )

                # Apply all style requests if we have any
                if style_requests:
                    try:
                        # Log the style requests
                        logger.info(
                            f"Sending API request to apply text styling with {len(style_requests)} style requests"
                        )
                        for i, req in enumerate(style_requests):
                            logger.info(
                                f"Style request {i + 1}: {json.dumps(req, indent=2)}"
                            )

                        # Execute style requests
                        style_response = (
                            self.service.presentations()
                            .batchUpdate(
                                presentationId=presentation_id,
                                body={"requests": style_requests},
                            )
                            .execute()
                        )

                        # Log the response
                        logger.info(
                            f"API response for text styling: {json.dumps(style_response, indent=2)}"
                        )
                    except Exception as style_error:
                        logger.warning(
                            f"Failed to apply text styles: {str(style_error)}"
                        )
                        logger.exception("Style application error details")

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "elementId": element_id,
                "operation": "add_formatted_text",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("add_formatted_text", e)

    def add_bulleted_list(
        self,
        presentation_id: str,
        slide_id: str,
        items: list[str],
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] = (400, 200),
    ) -> dict[str, Any]:
        """
        Add a bulleted list to a slide.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            items: List of bullet point text items
            position: Tuple of (x, y) coordinates for position
            size: Tuple of (width, height) for the text box

        Returns:
            Response data or error information
        """
        try:
            # Create a unique element ID
            element_id = f"list_{slide_id}_{hash(str(items)) % 10000}"

            # Prepare the text content with newlines
            text_content = "\n".join(items)

            # Log the request
            log_data = {
                "createShape": {
                    "objectId": element_id,  # Include objectId here
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": size[0]},
                            "height": {"magnitude": size[1]},
                        },
                        "transform": {
                            "translateX": position[0],
                            "translateY": position[1],
                        },
                    },
                }
            }
            logger.info(
                f"Sending API request to create shape for bullet list: {json.dumps(log_data, indent=2)}"
            )

            # Create requests
            requests = [
                # First create the shape
                {
                    "createShape": {
                        "objectId": element_id,  # Include objectId here
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size[0], "unit": "PT"},
                                "height": {"magnitude": size[1], "unit": "PT"},
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
                },
                # Insert the text content
                {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": text_content,
                    }
                },
            ]

            # Log the text insertion
            logger.info(
                f"Sending API request to insert bullet text: {json.dumps(requests[1], indent=2)}"
            )

            # Execute the request to create shape and insert text
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            # Log the response
            logger.info(
                f"API response for bullet list creation: {json.dumps(response, indent=2)}"
            )

            # Now add bullet formatting
            try:
                # Use a simpler approach - apply bullets to the whole shape
                bullet_request = [
                    {
                        "createParagraphBullets": {
                            "objectId": element_id,
                            "textRange": {
                                "type": "ALL"
                            },  # Apply to all text in the shape
                            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                        }
                    }
                ]

                # Log the bullet formatting request
                logger.info(
                    f"Sending API request to apply bullet formatting: {json.dumps(bullet_request[0], indent=2)}"
                )

                bullet_response = (
                    self.service.presentations()
                    .batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": bullet_request},
                    )
                    .execute()
                )

                # Log the response
                logger.info(
                    f"API response for bullet formatting: {json.dumps(bullet_response, indent=2)}"
                )
            except Exception as bullet_error:
                logger.warning(
                    f"Failed to apply bullet formatting: {str(bullet_error)}"
                )
                # No fallback here - the text is already added, just without bullets

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "elementId": element_id,
                "operation": "add_bulleted_list",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("add_bulleted_list", e)

    def create_presentation_from_markdown(
        self, title: str, markdown_content: str
    ) -> dict[str, Any]:
        """
        Create a Google Slides presentation from Markdown content using markdowndeck.

        Args:
            title: Title of the presentation
            markdown_content: Markdown content to convert to slides

        Returns:
            Created presentation data
        """
        try:
            logger.info(f"Creating presentation from markdown: '{title}'")

            # Get credentials
            credentials = gauth.get_credentials()

            # Use markdowndeck to create the presentation
            result = create_presentation(
                markdown=markdown_content, title=title, credentials=credentials
            )

            logger.info(
                f"Successfully created presentation with ID: {result.get('presentationId')}"
            )

            # The presentation data is already in the expected format from markdowndeck
            return result

        except Exception as e:
            logger.exception(f"Error creating presentation from markdown: {str(e)}")
            return self.handle_api_error("create_presentation_from_markdown", e)

    def get_slides(self, presentation_id: str) -> list[dict[str, Any]]:
        """
        Get all slides from a presentation.

        Args:
            presentation_id: The ID of the presentation

        Returns:
            List of slide data dictionaries or error information
        """
        try:
            # Get the presentation with slide details
            presentation = (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )

            # Extract slide information
            slides = []
            for slide in presentation.get("slides", []):
                slide_id = slide.get("objectId", "")

                # Extract page elements
                elements = []
                for element in slide.get("pageElements", []):
                    element_type = None
                    element_content = None

                    # Determine element type and content
                    if "shape" in element and "text" in element["shape"]:
                        element_type = "text"
                        if "textElements" in element["shape"]["text"]:
                            # Extract text content
                            text_parts = []
                            for text_element in element["shape"]["text"][
                                "textElements"
                            ]:
                                if "textRun" in text_element:
                                    text_parts.append(
                                        text_element["textRun"].get("content", "")
                                    )
                            element_content = "".join(text_parts)
                    elif "image" in element:
                        element_type = "image"
                        if "contentUrl" in element["image"]:
                            element_content = element["image"]["contentUrl"]
                    elif "table" in element:
                        element_type = "table"
                        element_content = f"Table with {element['table'].get('rows', 0)} rows, {element['table'].get('columns', 0)} columns"

                    # Add to elements if we found content
                    if element_type and element_content:
                        elements.append(
                            {
                                "id": element.get("objectId", ""),
                                "type": element_type,
                                "content": element_content,
                            }
                        )

                # Get speaker notes if present
                notes = ""
                if (
                    "slideProperties" in slide
                    and "notesPage" in slide["slideProperties"]
                ):
                    notes_page = slide["slideProperties"]["notesPage"]
                    if "pageElements" in notes_page:
                        for element in notes_page["pageElements"]:
                            if (
                                "shape" in element
                                and "text" in element["shape"]
                                and "textElements" in element["shape"]["text"]
                            ):
                                note_parts = []
                                for text_element in element["shape"]["text"][
                                    "textElements"
                                ]:
                                    if "textRun" in text_element:
                                        note_parts.append(
                                            text_element["textRun"].get("content", "")
                                        )
                                if note_parts:
                                    notes = "".join(note_parts)

                # Add slide info to results
                slides.append(
                    {
                        "id": slide_id,
                        "elements": elements,
                        "notes": notes if notes else None,
                    }
                )

            return slides
        except Exception as e:
            return self.handle_api_error("get_slides", e)

    def delete_slide(self, presentation_id: str, slide_id: str) -> dict[str, Any]:
        """
        Delete a slide from a presentation.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide to delete

        Returns:
            Response data or error information
        """
        try:
            # Define the delete request
            requests = [{"deleteObject": {"objectId": slide_id}}]

            logger.info(
                f"Sending API request to delete slide: {json.dumps(requests[0], indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(
                f"API response for slide deletion: {json.dumps(response, indent=2)}"
            )

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "operation": "delete_slide",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("delete_slide", e)

    def add_image(
        self,
        presentation_id: str,
        slide_id: str,
        image_url: str,
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """
        Add an image to a slide from a URL.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            image_url: The URL of the image to add
            position: Tuple of (x, y) coordinates for position
            size: Optional tuple of (width, height) for the image

        Returns:
            Response data or error information
        """
        try:
            # Create a unique element ID (FIX: Actually assign the variable!)
            image_id = f"image_{slide_id}_{hash(image_url) % 10000}"

            # Define the base request
            create_image_request = {
                "createImage": {
                    "objectId": image_id,  # FIX: Add the missing objectId
                    "url": image_url,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": position[0],
                            "translateY": position[1],
                            "unit": "PT",  # Could use "EMU" to match docs
                        },
                    },
                }
            }

            # Add size if specified
            if size:
                create_image_request["createImage"]["elementProperties"]["size"] = {
                    "width": {"magnitude": size[0], "unit": "PT"},
                    "height": {"magnitude": size[1], "unit": "PT"},
                }

            logger.info(
                f"Sending API request to create image: {json.dumps(create_image_request, indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [create_image_request]},
                )
                .execute()
            )

            # Extract the image ID from the response
            if "replies" in response and len(response["replies"]) > 0:
                image_id = response["replies"][0].get("createImage", {}).get("objectId")
                logger.info(
                    f"API response for image creation: {json.dumps(response, indent=2)}"
                )
                return {
                    "presentationId": presentation_id,
                    "slideId": slide_id,
                    "imageId": image_id,
                    "operation": "add_image",
                    "result": "success",
                }

            return response
        except Exception as e:
            return self.handle_api_error("add_image", e)

    def add_image_with_unit(
        self,
        presentation_id: str,
        slide_id: str,
        image_url: str,
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] | None = None,
        unit: str = "PT",
    ) -> dict[str, Any]:
        """
        Add an image to a slide from a URL with support for different units.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            image_url: The URL of the image to add
            position: Tuple of (x, y) coordinates for position
            size: Optional tuple of (width, height) for the image
            unit: Unit type - "PT" for points or "EMU" for English Metric Units

        Returns:
            Response data or error information
        """
        try:
            # Create a unique element ID
            image_id = f"image_{slide_id}_{hash(image_url) % 10000}"

            # Define the base request
            create_image_request = {
                "createImage": {
                    "objectId": image_id,
                    "url": image_url,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": position[0],
                            "translateY": position[1],
                            "unit": unit,  # Use the specified unit
                        },
                    },
                }
            }

            # Add size if specified
            if size:
                create_image_request["createImage"]["elementProperties"]["size"] = {
                    "width": {"magnitude": size[0], "unit": unit},
                    "height": {"magnitude": size[1], "unit": unit},
                }

            logger.info(
                f"Sending API request to create image with {unit} units: {json.dumps(create_image_request, indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [create_image_request]},
                )
                .execute()
            )

            # Extract the image ID from the response
            if "replies" in response and len(response["replies"]) > 0:
                image_id = response["replies"][0].get("createImage", {}).get("objectId")
                logger.info(
                    f"API response for image creation: {json.dumps(response, indent=2)}"
                )
                return {
                    "presentationId": presentation_id,
                    "slideId": slide_id,
                    "imageId": image_id,
                    "operation": "add_image_with_unit",
                    "result": "success",
                }

            return response
        except Exception as e:
            return self.handle_api_error("add_image_with_unit", e)

    def add_table(
        self,
        presentation_id: str,
        slide_id: str,
        rows: int,
        columns: int,
        data: list[list[str]],
        position: tuple[float, float] = (100, 100),
        size: tuple[float, float] = (400, 200),
    ) -> dict[str, Any]:
        """
        Add a table to a slide.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            rows: Number of rows in the table
            columns: Number of columns in the table
            data: 2D array of strings containing table data
            position: Tuple of (x, y) coordinates for position
            size: Tuple of (width, height) for the table

        Returns:
            Response data or error information
        """
        try:
            # Create a unique table ID
            table_id = f"table_{slide_id}_{hash(str(data)) % 10000}"

            # Create table request
            create_table_request = {
                "createTable": {
                    "objectId": table_id,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": size[0], "unit": "PT"},
                            "height": {"magnitude": size[1], "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": position[0],
                            "translateY": position[1],
                            "unit": "PT",
                        },
                    },
                    "rows": rows,
                    "columns": columns,
                }
            }

            logger.info(
                f"Sending API request to create table: {json.dumps(create_table_request, indent=2)}"
            )

            # Execute table creation
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [create_table_request]},
                )
                .execute()
            )

            logger.info(
                f"API response for table creation: {json.dumps(response, indent=2)}"
            )

            # Populate the table if data is provided
            if data:
                text_requests = []

                for r, row in enumerate(data):
                    for c, cell_text in enumerate(row):
                        if cell_text and r < rows and c < columns:
                            # Insert text into cell
                            text_requests.append(
                                {
                                    "insertText": {
                                        "objectId": table_id,
                                        "cellLocation": {
                                            "rowIndex": r,
                                            "columnIndex": c,
                                        },
                                        "text": cell_text,
                                        "insertionIndex": 0,
                                    }
                                }
                            )

                if text_requests:
                    logger.info(
                        f"Sending API request to populate table with {len(text_requests)} cell entries"
                    )
                    table_text_response = (
                        self.service.presentations()
                        .batchUpdate(
                            presentationId=presentation_id,
                            body={"requests": text_requests},
                        )
                        .execute()
                    )
                    logger.info(
                        f"API response for table population: {json.dumps(table_text_response, indent=2)}"
                    )

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "tableId": table_id,
                "operation": "add_table",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("add_table", e)

    def add_slide_notes(
        self,
        presentation_id: str,
        slide_id: str,
        notes_text: str,
    ) -> dict[str, Any]:
        """
        Add presenter notes to a slide.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            notes_text: The text content for presenter notes

        Returns:
            Response data or error information
        """
        try:
            # Create the update speaker notes request
            requests = [
                {
                    "updateSpeakerNotesProperties": {
                        "objectId": slide_id,
                        "speakerNotesProperties": {"speakerNotesText": notes_text},
                        "fields": "speakerNotesText",
                    }
                }
            ]

            logger.info(
                f"Sending API request to add slide notes: {json.dumps(requests[0], indent=2)}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(
                f"API response for slide notes: {json.dumps(response, indent=2)}"
            )

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "operation": "add_slide_notes",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("add_slide_notes", e)

    def duplicate_slide(
        self, presentation_id: str, slide_id: str, insert_at_index: int | None = None
    ) -> dict[str, Any]:
        """
        Duplicate a slide in a presentation.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide to duplicate
            insert_at_index: Optional index where to insert the duplicated slide

        Returns:
            Response data with the new slide ID or error information
        """
        try:
            # Create the duplicate slide request
            duplicate_request = {"duplicateObject": {"objectId": slide_id}}

            # If insert location is specified
            if insert_at_index is not None:
                duplicate_request["duplicateObject"]["insertionIndex"] = str(
                    insert_at_index
                )

            logger.info(
                f"Sending API request to duplicate slide: {json.dumps(duplicate_request, indent=2)}"
            )

            # Execute the duplicate request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [duplicate_request]},
                )
                .execute()
            )

            logger.info(
                f"API response for slide duplication: {json.dumps(response, indent=2)}"
            )

            # Extract the duplicated slide ID
            new_slide_id = None
            if "replies" in response and len(response["replies"]) > 0:
                new_slide_id = (
                    response["replies"][0].get("duplicateObject", {}).get("objectId")
                )

            return {
                "presentationId": presentation_id,
                "originalSlideId": slide_id,
                "newSlideId": new_slide_id,
                "operation": "duplicate_slide",
                "result": "success",
            }
        except Exception as e:
            return self.handle_api_error("duplicate_slide", e)

    def calculate_optimal_font_size(
        self,
        text: str,
        box_width: float,
        box_height: float,
        font_family: str = "Arial",
        max_font_size: int = 48,
        min_font_size: int = 8,
    ) -> int:
        """
        Calculate optimal font size to fit text within given dimensions.
        Uses simple estimation since PIL may not be available.
        """
        try:
            # Try to import PIL for accurate measurement
            from PIL import Image, ImageDraw, ImageFont

            def get_text_dimensions(text, font_size, font_family):
                try:
                    img = Image.new("RGB", (1000, 1000), color="white")
                    draw = ImageDraw.Draw(img)

                    try:
                        font = ImageFont.truetype(f"{font_family}.ttf", font_size)
                    except:
                        font = ImageFont.load_default()

                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    return text_width, text_height
                except Exception:
                    # Fallback calculation
                    char_width = font_size * 0.6
                    text_width = len(text) * char_width
                    text_height = font_size * 1.2
                    return text_width, text_height

            # Binary search for optimal font size
            low, high = min_font_size, max_font_size
            optimal_size = min_font_size

            while low <= high:
                mid = (low + high) // 2
                text_width, text_height = get_text_dimensions(text, mid, font_family)

                if text_width <= box_width and text_height <= box_height:
                    optimal_size = mid
                    low = mid + 1
                else:
                    high = mid - 1

            return optimal_size

        except ImportError:
            # Fallback to simple estimation if PIL not available
            logger.info("PIL not available, using simple font size estimation")
            chars_per_line = int(box_width / (12 * 0.6))  # Base font size 12

            if len(text) <= chars_per_line:
                return min(max_font_size, 12)

            scale_factor = chars_per_line / len(text)
            return max(min_font_size, int(12 * scale_factor))

    def create_textbox_with_text(
        self,
        presentation_id: str,
        slide_id: str,
        text: str,
        position: tuple[float, float],
        size: tuple[float, float],
        unit: str = "EMU",
        element_id: str | None = None,
        font_family: str = "Arial",
        font_size: float = 12,
        text_alignment: str | None = None,
        vertical_alignment: str | None = None,
        auto_size_font: bool = False,
    ) -> dict[str, Any]:
        """
        Create a text box with text, font formatting, and alignment.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide (page)
            text: The text content to insert
            position: Tuple of (x, y) coordinates for position
            size: Tuple of (width, height) for the text box
            unit: Unit type - "PT" for points or "EMU" for English Metric Units (default "EMU").
            element_id: Optional custom element ID, auto-generated if not provided
            font_family: Font family to use (default "Arial")
            font_size: Font size in points (default 12)
            text_alignment: Optional horizontal alignment ("LEFT", "CENTER", "RIGHT", "JUSTIFY")
            vertical_alignment: Optional vertical alignment ("TOP", "MIDDLE", "BOTTOM")
            auto_size_font: Whether to automatically calculate font size to fit (default False - DEPRECATED)

        Returns:
            Response data or error information
        """
        try:
            # Validate unit
            if unit not in ["PT", "EMU"]:
                raise ValueError(
                    "Unit must be either 'PT' (points) or 'EMU' (English Metric Units)"
                )

            # Generate element ID if not provided
            if element_id is None:
                import time

                element_id = f"TextBox_{int(time.time() * 1000)}"

            # Convert size to API format
            width = {"magnitude": size[0], "unit": unit}
            height = {"magnitude": size[1], "unit": unit}

            # Use provided font size instead of calculation
            if auto_size_font:
                logger.warning(
                    "auto_size_font is deprecated - using provided font_size instead"
                )

            # Build requests with proper sequence
            requests = [
                # Step 1: Create text box shape (no autofit - API limitation)
                {
                    "createShape": {
                        "objectId": element_id,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {"height": height, "width": width},
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": position[0],
                                "translateY": position[1],
                                "unit": unit,
                            },
                        },
                    }
                },
                # Step 2: Set autofit to NONE (only supported value)
                {
                    "updateShapeProperties": {
                        "objectId": element_id,
                        "shapeProperties": {"autofit": {"autofitType": "NONE"}},
                        "fields": "autofit.autofitType",
                    }
                },
                # Step 3: Insert text into the text box
                {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": text,
                    }
                },
                # Step 4: Apply font size and family
                {
                    "updateTextStyle": {
                        "objectId": element_id,
                        "textRange": {"type": "ALL"},
                        "style": {
                            "fontSize": {"magnitude": font_size, "unit": "PT"},
                            "fontFamily": font_family,
                        },
                        "fields": "fontSize,fontFamily",
                    }
                },
            ]

            # Step 5: Add text alignment if specified
            if text_alignment is not None:
                alignment_map = {
                    "LEFT": "START",
                    "CENTER": "CENTER",
                    "RIGHT": "END",
                    "JUSTIFY": "JUSTIFIED",
                }

                api_alignment = alignment_map.get(text_alignment.upper())
                if api_alignment:
                    requests.append(
                        {
                            "updateParagraphStyle": {
                                "objectId": element_id,
                                "textRange": {"type": "ALL"},
                                "style": {"alignment": api_alignment},
                                "fields": "alignment",
                            }
                        }
                    )

            # Step 6: Add vertical alignment if specified
            if vertical_alignment is not None:
                valign_map = {"TOP": "TOP", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM"}

                api_valign = valign_map.get(vertical_alignment.upper())
                if api_valign:
                    requests.append(
                        {
                            "updateShapeProperties": {
                                "objectId": element_id,
                                "shapeProperties": {"contentAlignment": api_valign},
                                "fields": "contentAlignment",
                            }
                        }
                    )

            logger.info(
                f"Creating text box with font {font_family} {font_size}pt, align: {text_alignment}/{vertical_alignment}"
            )

            # Execute the request
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(f"Text box creation response: {json.dumps(response, indent=2)}")

            # Extract object ID from response if available
            created_object_id = None
            if "replies" in response and len(response["replies"]) > 0:
                create_shape_response = response["replies"][0].get("createShape")
                if create_shape_response:
                    created_object_id = create_shape_response.get("objectId")

            return {
                "presentationId": presentation_id,
                "slideId": slide_id,
                "elementId": created_object_id or element_id,
                "text": text,
                "fontSize": font_size,
                "fontFamily": font_family,
                "textAlignment": text_alignment,
                "verticalAlignment": vertical_alignment,
                "operation": "create_textbox_with_text",
                "result": "success",
                "response": response,
            }
        except Exception as e:
            return self.handle_api_error("create_textbox_with_text", e)

    def batch_update(
        self, presentation_id: str, requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Apply a list of raw Google Slides API update requests to a presentation in a single operation.
        For advanced users familiar with Slides API request structures.
        Allows creating multiple elements (text boxes, images, shapes) in a single API call.

        Args:
            presentation_id: The ID of the presentation
            requests: List of Google Slides API request objects

        Returns:
            API response data or error information
        """
        try:
            logger.info(
                f"Executing batch update with {len(requests)} requests on presentation {presentation_id}"
            )

            # Execute all requests in a single batch operation
            response = (
                self.service.presentations()
                .batchUpdate(
                    presentationId=presentation_id, body={"requests": requests}
                )
                .execute()
            )

            logger.info(
                f"Batch update completed successfully. Response: {json.dumps(response, indent=2)}"
            )

            return {
                "presentationId": presentation_id,
                "operation": "batch_update",
                "requestCount": len(requests),
                "result": "success",
                "replies": response.get("replies", []),
                "writeControl": response.get("writeControl", {}),
            }
        except Exception as e:
            return self.handle_api_error("batch_update", e)

    def create_slide_from_template_data(
        self,
        presentation_id: str,
        slide_id: str,
        template_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a complete slide from template data in a single batch operation.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide
            template_data: Dictionary containing slide elements data structure:
                {
                    "title": {"text": "...", "position": {"x": 32, "y": 35, "width": 330, "height": 40}, "style": {"fontSize": 18, "fontFamily": "Roboto"}},
                    "description": {"text": "...", "position": {"x": 32, "y": 95, "width": 330, "height": 160}, "style": {"fontSize": 12, "fontFamily": "Roboto"}},
                    "stats": [
                        {"value": "43.4M", "label": "TOTAL IMPRESSIONS", "position": {"x": 374.5, "y": 268.5}},
                        {"value": "134K", "label": "TOTAL ENGAGEMENTS", "position": {"x": 516.5, "y": 268.5}},
                        # ... more stats
                    ],
                    "image": {"url": "...", "position": {"x": 375, "y": 35}, "size": {"width": 285, "height": 215}}
                }

        Returns:
            Response data or error information
        """
        try:
            import time

            requests = []
            element_counter = 0

            # Build title element
            if "title" in template_data:
                title_id = f"title_{int(time.time() * 1000)}_{element_counter}"
                requests.extend(
                    self._build_textbox_requests(
                        title_id, slide_id, template_data["title"]
                    )
                )
                element_counter += 1

            # Build description element
            if "description" in template_data:
                desc_id = f"description_{int(time.time() * 1000)}_{element_counter}"
                requests.extend(
                    self._build_textbox_requests(
                        desc_id, slide_id, template_data["description"]
                    )
                )
                element_counter += 1

            # Build stats elements
            for i, stat in enumerate(template_data.get("stats", [])):
                # Stat value
                stat_id = f"stat_value_{int(time.time() * 1000)}_{i}"
                stat_data = {
                    "text": stat["value"],
                    "position": stat["position"],
                    "style": {
                        "fontSize": 25,
                        "fontFamily": "Playfair Display",
                        "bold": True,
                    },
                }
                requests.extend(
                    self._build_textbox_requests(stat_id, slide_id, stat_data)
                )

                # Stat label
                label_id = f"stat_label_{int(time.time() * 1000)}_{i}"
                label_pos = {
                    "x": stat["position"]["x"],
                    "y": stat["position"]["y"] + 33.5,  # Position label below value
                    "width": stat["position"].get("width", 142),
                    "height": stat["position"].get("height", 40),
                }
                label_data = {
                    "text": stat["label"],
                    "position": label_pos,
                    "style": {"fontSize": 7.5, "fontFamily": "Roboto"},
                }
                requests.extend(
                    self._build_textbox_requests(label_id, slide_id, label_data)
                )

            # Build image element
            if "image" in template_data:
                image_id = f"image_{int(time.time() * 1000)}_{element_counter}"
                requests.append(
                    self._build_image_request(
                        image_id, slide_id, template_data["image"]
                    )
                )

            logger.info(f"Built {len(requests)} requests for slide creation")

            # Execute batch update
            return self.batch_update(presentation_id, requests)

        except Exception as e:
            return self.handle_api_error("create_slide_from_template_data", e)

    def _build_textbox_requests(
        self, object_id: str, slide_id: str, textbox_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Helper to build textbox creation requests"""
        pos = textbox_data["position"]
        style = textbox_data.get("style", {})

        requests = [
            # Create shape
            {
                "createShape": {
                    "objectId": object_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": pos.get("width", 142), "unit": "PT"},
                            "height": {
                                "magnitude": pos.get("height", 40),
                                "unit": "PT",
                            },
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": pos["x"],
                            "translateY": pos["y"],
                            "unit": "PT",
                        },
                    },
                }
            },
            # Insert text
            {"insertText": {"objectId": object_id, "text": textbox_data["text"]}},
        ]

        # Add formatting if specified
        if style:
            format_request = {
                "updateTextStyle": {
                    "objectId": object_id,
                    "textRange": {"type": "ALL"},
                    "style": {},
                    "fields": "",
                }
            }

            if "fontSize" in style:
                format_request["updateTextStyle"]["style"]["fontSize"] = {
                    "magnitude": style["fontSize"],
                    "unit": "PT",
                }
                format_request["updateTextStyle"]["fields"] += "fontSize,"

            if "fontFamily" in style:
                format_request["updateTextStyle"]["style"]["fontFamily"] = style[
                    "fontFamily"
                ]
                format_request["updateTextStyle"]["fields"] += "fontFamily,"

            if style.get("bold"):
                format_request["updateTextStyle"]["style"]["bold"] = True
                format_request["updateTextStyle"]["fields"] += "bold,"

            # Clean up trailing comma
            format_request["updateTextStyle"]["fields"] = format_request[
                "updateTextStyle"
            ]["fields"].rstrip(",")

            if format_request["updateTextStyle"][
                "fields"
            ]:  # Only add if there are fields to update
                requests.append(format_request)

        return requests

    def _build_image_request(
        self, object_id: str, slide_id: str, image_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Helper to build image creation request"""
        pos = image_data["position"]
        size = image_data.get("size", {})

        request = {
            "createImage": {
                "objectId": object_id,
                "url": image_data["url"],
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": pos["x"],
                        "translateY": pos["y"],
                        "unit": "PT",
                    },
                },
            }
        }

        # Add size if specified
        if size:
            request["createImage"]["elementProperties"]["size"] = {
                "width": {"magnitude": size["width"], "unit": "PT"},
                "height": {"magnitude": size["height"], "unit": "PT"},
            }

        return request

    def create_slide_with_elements(
        self,
        presentation_id: str,
        slide_id: str | None = None,
        elements: list[dict[str, Any]] | None = None,
        background_color: str | None = None,
        background_image_url: str | None = None,
        create_slide: bool = False,
        layout: str = "BLANK",
        insert_at_index: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a complete slide with multiple elements in a single batch operation.
        NOW SUPPORTS CREATING THE SLIDE ITSELF - eliminates the two-call pattern!

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide (optional if create_slide=True)
            elements: List of element dictionaries (optional, can create empty slide), example:
                [
                    {
                        "type": "textbox",
                        "content": "Slide Title",
                        "position": {"x": 282, "y": 558, "width": 600, "height": 45},
                        "style": {
                            "fontSize": 25,
                            "fontFamily": "Playfair Display",
                            "bold": True,
                            "textAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "textColor": "#FFFFFF",  # White text
                            "backgroundColor": "#FFFFFF80"  # Semi-transparent white background
                        }
                    },
                    {
                        "type": "textbox",
                        "content": "43.4M\nTOTAL IMPRESSIONS",
                        "position": {"x": 333, "y": 4059, "width": 122, "height": 79},
                        "textRanges": [
                            {
                                "startIndex": 0,
                                "endIndex": 5,
                                "style": {
                                    "fontSize": 25,
                                    "fontFamily": "Playfair Display",
                                    "bold": True,
                                    "textColor": "#FF0000"  # Red text for the number
                                }
                            },
                            {
                                "startIndex": 6,
                                "endIndex": 22,
                                "style": {
                                    "fontSize": 7.5,
                                    "fontFamily": "Roboto",
                                    "backgroundColor": "#FFFF0080"  # Semi-transparent yellow background for label
                                }
                            }
                        ],
                        "style": {"textAlignment": "CENTER"}
                    },
                    {
                        "type": "image",
                        "content": "https://drive.google.com/file/d/.../view",
                        "position": {"x": 675, "y": 0, "width": 238, "height": 514}
                    },
                    {
                        "type": "table",
                        "content": {
                            "headers": ["Category", "Metric"],
                            "rows": [
                                ["Reach & Visibility", "Total Impressions: 43,431,803"],
                                ["Engagement", "Total Engagements: 134,431"],
                                ["Media Value", "Ad Equivalency: $9.1 million"]
                            ]
                        },
                        "position": {"x": 100, "y": 300, "width": 400, "height": 200},
                        "style": {
                            "headerStyle": {
                                "bold": true,
                                "backgroundColor": "#ff6b6b"
                            },
                            "firstColumnBold": true,
                            "fontSize": 12,
                            "fontFamily": "Roboto"
                        }
                    },
                    {
                        "type": "chart",
                        "content": {
                            "chart_type": "BAR",
                            "data": [["Month", "Revenue"], ["Jan", 2500], ["Feb", 3100], ["Mar", 2800]],
                            "title": "Monthly Revenue"
                        },
                        "position": {"x": 100, "y": 400, "width": 480, "height": 320}
                    }
                ]
            background_color: Optional slide background color (e.g., "#f8cdcd4f")
            background_image_url: Optional slide background image URL (takes precedence over background_color)
            create_slide: If True, creates the slide first. If False, adds elements to existing slide. (default: False)
            layout: Layout for new slide (BLANK, TITLE_AND_BODY, etc.) - only used if create_slide=True
            insert_at_index: Position for new slide (only used if create_slide=True)

        Returns:
            Response data or error information
        """
        try:
            import time

            final_slide_id = slide_id
            requests = []

            # Step 1: Create slide if requested
            if create_slide:
                if not final_slide_id:
                    final_slide_id = f"slide_{int(time.time() * 1000)}"

                create_slide_request = {
                    "createSlide": {
                        "objectId": final_slide_id,
                        "slideLayoutReference": {"predefinedLayout": layout},
                    }
                }

                # Add insertion index if specified
                if insert_at_index is not None:
                    create_slide_request["createSlide"][
                        "insertionIndex"
                    ] = insert_at_index

                requests.append(create_slide_request)
                logger.info(f"Added slide creation request: {final_slide_id}")

            # Ensure we have a slide ID
            if not final_slide_id:
                raise ValueError(
                    "slide_id is required when create_slide=False, or set create_slide=True"
                )

            # Step 2: Create background if specified
            if background_image_url or background_color:
                bg_request = self._build_background_request(
                    final_slide_id, background_color, background_image_url
                )
                if bg_request:
                    requests.append(bg_request)
                    logger.info("Added background request")

            # Step 3: Create elements if provided
            if elements:
                for i, element in enumerate(elements):
                    element_id = f"element_{int(time.time() * 1000)}_{i}"
                    element_type = element.get("type", "textbox").lower()

                    if element_type == "textbox":
                        element_requests = self._build_textbox_requests_generic(
                            element_id, final_slide_id, element
                        )
                        requests.extend(element_requests)
                    elif element_type == "image":
                        image_request = self._build_image_request_generic(
                            element_id, final_slide_id, element
                        )
                        requests.append(image_request)
                    elif element_type == "table":
                        table_requests = self._build_table_request_generic(
                            element_id, final_slide_id, element
                        )
                        requests.extend(table_requests)
                    else:
                        logger.warning(f"Unknown element type: {element_type}")

                logger.info(f"Added {len(elements)} element requests")

            # Execute batch update
            if requests:
                batch_result = self.batch_update(presentation_id, requests)

                # Extract slide ID from response if we created a new slide
                if create_slide and batch_result.get("replies"):
                    # The first reply should be the createSlide response
                    create_slide_reply = batch_result["replies"][0].get(
                        "createSlide", {}
                    )
                    if create_slide_reply:
                        final_slide_id = create_slide_reply.get(
                            "objectId", final_slide_id
                        )

                return {
                    "presentationId": presentation_id,
                    "slideId": final_slide_id,
                    "operation": (
                        "create_slide_with_elements"
                        if create_slide
                        else "update_slide_with_elements"
                    ),
                    "result": "success",
                    "slideCreated": create_slide,
                    "elementsAdded": len(elements or []),
                    "totalRequests": len(requests),
                    "batchResult": batch_result,
                }
            return {
                "presentationId": presentation_id,
                "slideId": final_slide_id,
                "operation": "no_operation",
                "result": "success",
                "message": "No requests generated",
            }

        except Exception as e:
            return self.handle_api_error("create_slide_with_elements", e)

    def create_multiple_slides_with_elements(
        self,
        presentation_id: str,
        slides_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create multiple slides with their elements in a single batch operation.
        PERFECT FOR BULK SLIDE CREATION - eliminates the need for multiple API calls!

        Args:
            presentation_id: The ID of the presentation
            slides_data: List of slide dictionaries, each containing:
                {
                    "layout": "BLANK",  # Optional, defaults to "BLANK"
                    "background_color": "#f8cdcd4f",  # Optional
                    "background_image_url": "https://...",  # Optional
                    "insert_at_index": 2,  # Optional, where to insert this slide
                    "elements": [  # Optional list of elements for this slide
                        {
                            "type": "textbox",
                            "content": "Slide 1 Title",
                            "position": {"x": 100, "y": 100, "width": 400, "height": 50},
                            "style": {"fontSize": 18, "bold": True}
                        },
                        {
                            "type": "image",
                            "content": "https://images.unsplash.com/...",
                            "position": {"x": 200, "y": 200, "width": 300, "height": 200}
                        }
                    ]
                }

        Returns:
            Response data with all created slide IDs and operation details

        Example Usage:
            # Create 5 slides with elements in ONE API call:
            slides_data = [
                {
                    "layout": "BLANK",
                    "background_color": "#f0f0f0",
                    "elements": [
                        {
                            "type": "textbox",
                            "content": "Slide 1 Title",
                            "position": {"x": 100, "y": 100, "width": 400, "height": 50},
                            "style": {"fontSize": 20, "bold": True}
                        }
                    ]
                },
                {
                    "layout": "BLANK",
                    "elements": [
                        {
                            "type": "textbox",
                            "content": "Slide 2 Content",
                            "position": {"x": 100, "y": 150, "width": 400, "height": 100},
                            "style": {"fontSize": 14}
                        },
                        {
                            "type": "image",
                            "content": "https://images.unsplash.com/photo-1565299507177-b0ac66763828",
                            "position": {"x": 300, "y": 300, "width": 200, "height": 150}
                        }
                    ]
                },
                # ... up to 3 more slides
            ]

            result = slides_service.create_multiple_slides_with_elements(
                presentation_id="abc123",
                slides_data=slides_data
            )
            # Returns: {"slideIds": ["slide_1", "slide_2", ...], "slidesCreated": 5, "totalRequests": 25}
        """
        try:
            import time

            if not slides_data:
                raise ValueError("slides_data cannot be empty")

            # Track converted images for cleanup at the end
            converted_images = []

            # Pre-process slides data to convert private images to public
            logger.info(
                f"Pre-processing {len(slides_data)} slides for private image handling"
            )
            for slide_data in slides_data:
                # Handle background images
                background_image_url = slide_data.get("background_image_url", "")
                if background_image_url and self._is_private_drive_url(
                    background_image_url
                ):
                    logger.info(
                        f"Converting private background image to public: {background_image_url}"
                    )
                    public_url = self._convert_private_image_to_public(
                        background_image_url, converted_images
                    )
                    slide_data["background_image_url"] = public_url

                # Handle element images
                elements = slide_data.get("elements", [])
                for element in elements:
                    if element.get("type", "").lower() == "image":
                        image_url = element.get("content", "")
                        if image_url and self._is_private_drive_url(image_url):
                            logger.info(
                                f"Converting private image to public: {image_url}"
                            )
                            public_url = self._convert_private_image_to_public(
                                image_url, converted_images
                            )
                            element["content"] = public_url

            all_requests = []
            slide_ids = []
            chart_data = []  # Store chart elements for post-processing
            base_timestamp = int(time.time() * 1000)

            logger.info(f"Creating {len(slides_data)} slides in batch operation")

            # Process each slide
            for slide_index, slide_data in enumerate(slides_data):
                slide_id = f"slide_{base_timestamp}_{slide_index}"
                slide_ids.append(slide_id)

                layout = slide_data.get("layout", "BLANK")
                background_color = slide_data.get("background_color")
                background_image_url = slide_data.get("background_image_url")
                insert_at_index = slide_data.get("insert_at_index")
                elements = slide_data.get("elements", [])

                # Step 1: Create slide
                create_slide_request = {
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": layout},
                    }
                }

                # Add insertion index if specified
                if insert_at_index is not None:
                    create_slide_request["createSlide"]["insertionIndex"] = (
                        insert_at_index
                        + slide_index  # Adjust index for multiple slides
                    )

                all_requests.append(create_slide_request)

                # Step 2: Add background if specified
                if background_image_url or background_color:
                    bg_request = self._build_background_request(
                        slide_id, background_color, background_image_url
                    )
                    if bg_request:
                        all_requests.append(bg_request)

                # Step 3: Add elements for this slide
                for element_index, element in enumerate(elements):
                    element_id = (
                        f"element_{base_timestamp}_{slide_index}_{element_index}"
                    )
                    element_type = element.get("type", "textbox").lower()

                    if element_type == "textbox":
                        element_requests = self._build_textbox_requests_generic(
                            element_id, slide_id, element
                        )
                        all_requests.extend(element_requests)
                    elif element_type == "image":
                        image_request = self._build_image_request_generic(
                            element_id, slide_id, element
                        )
                        all_requests.append(image_request)
                    elif element_type == "table":
                        table_requests = self._build_table_request_generic(
                            element_id, slide_id, element
                        )
                        all_requests.extend(table_requests)
                    elif element_type == "chart":
                        # Collect chart data for post-processing
                        chart_data.append(
                            {
                                "slide_id": slide_id,
                                "element_id": element_id,
                                "chart_data": element,
                            }
                        )
                        logger.info(
                            f"Collected chart element for post-processing: {element_id}"
                        )
                    else:
                        logger.warning(f"Unknown element type: {element_type}")

                logger.debug(
                    f"Slide {slide_index + 1}: {slide_id} with {len(elements)} elements"
                )

            # Execute all requests in single batch operation
            logger.info(
                f"Executing batch creation of {len(slides_data)} slides with {len(all_requests)} total requests"
            )

            batch_result = self.batch_update(presentation_id, all_requests)

            # Extract actual slide IDs from response (in case Google changed them)
            created_slide_ids = []
            if batch_result.get("replies"):
                for _i, reply in enumerate(batch_result["replies"]):
                    if "createSlide" in reply:
                        actual_slide_id = reply["createSlide"].get("objectId")
                        if actual_slide_id:
                            created_slide_ids.append(actual_slide_id)

            # Use created IDs if available, otherwise use our generated ones
            final_slide_ids = created_slide_ids if created_slide_ids else slide_ids

            # Process charts after slide creation is complete
            chart_results = []
            if chart_data:
                logger.info(f"Processing {len(chart_data)} chart elements")
                for chart_element in chart_data:
                    try:
                        chart_result = self._process_chart_element(
                            presentation_id,
                            chart_element["slide_id"],
                            chart_element["chart_data"],
                            chart_element["element_id"],
                        )
                        chart_results.append(chart_result)
                        logger.info(
                            f"Successfully processed chart element: {chart_element['element_id']}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to process chart element {chart_element['element_id']}: {e}"
                        )
                        chart_results.append(
                            {"error": str(e), "element_id": chart_element["element_id"]}
                        )

            # Clean up: revert all converted images back to private
            self._revert_images_to_private(converted_images)

            return {
                "presentationId": presentation_id,
                "slideIds": final_slide_ids,
                "operation": "create_multiple_slides_with_elements",
                "result": "success",
                "slidesCreated": len(slides_data),
                "totalRequests": len(all_requests),
                "chartsProcessed": len(chart_data),
                "totalElements": sum(
                    len(slide.get("elements", [])) for slide in slides_data
                ),
                "batchResult": batch_result,
                "chartResults": chart_results,
            }

        except Exception as e:
            # Clean up: revert all converted images back to private even on error
            self._revert_images_to_private(converted_images)
            return self.handle_api_error("create_multiple_slides_with_elements", e)

    def _build_textbox_requests_generic(
        self, object_id: str, slide_id: str, element: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generic helper to build textbox creation requests with support for mixed text formatting"""
        pos = element["position"]
        style = element.get("style", {})
        text_ranges = element.get("textRanges")

        requests = [
            # Create shape
            {
                "createShape": {
                    "objectId": object_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": pos["width"], "unit": "PT"},
                            "height": {"magnitude": pos["height"], "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": pos["x"],
                            "translateY": pos["y"],
                            "unit": "PT",
                        },
                    },
                }
            },
            # Insert text
            {"insertText": {"objectId": object_id, "text": element["content"]}},
        ]

        # Add formatting for the entire text if specified (base formatting)
        if style:
            format_request = {
                "updateTextStyle": {
                    "objectId": object_id,
                    "textRange": {"type": "ALL"},
                    "style": {},
                    "fields": "",
                }
            }

            if "fontSize" in style:
                format_request["updateTextStyle"]["style"]["fontSize"] = {
                    "magnitude": style["fontSize"],
                    "unit": "PT",
                }
                format_request["updateTextStyle"]["fields"] += "fontSize,"

            if "fontFamily" in style:
                format_request["updateTextStyle"]["style"]["fontFamily"] = style[
                    "fontFamily"
                ]
                format_request["updateTextStyle"]["fields"] += "fontFamily,"

            if style.get("bold"):
                format_request["updateTextStyle"]["style"]["bold"] = True
                format_request["updateTextStyle"]["fields"] += "bold,"

            # Add foreground color support
            if "color" in style or "foregroundColor" in style or "textColor" in style:
                color_value = (
                    style.get("color")
                    or style.get("foregroundColor")
                    or style.get("textColor")
                )
                color_obj = self._parse_color(color_value)
                if color_obj:
                    format_request["updateTextStyle"]["style"][
                        "foregroundColor"
                    ] = color_obj
                    format_request["updateTextStyle"]["fields"] += "foregroundColor,"

            # Clean up trailing comma and add format request
            format_request["updateTextStyle"]["fields"] = format_request[
                "updateTextStyle"
            ]["fields"].rstrip(",")

            if format_request["updateTextStyle"]["fields"]:
                requests.append(format_request)

        # Handle mixed text formatting with textRanges (applied on top of base formatting)
        if text_ranges:
            # Convert content-based ranges to index-based ranges automatically
            processed_ranges = self._process_text_ranges(
                element["content"], text_ranges
            )

            for text_range in processed_ranges:
                range_style = text_range.get("style", {})
                start_index = text_range.get("startIndex", 0)
                end_index = text_range.get("endIndex", len(element["content"]))

                if range_style:
                    format_request = {
                        "updateTextStyle": {
                            "objectId": object_id,
                            "textRange": {
                                "type": "FIXED_RANGE",
                                "startIndex": start_index,
                                "endIndex": end_index,
                            },
                            "style": {},
                            "fields": "",
                        }
                    }

                    if "fontSize" in range_style:
                        format_request["updateTextStyle"]["style"]["fontSize"] = {
                            "magnitude": range_style["fontSize"],
                            "unit": "PT",
                        }
                        format_request["updateTextStyle"]["fields"] += "fontSize,"

                    if "fontFamily" in range_style:
                        format_request["updateTextStyle"]["style"]["fontFamily"] = (
                            range_style["fontFamily"]
                        )
                        format_request["updateTextStyle"]["fields"] += "fontFamily,"

                    if range_style.get("bold"):
                        format_request["updateTextStyle"]["style"]["bold"] = True
                        format_request["updateTextStyle"]["fields"] += "bold,"

                    # Add foreground color support
                    if (
                        "color" in range_style
                        or "foregroundColor" in range_style
                        or "textColor" in range_style
                    ):
                        color_value = (
                            range_style.get("color")
                            or range_style.get("foregroundColor")
                            or range_style.get("textColor")
                        )
                        color_obj = self._parse_color(color_value)
                        if color_obj:
                            format_request["updateTextStyle"]["style"][
                                "foregroundColor"
                            ] = color_obj
                            format_request["updateTextStyle"][
                                "fields"
                            ] += "foregroundColor,"

                    # Clean up trailing comma and add format request
                    format_request["updateTextStyle"]["fields"] = format_request[
                        "updateTextStyle"
                    ]["fields"].rstrip(",")

                    if format_request["updateTextStyle"]["fields"]:
                        requests.append(format_request)

        # Add text alignment (paragraph-level)
        if style and style.get("textAlignment"):
            alignment_map = {
                "LEFT": "START",
                "CENTER": "CENTER",
                "RIGHT": "END",
                "JUSTIFY": "JUSTIFIED",
            }
            api_alignment = alignment_map.get(style["textAlignment"].upper(), "START")
            requests.append(
                {
                    "updateParagraphStyle": {
                        "objectId": object_id,
                        "textRange": {"type": "ALL"},
                        "style": {"alignment": api_alignment},
                        "fields": "alignment",
                    }
                }
            )

        # Add vertical alignment (shape-level)
        if style and style.get("verticalAlignment"):
            valign_map = {"TOP": "TOP", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM"}
            api_valign = valign_map.get(style["verticalAlignment"].upper(), "TOP")
            requests.append(
                {
                    "updateShapeProperties": {
                        "objectId": object_id,
                        "shapeProperties": {"contentAlignment": api_valign},
                        "fields": "contentAlignment",
                    }
                }
            )

        # Add text box background color (shape-level) - this is the key fix!
        if style and style.get("backgroundColor"):
            color_obj, alpha = self._parse_color_with_alpha(style["backgroundColor"])
            if color_obj:
                requests.append(
                    {
                        "updateShapeProperties": {
                            "objectId": object_id,
                            "shapeProperties": {
                                "shapeBackgroundFill": {
                                    "solidFill": {"color": color_obj, "alpha": alpha}
                                }
                            },
                            "fields": "shapeBackgroundFill",
                        }
                    }
                )

        return requests

    def _process_text_ranges(self, content: str, text_ranges: list[dict]) -> list[dict]:
        """
        Process textRanges to support both content-based and index-based ranges.

        Args:
            content: The full text content
            text_ranges: List of textRange objects that can be either:
                - Index-based: {"startIndex": 0, "endIndex": 5, "style": {...}}
                - Content-based: {"content": "43.4M", "style": {...}}

        Returns:
            List of index-based textRange objects
        """
        processed_ranges = []

        for text_range in text_ranges:
            if "content" in text_range:
                # Content-based range - find the text in the content
                target_content = text_range["content"]
                start_index = content.find(target_content)

                if start_index >= 0:
                    end_index = start_index + len(target_content)
                    processed_ranges.append(
                        {
                            "startIndex": start_index,
                            "endIndex": end_index,
                            "style": text_range.get("style", {}),
                        }
                    )
                else:
                    # Content not found - log warning but continue
                    logger.warning(
                        f"Content '{target_content}' not found in text: '{content}'"
                    )
            else:
                # Index-based range - use as-is but validate indices
                start_index = text_range.get("startIndex", 0)
                end_index = text_range.get("endIndex", len(content))

                # Auto-fix common off-by-one errors
                if end_index == len(content) - 1:
                    end_index = len(content)
                    logger.info(
                        f"Auto-corrected endIndex from {len(content) - 1} to {len(content)}"
                    )

                # Validate indices
                if (
                    start_index >= 0
                    and end_index <= len(content)
                    and start_index < end_index
                ):
                    processed_ranges.append(
                        {
                            "startIndex": start_index,
                            "endIndex": end_index,
                            "style": text_range.get("style", {}),
                        }
                    )
                else:
                    logger.warning(
                        f"Invalid text range indices: start={start_index}, end={end_index}, content_length={len(content)}"
                    )

        return processed_ranges

    def _parse_color(self, color_value: str | dict) -> dict | None:
        """Parse color value into Google Slides API format.

        Args:
            color_value: Color as hex string (e.g., "#ffffff"), RGB dict, or theme color

        Returns:
            Color object in Google Slides API format or None if invalid
        """
        if not color_value:
            return None

        # Handle hex color strings
        if isinstance(color_value, str):
            if color_value.lower() == "white":
                color_value = "#ffffff"
            elif color_value.lower() == "black":
                color_value = "#000000"

            if color_value.startswith("#"):
                # Convert hex to RGB
                try:
                    hex_color = color_value.lstrip("#")
                    if len(hex_color) == 6:
                        r = int(hex_color[0:2], 16) / 255.0
                        g = int(hex_color[2:4], 16) / 255.0
                        b = int(hex_color[4:6], 16) / 255.0

                        return {
                            "opaqueColor": {
                                "rgbColor": {"red": r, "green": g, "blue": b}
                            }
                        }
                    if len(hex_color) == 8:
                        # Handle 8-character hex with alpha (RRGGBBAA)
                        r = int(hex_color[0:2], 16) / 255.0
                        g = int(hex_color[2:4], 16) / 255.0
                        b = int(hex_color[4:6], 16) / 255.0
                        int(hex_color[6:8], 16) / 255.0

                        return {
                            "opaqueColor": {
                                "rgbColor": {"red": r, "green": g, "blue": b}
                            }
                        }
                        # Note: Google Slides API doesn't support alpha in text colors directly
                        # The alpha would need to be handled differently (e.g., using SolidFill with alpha)
                except ValueError:
                    logger.warning(f"Invalid hex color format: {color_value}")
                    return None

        # Handle RGB dict format
        elif isinstance(color_value, dict):
            if "r" in color_value and "g" in color_value and "b" in color_value:
                return {
                    "opaqueColor": {
                        "rgbColor": {
                            "red": color_value["r"] / 255.0,
                            "green": color_value["g"] / 255.0,
                            "blue": color_value["b"] / 255.0,
                        }
                    }
                }
            if (
                "red" in color_value
                and "green" in color_value
                and "blue" in color_value
            ):
                return {
                    "opaqueColor": {
                        "rgbColor": {
                            "red": color_value["red"],
                            "green": color_value["green"],
                            "blue": color_value["blue"],
                        }
                    }
                }

        logger.warning(f"Unsupported color format: {color_value}")
        return None

    def _build_image_request_generic(
        self, object_id: str, slide_id: str, element: dict[str, Any]
    ) -> dict[str, Any]:
        """Generic helper to build image creation request with smart sizing support"""
        pos = element["position"]

        request = {
            "createImage": {
                "objectId": object_id,
                "url": element["content"],  # For images, content is the URL
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": pos["x"],
                        "translateY": pos["y"],
                        "unit": "PT",
                    },
                },
            }
        }

        # Smart sizing: handle different dimension specifications
        # IMPORTANT: Google Slides API limitation - createImage requires BOTH width and height
        # if size is specified, or omit size entirely. Single dimension causes UNIT_UNSPECIFIED error.

        if "width" in pos and "height" in pos and pos["width"] and pos["height"]:
            # Both dimensions specified - exact sizing
            request["createImage"]["elementProperties"]["size"] = {
                "width": {"magnitude": pos["width"], "unit": "PT"},
                "height": {"magnitude": pos["height"], "unit": "PT"},
            }
        elif "height" in pos and pos["height"]:
            # Only height specified - assume this is for portrait/vertical images
            # Use a reasonable aspect ratio (3:4 portrait) to calculate width
            height = pos["height"]
            width = height * (3.0 / 4.0)  # 3:4 aspect ratio (portrait)
            logger.info(
                f"Image height specified ({height}pt), calculating proportional width ({width:.1f}pt) using 3:4 aspect ratio"
            )
            request["createImage"]["elementProperties"]["size"] = {
                "width": {"magnitude": width, "unit": "PT"},
                "height": {"magnitude": height, "unit": "PT"},
            }
        elif "width" in pos and pos["width"]:
            # Only width specified - assume this is for landscape images
            # Use a reasonable aspect ratio (16:9 landscape) to calculate height
            width = pos["width"]
            height = width * (9.0 / 16.0)  # 16:9 aspect ratio (landscape)
            logger.info(
                f"Image width specified ({width}pt), calculating proportional height ({height:.1f}pt) using 16:9 aspect ratio"
            )
            request["createImage"]["elementProperties"]["size"] = {
                "width": {"magnitude": width, "unit": "PT"},
                "height": {"magnitude": height, "unit": "PT"},
            }
        # If neither width nor height specified, omit size - image uses natural dimensions

        return request

    def _build_table_request_generic(
        self, object_id: str, slide_id: str, element: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generic helper to build table creation requests with data population"""
        pos = element["position"]
        content = element["content"]

        # Extract table data
        headers = content.get("headers", [])
        rows_data = content.get("rows", [])

        # Calculate table dimensions
        num_rows = len(rows_data) + (
            1 if headers else 0
        )  # Add 1 for headers if present
        num_columns = max(
            len(headers) if headers else 0,
            max(len(row) for row in rows_data) if rows_data else 0,
        )

        if num_columns == 0 or num_rows == 0:
            logger.warning("Table has no data, skipping creation")
            return []

        requests = []

        # Create table request
        create_table_request = {
            "createTable": {
                "objectId": object_id,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": pos["width"], "unit": "PT"},
                        "height": {"magnitude": pos["height"], "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": pos["x"],
                        "translateY": pos["y"],
                        "unit": "PT",
                    },
                },
                "rows": num_rows,
                "columns": num_columns,
            }
        }
        requests.append(create_table_request)

        # Populate table with data
        current_row = 0

        # Insert headers if present
        if headers:
            for col_index, header_text in enumerate(headers):
                if col_index < num_columns and header_text:
                    requests.append(
                        {
                            "insertText": {
                                "objectId": object_id,
                                "cellLocation": {
                                    "rowIndex": current_row,
                                    "columnIndex": col_index,
                                },
                                "text": str(header_text),
                                "insertionIndex": 0,
                            }
                        }
                    )
            current_row += 1

        # Insert row data
        for row_index, row in enumerate(rows_data):
            table_row_index = current_row + row_index
            for col_index, cell_text in enumerate(row):
                if col_index < num_columns and cell_text and table_row_index < num_rows:
                    requests.append(
                        {
                            "insertText": {
                                "objectId": object_id,
                                "cellLocation": {
                                    "rowIndex": table_row_index,
                                    "columnIndex": col_index,
                                },
                                "text": str(cell_text),
                                "insertionIndex": 0,
                            }
                        }
                    )

                # Add table styling based on style configuration
        style = element.get("style", {})

        # Add styling based on prompt rules
        if style:
            # Apply base font formatting to ALL table cells first (like we fixed for textboxes)
            if "fontSize" in style or "fontFamily" in style:
                for row_idx in range(num_rows):
                    for col_idx in range(num_columns):
                        base_style_request = {
                            "updateTextStyle": {
                                "objectId": object_id,
                                "cellLocation": {
                                    "rowIndex": row_idx,
                                    "columnIndex": col_idx,
                                },
                                "style": {},
                                "fields": "",
                            }
                        }

                        if "fontSize" in style:
                            base_style_request["updateTextStyle"]["style"][
                                "fontSize"
                            ] = {
                                "magnitude": style["fontSize"],
                                "unit": "PT",
                            }
                            base_style_request["updateTextStyle"][
                                "fields"
                            ] += "fontSize,"

                        if "fontFamily" in style:
                            base_style_request["updateTextStyle"]["style"][
                                "fontFamily"
                            ] = style["fontFamily"]
                            base_style_request["updateTextStyle"][
                                "fields"
                            ] += "fontFamily,"

                        # Clean up trailing comma
                        base_style_request["updateTextStyle"]["fields"] = (
                            base_style_request["updateTextStyle"]["fields"].rstrip(",")
                        )

                        if base_style_request["updateTextStyle"]["fields"]:
                            requests.append(base_style_request)

            # Make first column bold if specified (prompt rule)
            if style.get("firstColumnBold", False):
                for row_idx in range(num_rows):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "objectId": object_id,
                                "cellLocation": {
                                    "rowIndex": row_idx,
                                    "columnIndex": 0,
                                },
                                "style": {"bold": True},
                                "fields": "bold",
                            }
                        }
                    )
            # Add header row styling if headers are present
            if headers and style.get("headerStyle"):
                header_style = style["headerStyle"]
                for col_index in range(len(headers)):
                    if header_style.get("bold"):
                        requests.append(
                            {
                                "updateTextStyle": {
                                    "objectId": object_id,
                                    "cellLocation": {
                                        "rowIndex": 0,
                                        "columnIndex": col_index,
                                    },
                                    "style": {"bold": True},
                                    "fields": "bold",
                                }
                            }
                        )

                    if header_style.get("backgroundColor"):
                        color_obj, alpha = self._parse_color_with_alpha(
                            header_style["backgroundColor"]
                        )
                        if color_obj:
                            requests.append(
                                {
                                    "updateTableCellProperties": {
                                        "objectId": object_id,
                                        "tableRange": {
                                            "location": {
                                                "rowIndex": 0,
                                                "columnIndex": col_index,
                                            },
                                            "rowSpan": 1,
                                            "columnSpan": 1,
                                        },
                                        "tableCellProperties": {
                                            "tableCellBackgroundFill": {
                                                "solidFill": {
                                                    "color": color_obj,
                                                    "alpha": alpha,
                                                }
                                            }
                                        },
                                        "fields": "tableCellBackgroundFill",
                                    }
                                }
                            )

        return requests

    def _hex_to_rgb(self, hex_color: str) -> dict[str, float]:
        """Convert hex color to RGB values (0-1 range)"""
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Handle 8-character hex (with alpha) by taking first 6 characters
        if len(hex_color) == 8:
            hex_color = hex_color[:6]

        # Convert to RGB
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return {"red": r, "green": g, "blue": b}
        except ValueError:
            # Default to light pink if conversion fails
            return {"red": 0.97, "green": 0.8, "blue": 0.8}

    def update_text_formatting(
        self,
        presentation_id: str,
        element_id: str,
        formatted_text: str,
        font_size: float | None = None,
        font_family: str | None = None,
        text_alignment: str | None = None,
        vertical_alignment: str | None = None,
        start_index: int | None = None,
        end_index: int | None = None,
    ) -> dict[str, Any]:
        """
        Update formatting of text in an existing text box with support for font and alignment parameters.

        Args:
            presentation_id: The ID of the presentation
            element_id: The ID of the text box element
            formatted_text: Text with formatting markers (**, *, etc.)
            font_size: Optional font size in points (e.g., 25, 7.5)
            font_family: Optional font family (e.g., "Playfair Display", "Roboto", "Arial")
            text_alignment: Optional horizontal alignment ("LEFT", "CENTER", "RIGHT", "JUSTIFY")
            vertical_alignment: Optional vertical alignment ("TOP", "MIDDLE", "BOTTOM")
            start_index: Optional start index for applying formatting to specific range (0-based)
            end_index: Optional end index for applying formatting to specific range (exclusive)

        Returns:
            Response data or error information
        """
        try:
            import re

            # First, replace the text content if needed
            plain_text = formatted_text
            # Remove bold markers
            plain_text = re.sub(r"\*\*(.*?)\*\*", r"\1", plain_text)
            # Remove italic markers
            plain_text = re.sub(r"\*(.*?)\*", r"\1", plain_text)
            # Remove code markers if present
            plain_text = re.sub(r"`(.*?)`", r"\1", plain_text)

            # Update the text content first if it has formatting markers
            if plain_text != formatted_text:
                update_text_request = {
                    "deleteText": {"objectId": element_id, "textRange": {"type": "ALL"}}
                }

                insert_text_request = {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": plain_text,
                    }
                }

                # Execute text replacement
                self.service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [update_text_request, insert_text_request]},
                ).execute()

            # Generate style requests
            style_requests = []

            # If font_size or font_family are specified, apply them to the specified range or entire text
            if font_size is not None or font_family is not None:
                style = {}
                fields = []

                if font_size is not None:
                    style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
                    fields.append("fontSize")

                if font_family is not None:
                    style["fontFamily"] = font_family
                    fields.append("fontFamily")

                if style:
                    text_range = {"type": "ALL"}
                    if start_index is not None and end_index is not None:
                        text_range = {
                            "type": "FIXED_RANGE",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        }

                    style_requests.append(
                        {
                            "updateTextStyle": {
                                "objectId": element_id,
                                "textRange": text_range,
                                "style": style,
                                "fields": ",".join(fields),
                            }
                        }
                    )

            # Handle text alignment (paragraph-level formatting)
            if text_alignment is not None:
                # Map alignment values to Google Slides API format
                alignment_map = {
                    "LEFT": "START",
                    "CENTER": "CENTER",
                    "RIGHT": "END",
                    "JUSTIFY": "JUSTIFIED",
                }

                api_alignment = alignment_map.get(text_alignment.upper(), "START")
                if api_alignment:
                    text_range = {"type": "ALL"}
                    if start_index is not None and end_index is not None:
                        text_range = {
                            "type": "FIXED_RANGE",
                            "startIndex": start_index,
                            "endIndex": end_index,
                        }

                    style_requests.append(
                        {
                            "updateParagraphStyle": {
                                "objectId": element_id,
                                "textRange": text_range,
                                "style": {"alignment": api_alignment},
                                "fields": "alignment",
                            }
                        }
                    )

            # Handle vertical alignment (content alignment for the entire text box)
            if vertical_alignment is not None:
                # Map vertical alignment values to Google Slides API format
                valign_map = {"TOP": "TOP", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM"}

                api_valign = valign_map.get(vertical_alignment.upper(), "TOP")
                if api_valign:
                    style_requests.append(
                        {
                            "updateShapeProperties": {
                                "objectId": element_id,
                                "shapeProperties": {"contentAlignment": api_valign},
                                "fields": "contentAlignment",
                            }
                        }
                    )

            # Process bold text formatting
            bold_pattern = r"\*\*(.*?)\*\*"
            bold_matches = list(re.finditer(bold_pattern, formatted_text))

            text_offset = 0  # Track offset due to removed markers
            for match in bold_matches:
                content = match.group(1)
                # Calculate position in plain text
                start_pos = match.start() - text_offset
                end_pos = start_pos + len(content)

                style_requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": element_id,
                            "textRange": {
                                "type": "FIXED_RANGE",
                                "startIndex": start_pos,
                                "endIndex": end_pos,
                            },
                            "style": {"bold": True},
                            "fields": "bold",
                        }
                    }
                )

                # Update offset (removed 4 characters: **)
                text_offset += 4

            # Process italic text formatting
            italic_pattern = r"\*(.*?)\*"
            italic_matches = list(re.finditer(italic_pattern, formatted_text))

            text_offset = 0  # Reset offset for italic processing
            for match in italic_matches:
                content = match.group(1)
                # Skip if this is part of a bold pattern
                if any(
                    bold_match.start() <= match.start() < bold_match.end()
                    for bold_match in bold_matches
                ):
                    continue

                start_pos = match.start() - text_offset
                end_pos = start_pos + len(content)

                style_requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": element_id,
                            "textRange": {
                                "type": "FIXED_RANGE",
                                "startIndex": start_pos,
                                "endIndex": end_pos,
                            },
                            "style": {"italic": True},
                            "fields": "italic",
                        }
                    }
                )

                # Update offset (removed 2 characters: *)
                text_offset += 2

            # Process code text formatting
            code_pattern = r"`(.*?)`"
            code_matches = list(re.finditer(code_pattern, formatted_text))

            text_offset = 0  # Reset offset for code processing
            for match in code_matches:
                content = match.group(1)
                start_pos = match.start() - text_offset
                end_pos = start_pos + len(content)

                style_requests.append(
                    {
                        "updateTextStyle": {
                            "objectId": element_id,
                            "textRange": {
                                "type": "FIXED_RANGE",
                                "startIndex": start_pos,
                                "endIndex": end_pos,
                            },
                            "style": {
                                "fontFamily": "Courier New",
                                "backgroundColor": {
                                    "opaqueColor": {
                                        "rgbColor": {
                                            "red": 0.95,
                                            "green": 0.95,
                                            "blue": 0.95,
                                        }
                                    }
                                },
                            },
                            "fields": "fontFamily,backgroundColor",
                        }
                    }
                )

                # Update offset (removed 2 characters: `)
                text_offset += 2

            # Execute all style requests
            if style_requests:
                logger.info(f"Applying {len(style_requests)} formatting requests")
                (
                    self.service.presentations()
                    .batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": style_requests},
                    )
                    .execute()
                )

                return {
                    "presentationId": presentation_id,
                    "elementId": element_id,
                    "appliedFormats": {
                        "fontSize": font_size,
                        "fontFamily": font_family,
                        "textAlignment": text_alignment,
                        "verticalAlignment": vertical_alignment,
                        "textRange": (
                            {"startIndex": start_index, "endIndex": end_index}
                            if start_index is not None and end_index is not None
                            else "ALL"
                        ),
                    },
                    "operation": "update_text_formatting",
                    "result": "success",
                }

            return {"result": "no_formatting_applied"}

        except Exception as e:
            return self.handle_api_error("update_text_formatting", e)

    def convert_template_zones_to_pt(
        self, template_zones: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Convert template zones coordinates from EMU to PT for easier slide element creation.

        Args:
            template_zones: Template zones from extract_template_zones_only

        Returns:
            Template zones with additional PT coordinates (x_pt, y_pt, width_pt, height_pt)
        """
        try:
            return convert_template_zones(template_zones, target_unit="PT")
        except Exception as e:
            return self.handle_api_error("convert_template_zones_to_pt", e)

    def _parse_color_with_alpha(
        self, color_value: str | dict
    ) -> tuple[dict | None, float]:
        """Parse color value with alpha support for Google Slides API format.

        Args:
            color_value: Color as hex string (e.g., "#ffffff", "#ffffff80"), RGB dict, rgba() string, or theme color

        Returns:
            Tuple of (color_object, alpha_value) where alpha is 0.0-1.0
        """
        if not color_value:
            return None, 1.0

        alpha = 1.0  # Default to fully opaque

        # Handle hex color strings
        if isinstance(color_value, str):
            if color_value.lower() == "white":
                color_value = "#ffffff"
            elif color_value.lower() == "black":
                color_value = "#000000"

            # Handle rgba() CSS format
            if color_value.startswith("rgba("):
                import re

                # Parse rgba(r, g, b, a) format
                match = re.match(
                    r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
                    color_value,
                )
                if match:
                    r = int(match.group(1)) / 255.0
                    g = int(match.group(2)) / 255.0
                    b = int(match.group(3)) / 255.0
                    alpha = float(match.group(4))

                    color_obj = {"rgbColor": {"red": r, "green": g, "blue": b}}
                    return color_obj, alpha
                logger.warning(f"Invalid rgba format: {color_value}")
                return None, 1.0

            # Handle rgb() CSS format (no alpha)
            if color_value.startswith("rgb("):
                import re

                # Parse rgb(r, g, b) format
                match = re.match(
                    r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_value
                )
                if match:
                    r = int(match.group(1)) / 255.0
                    g = int(match.group(2)) / 255.0
                    b = int(match.group(3)) / 255.0

                    color_obj = {"rgbColor": {"red": r, "green": g, "blue": b}}
                    return color_obj, alpha
                logger.warning(f"Invalid rgb format: {color_value}")
                return None, 1.0

            if color_value.startswith("#"):
                # Convert hex to RGB
                try:
                    hex_color = color_value.lstrip("#")
                    if len(hex_color) == 6:
                        r = int(hex_color[0:2], 16) / 255.0
                        g = int(hex_color[2:4], 16) / 255.0
                        b = int(hex_color[4:6], 16) / 255.0

                        color_obj = {"rgbColor": {"red": r, "green": g, "blue": b}}
                        return color_obj, alpha
                    if len(hex_color) == 8:
                        # Handle 8-character hex with alpha (RRGGBBAA)
                        r = int(hex_color[0:2], 16) / 255.0
                        g = int(hex_color[2:4], 16) / 255.0
                        b = int(hex_color[4:6], 16) / 255.0
                        alpha = int(hex_color[6:8], 16) / 255.0  # Extract alpha

                        color_obj = {"rgbColor": {"red": r, "green": g, "blue": b}}
                        return color_obj, alpha
                except ValueError:
                    logger.warning(f"Invalid hex color format: {color_value}")
                    return None, 1.0

        # Handle RGB dict format
        elif isinstance(color_value, dict):
            if "r" in color_value and "g" in color_value and "b" in color_value:
                color_obj = {
                    "rgbColor": {
                        "red": color_value["r"] / 255.0,
                        "green": color_value["g"] / 255.0,
                        "blue": color_value["b"] / 255.0,
                    }
                }
                alpha = color_value.get("a", 255) / 255.0  # Handle alpha if present
                return color_obj, alpha
            if (
                "red" in color_value
                and "green" in color_value
                and "blue" in color_value
            ):
                color_obj = {
                    "rgbColor": {
                        "red": color_value["red"],
                        "green": color_value["green"],
                        "blue": color_value["blue"],
                    }
                }
                alpha = color_value.get("alpha", 1.0)  # Handle alpha if present
                return color_obj, alpha

        logger.warning(f"Unsupported color format: {color_value}")
        return None, 1.0

    def _build_background_request(
        self,
        slide_id: str,
        background_color: str | None,
        background_image_url: str | None,
    ) -> dict[str, Any] | None:
        """Helper to build background request for a slide"""
        if background_image_url:
            logger.info(f"Setting slide background image: {background_image_url}")
            return {
                "updatePageProperties": {
                    "objectId": slide_id,
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "stretchedPictureFill": {"contentUrl": background_image_url}
                        }
                    },
                    "fields": "pageBackgroundFill",
                }
            }
        if background_color:
            logger.info(f"Setting slide background color: {background_color}")
            return {
                "updatePageProperties": {
                    "objectId": slide_id,
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {
                                "color": {
                                    "rgbColor": self._hex_to_rgb(background_color)
                                }
                            }
                        }
                    },
                    "fields": "pageBackgroundFill.solidFill.color",
                }
            }
        return None

    def _process_chart_element(
        self,
        presentation_id: str,
        slide_id: str,
        chart_element: dict[str, Any],
        element_id: str,
    ) -> dict[str, Any]:
        """Process a chart element by creating sheet, chart, and embedding into slide"""

        from google_workspace_mcp.services.drive import DriveService
        from google_workspace_mcp.services.sheets_service import SheetsService

        try:
            sheets_service = SheetsService()
            drive_service = DriveService()

            # Extract chart data from element
            content = chart_element.get("content", {})
            chart_type = content.get("chart_type", "BAR")
            data = content.get("data", [])
            title = content.get("title", "Chart")
            position = chart_element.get(
                "position", {"x": 100, "y": 100, "width": 400, "height": 300}
            )

            # Get the dedicated folder for storing data sheets
            data_folder_id = drive_service._get_or_create_data_folder()

            # Create a temporary Google Sheet for the data
            sheet_title = f"[Chart Data] - {title}"
            sheet_result = sheets_service.create_spreadsheet(title=sheet_title)
            if not sheet_result or sheet_result.get("error"):
                raise RuntimeError(
                    f"Failed to create data sheet: {sheet_result.get('message') if sheet_result else 'No result'}"
                )

            spreadsheet_id = sheet_result["spreadsheet_id"]

            # Move the new sheet to the correct folder and remove it from root
            drive_service.service.files().update(
                fileId=spreadsheet_id,
                addParents=data_folder_id,
                removeParents="root",
                fields="id, parents",
            ).execute()
            logger.info(f"Moved data sheet {spreadsheet_id} to folder {data_folder_id}")

            # Write the data to the temporary sheet
            num_rows = len(data)
            num_cols = len(data[0]) if data else 0
            if num_rows == 0 or num_cols < 2:
                raise ValueError(
                    "Data must have at least one header row and one data column."
                )

            range_a1 = f"Sheet1!A1:{chr(ord('A') + num_cols - 1)}{num_rows}"
            write_result = sheets_service.write_range(spreadsheet_id, range_a1, data)
            if not write_result or write_result.get("error"):
                raise RuntimeError(
                    f"Failed to write data to sheet: {write_result.get('message') if write_result else 'No result'}"
                )

            # Get sheet metadata to get numeric sheet ID
            metadata = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
            if not metadata or not metadata.get("sheets"):
                raise RuntimeError(
                    "Failed to get spreadsheet metadata or no sheets found"
                )
            sheet_id_numeric = metadata["sheets"][0]["properties"]["sheetId"]

            # Map user-friendly chart type to API-specific chart type
            chart_type_upper = chart_type.upper()
            if chart_type_upper in ["BAR", "COLUMN"]:
                api_chart_type = "COLUMN"
            elif chart_type_upper == "PIE":
                api_chart_type = "PIE_CHART"
            else:
                api_chart_type = chart_type_upper

            # Create the chart object within the sheet
            chart_result = sheets_service.create_chart_on_sheet(
                spreadsheet_id,
                sheet_id_numeric,
                api_chart_type,
                num_rows,
                num_cols,
                title,
            )
            if not chart_result or chart_result.get("error"):
                raise RuntimeError(
                    f"Failed to create chart in sheet: {chart_result.get('message') if chart_result else 'No result'}"
                )
            chart_id = chart_result["chartId"]

            # Embed the chart into the Google Slide
            embed_result = self.embed_sheets_chart(
                presentation_id,
                slide_id,
                spreadsheet_id,
                chart_id,
                position=(position.get("x", 100), position.get("y", 100)),
                size=(position.get("width", 400), position.get("height", 300)),
            )
            if not embed_result or embed_result.get("error"):
                raise RuntimeError(
                    f"Failed to embed chart into slide: {embed_result.get('message') if embed_result else 'No result'}"
                )

            return {
                "success": True,
                "message": f"Successfully processed chart '{title}'",
                "element_id": element_id,
                "chart_element_id": embed_result.get("element_id"),
                "spreadsheet_id": spreadsheet_id,
                "chart_id": chart_id,
            }

        except Exception as e:
            logger.error(
                f"Chart processing failed for element {element_id}: {e}", exc_info=True
            )
            return {
                "error": True,
                "message": f"Chart processing failed: {e}",
                "element_id": element_id,
            }

    def embed_sheets_chart(
        self,
        presentation_id: str,
        slide_id: str,
        spreadsheet_id: str,
        chart_id: int,
        position: tuple[float, float],
        size: tuple[float, float],
    ) -> dict[str, Any]:
        """
        Embeds a chart from Google Sheets into a Google Slides presentation.

        Args:
            presentation_id: The ID of the presentation.
            slide_id: The ID of the slide to add the chart to.
            spreadsheet_id: The ID of the Google Sheet containing the chart.
            chart_id: The ID of the chart within the sheet.
            position: Tuple of (x, y) coordinates for position in PT.
            size: Tuple of (width, height) for the chart size in PT.

        Returns:
            The API response from the batchUpdate call.
        """
        try:
            element_id = f"chart_{chart_id}_{int(__import__('time').time() * 1000)}"
            logger.info(
                f"Embedding chart {chart_id} from sheet {spreadsheet_id} into slide {slide_id}"
            )

            requests = [
                {
                    "createSheetsChart": {
                        "objectId": element_id,
                        "spreadsheetId": spreadsheet_id,
                        "chartId": chart_id,
                        "linkingMode": "LINKED",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": size[0], "unit": "PT"},
                                "height": {"magnitude": size[1], "unit": "PT"},
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
            ]

            response = self.batch_update(presentation_id, requests)
            if response.get("error"):
                raise ValueError(
                    response.get("message", "Batch update for chart embedding failed")
                )

            created_element_id = (
                response.get("replies", [{}])[0]
                .get("createSheetsChart", {})
                .get("objectId")
            )

            return {
                "success": True,
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "element_id": created_element_id or element_id,
            }

        except Exception as e:
            return self.handle_api_error("embed_sheets_chart", e)

    def _is_private_drive_url(self, url: str) -> bool:
        """Check if URL is a private Google Drive URL by trying to extract an ID."""
        return self._extract_drive_file_id(url) is not None

    def _extract_drive_file_id(self, url: str) -> str | None:
        """Extract Drive file ID from various Google Drive URL formats."""
        # This regex is designed to be robust and capture the ID from multiple common URL patterns
        # e.g., /file/d/FILE_ID/edit, /uc?id=FILE_ID, /open?id=FILE_ID
        patterns = [
            r"/file/d/([a-zA-Z0-9-_]+)",
            r"id=([a-zA-Z0-9-_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                # Return the first captured group
                return match.group(1)

        # If no pattern matches, it's not a recognizable Drive URL
        return None

    def _convert_private_image_to_public(
        self, image_url: str, converted_images_list: list
    ) -> str:
        """
        Convert a private Google Drive image to public access and track it for later reversion.

        Args:
            image_url: The original image URL (private Drive URL)
            converted_images_list: List to track file IDs that were converted to public

        Returns:
            The public Drive URL that can be used in Slides API
        """
        try:
            # Extract Drive file ID from the URL
            file_id = self._extract_drive_file_id(image_url)
            if not file_id:
                logger.warning(f"Could not extract file ID from URL: {image_url}")
                return image_url  # Return original URL if not a Drive URL

            # Make the file public using DriveService
            drive_service = DriveService()
            result = drive_service.share_file_publicly(file_id, role="reader")

            if result.get("success"):
                # Track this file for later reversion to private
                converted_images_list.append(
                    {
                        "file_id": file_id,
                        "permission_id": result.get("permission_id"),
                        "original_url": image_url,
                    }
                )

                # Return the public Drive URL
                public_url = f"https://drive.google.com/uc?id={file_id}"
                logger.info(
                    f"Successfully converted private image to public: {file_id}"
                )
                return public_url
            logger.error(f"Failed to make file public: {result}")
            return image_url  # Return original URL on failure

        except Exception as e:
            logger.error(f"Error converting private image to public: {e}")
            return image_url  # Return original URL on error

    def _revert_images_to_private(self, converted_images: list) -> None:
        """
        Revert all converted images back to private by removing their public permissions.

        Args:
            converted_images: List of image data that were converted to public
        """
        if not converted_images:
            return

        logger.info(f"Reverting {len(converted_images)} images back to private")
        drive_service = DriveService()

        for image_data in converted_images:
            try:
                file_id = image_data.get("file_id")
                permission_id = image_data.get("permission_id")

                if file_id and permission_id:
                    # Remove the public permission
                    drive_service.service.permissions().delete(
                        fileId=file_id,
                        permissionId=permission_id,
                        supportsAllDrives=True,
                    ).execute()
                    logger.info(f"Successfully reverted image to private: {file_id}")
                else:
                    logger.warning(
                        f"Missing file_id or permission_id for image: {image_data}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to revert image {image_data.get('file_id')} to private: {e}"
                )
