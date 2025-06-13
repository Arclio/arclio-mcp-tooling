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

                api_alignment = alignment_map.get(text_alignment.upper())
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

                api_valign = valign_map.get(vertical_alignment.upper())
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
