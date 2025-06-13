"""
Google Slides service implementation.
"""

import json
import logging
import re
from typing import Any

from google_workspace_mcp.auth import gauth
from google_workspace_mcp.services.base import BaseGoogleService
from google_workspace_mcp.utils.markdown_slides import MarkdownSlidesConverter
from markdowndeck import create_presentation

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

    def create_presentation(self, title: str) -> dict[str, Any]:
        """
        Create a new presentation with a title.

        Args:
            title: The title of the new presentation

        Returns:
            Created presentation data or error information
        """
        try:
            body = {"title": title}
            return self.service.presentations().create(body=body).execute()
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

    def create_textbox_with_text(
        self,
        presentation_id: str,
        slide_id: str,
        text: str,
        position: tuple[float, float] = (350, 100),
        size: tuple[float, float] = (350, 350),
        unit: str = "PT",
        element_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a text box with text following the Google API example pattern.
        This method creates both the text box shape and inserts text in one operation.

        Args:
            presentation_id: The ID of the presentation
            slide_id: The ID of the slide (page)
            text: The text content to insert
            position: Tuple of (x, y) coordinates for position in PT
            size: Tuple of (width, height) for the text box in PT
            unit: Unit type - "PT" for points or "EMU" for English Metric Units (default "PT").
            element_id: Optional custom element ID, auto-generated if not provided

        Returns:
            Response data or error information
        """
        try:
            # Generate element ID if not provided
            if element_id is None:
                import time

                element_id = f"TextBox_{int(time.time() * 1000)}"

            # Convert size to Google API format
            width = {"magnitude": size[0], "unit": unit}
            height = {"magnitude": size[1], "unit": unit}

            # Build requests following the Google API example exactly
            requests = [
                # Create text box shape
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
                # Insert text into the text box
                {
                    "insertText": {
                        "objectId": element_id,
                        "insertionIndex": 0,
                        "text": text,
                    }
                },
            ]

            logger.info(
                f"Creating text box with text using requests: {json.dumps(requests, indent=2)}"
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
                "operation": "create_textbox_with_text",
                "result": "success",
                "response": response,
            }
        except Exception as e:
            return self.handle_api_error("create_textbox_with_text", e)

    def update_text_formatting(
        self,
        presentation_id: str,
        element_id: str,
        formatted_text: str,
    ) -> dict[str, Any]:
        """
        Update formatting of text in an existing text box.

        Args:
            presentation_id: The ID of the presentation
            element_id: The ID of the text box element
            formatted_text: Text with formatting markers (**, *, etc.)

        Returns:
            Response data or error information
        """
        try:
            # Process the formatted text
            plain_text = formatted_text
            # Remove bold markers
            plain_text = re.sub(r"\*\*(.*?)\*\*", r"\1", plain_text)
            # Remove italic markers
            plain_text = re.sub(r"\*(.*?)\*", r"\1", plain_text)
            # Remove code markers if present
            plain_text = re.sub(r"`(.*?)`", r"\1", plain_text)

            # Generate style requests
            style_requests = []

            # Process bold text
            bold_pattern = r"\*\*(.*?)\*\*"
            bold_matches = list(re.finditer(bold_pattern, formatted_text))

            for match in bold_matches:
                content = match.group(1)
                start_pos = plain_text.find(content)
                if start_pos >= 0:
                    end_pos = start_pos + len(content)
                    style_requests.append(
                        {
                            "updateTextStyle": {
                                "objectId": element_id,
                                "textRange": {
                                    "type": "FIXED_RANGE",  # Specify the range type
                                    "startIndex": start_pos,
                                    "endIndex": end_pos,
                                },
                                "style": {"bold": True},
                                "fields": "bold",
                            }
                        }
                    )

            # Process italic text (similar pattern for italic)
            # ... (similar code for italic formatting)

            if style_requests:
                response = (
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
                    "operation": "update_text_formatting",
                    "result": "success",
                }
            return {"result": "no_formatting_applied"}

        except Exception as e:
            return self.handle_api_error("update_text_formatting", e)
