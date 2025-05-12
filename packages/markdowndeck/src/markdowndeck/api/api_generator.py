"""Generator for Google Slides API requests."""

import logging
import uuid
from typing import Any

from markdowndeck.models import (
    AlignmentType,
    CodeElement,
    Deck,
    Element,
    ElementType,
    ImageElement,
    ListElement,
    Slide,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
)

logger = logging.getLogger(__name__)


class ApiRequestGenerator:
    """Generates Google Slides API requests from the Intermediate Representation."""

    def __init__(self):
        """Initialize the request generator."""
        logger.debug("Initializing API request generator")

    def generate_batch_requests(self, deck: Deck, presentation_id: str) -> list[dict]:
        """
        Generate all batch requests needed to create a presentation.

        Args:
            deck: The presentation deck
            presentation_id: The presentation ID

        Returns:
            List of batch request dictionaries
        """
        batches = []

        for i, slide in enumerate(deck.slides):
            slide_requests = []
            current_batch = {"presentationId": presentation_id, "requests": []}

            # Create the slide
            create_slide_request = self._create_slide_request(slide)
            slide_requests.append(create_slide_request)

            # Add slide notes if present
            if slide.notes:
                notes_request = self._create_notes_request(slide)
                slide_requests.append(notes_request)

            # Add elements to the slide
            for element in slide.elements:
                if (
                    (hasattr(element, "element_type") and element.element_type == ElementType.TITLE)
                    or (
                        hasattr(element, "element_type")
                        and element.element_type == ElementType.SUBTITLE
                    )
                    or (
                        hasattr(element, "element_type")
                        and element.element_type == ElementType.TEXT
                    )
                    or (
                        hasattr(element, "element_type")
                        and element.element_type == ElementType.FOOTER
                    )
                ):
                    requests = self._generate_text_element_requests(element, f"p.{i}")
                    slide_requests.extend(requests)
                elif (
                    hasattr(element, "element_type")
                    and element.element_type == ElementType.BULLET_LIST
                ):
                    requests = self._generate_list_element_requests(
                        element, f"p.{i}", "BULLET_DISC_CIRCLE_SQUARE"
                    )
                    slide_requests.extend(requests)
                elif (
                    hasattr(element, "element_type")
                    and element.element_type == ElementType.ORDERED_LIST
                ):
                    requests = self._generate_list_element_requests(
                        element, f"p.{i}", "NUMBERED_DIGIT_ALPHA_ROMAN"
                    )
                    slide_requests.extend(requests)
                elif hasattr(element, "element_type") and element.element_type == ElementType.IMAGE:
                    requests = self._generate_image_element_requests(element, f"p.{i}")
                    slide_requests.extend(requests)
                elif hasattr(element, "element_type") and element.element_type == ElementType.TABLE:
                    requests = self._generate_table_element_requests(element, f"p.{i}")
                    slide_requests.extend(requests)
                elif hasattr(element, "element_type") and element.element_type == ElementType.CODE:
                    requests = self._generate_code_element_requests(element, f"p.{i}")
                    slide_requests.extend(requests)
                elif hasattr(element, "element_type") and element.element_type == ElementType.QUOTE:
                    requests = self._generate_quote_element_requests(element, f"p.{i}")
                    slide_requests.extend(requests)

            # Set slide background if present
            if slide.background:
                background_request = self._create_background_request(slide)
                slide_requests.append(background_request)

            current_batch["requests"] = slide_requests
            batches.append(current_batch)

        logger.info(f"Generated {len(batches)} batch requests")
        return batches

    def generate_slide_batch(self, slide: Slide, presentation_id: str) -> dict:
        """
        Generate a batch of requests for a single slide.

        Args:
            slide: The slide to generate requests for
            presentation_id: The presentation ID

        Returns:
            Dictionary with presentationId and requests
        """
        requests = []

        # Create the slide
        slide_request = self._create_slide_request(slide)
        requests.append(slide_request)

        # Set slide background if present
        if slide.background:
            background_request = self._create_background_request(slide)
            requests.append(background_request)

        # For each element, generate appropriate requests
        for element in slide.elements:
            element_requests = self._generate_element_requests(element, slide.object_id)
            requests.extend(element_requests)

        # Add speaker notes if present
        if slide.notes:
            note_request = self._create_notes_request(slide)
            requests.append(note_request)

        logger.debug(f"Generated {len(requests)} requests for slide {slide.object_id}")
        return {"presentationId": presentation_id, "requests": requests}

    def _create_slide_request(self, slide: Slide) -> dict:
        """
        Create a request to add a new slide with the specified layout.

        Args:
            slide: The slide to create

        Returns:
            Dictionary with the create slide request
        """
        # Generate a unique ID for the slide if not present
        if not slide.object_id:
            slide.object_id = self._generate_id("slide")

        # Create the slide request
        request = {
            "createSlide": {
                "objectId": slide.object_id,
                "slideLayoutReference": {"predefinedLayout": slide.layout.value},
                "placeholderIdMappings": [],
            }
        }

        logger.debug(
            f"Created slide request with ID: {slide.object_id}, layout: {slide.layout.value}"
        )
        return request

    def _create_background_request(self, slide: Slide) -> dict:
        """
        Create a request to set the slide background.

        Args:
            slide: The slide to set background for

        Returns:
            Dictionary with the update slide background request
        """
        if not slide.background:
            return {}

        background_type = slide.background.get("type")
        background_value = slide.background.get("value")

        request = {
            "updateSlideProperties": {
                "objectId": slide.object_id,
                "fields": "slideProperties.backgroundFill",
                "slideProperties": {"backgroundFill": {}},
            }
        }

        if background_type == "color":
            # Handle color backgrounds
            if background_value.startswith("#"):
                # Convert hex to RGB
                rgb = self._hex_to_rgb(background_value)
                request["updateSlideProperties"]["slideProperties"]["backgroundFill"] = {
                    "solidFill": {"color": {"opaqueColor": {"rgbColor": rgb}}}
                }
            else:
                # Named colors
                request["updateSlideProperties"]["slideProperties"]["backgroundFill"] = {
                    "solidFill": {
                        "color": {"opaqueColor": {"themeColor": background_value.upper()}}
                    }
                }
        elif background_type == "image":
            # Handle image backgrounds
            request["updateSlideProperties"]["slideProperties"]["backgroundFill"] = {
                "stretchedPictureFill": {"pictureId": background_value}
            }

        logger.debug(f"Created background request for slide: {slide.object_id}")
        return request

    def _generate_element_requests(self, element: Element, slide_id: str) -> list[dict]:
        """
        Generate requests for a specific element.

        Args:
            element: The element to generate requests for
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        if not element.object_id:
            element.object_id = self._generate_id(str(element.element_type.value))

        # Handle text elements
        if element.element_type == ElementType.TEXT:
            return self._generate_text_element_requests(element, slide_id)

        # Handle title element
        if element.element_type == ElementType.TITLE:
            return self._generate_text_element_requests(element, slide_id)

        # Handle subtitle element
        if element.element_type == ElementType.SUBTITLE:
            return self._generate_text_element_requests(element, slide_id)

        # Handle footer element
        if element.element_type == ElementType.FOOTER:
            return self._generate_footer_element_requests(element, slide_id)

        # Handle bullet list element
        if element.element_type == ElementType.BULLET_LIST:
            return self._generate_list_element_requests(
                element, slide_id, bullet_type="BULLET_DISC_CIRCLE_SQUARE"
            )

        # Handle ordered list element
        if element.element_type == ElementType.ORDERED_LIST:
            return self._generate_list_element_requests(
                element, slide_id, bullet_type="NUMBERED_DIGIT_ALPHA_ROMAN"
            )

        if element.element_type == ElementType.IMAGE:
            return self._generate_image_element_requests(element, slide_id)

        if element.element_type == ElementType.TABLE:
            return self._generate_table_element_requests(element, slide_id)

        if element.element_type == ElementType.CODE:
            return self._generate_code_element_requests(element, slide_id)

        if element.element_type == ElementType.QUOTE:
            return self._generate_quote_element_requests(element, slide_id)

        logger.warning(f"Unknown element type: {element.element_type}")
        return []

    def _generate_text_element_requests(self, element: TextElement, slide_id: str) -> list[dict]:
        """
        Generate requests for a text element (title, subtitle, or paragraph).

        Args:
            element: The text element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 50))

        # Create shape
        create_shape_request = {
            "createShape": {
                "objectId": element.object_id,
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
        }
        requests.append(create_shape_request)

        # Insert text
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": element.text,
            }
        }
        requests.append(insert_text_request)

        # Apply text formatting if present
        if hasattr(element, "formatting") and element.formatting:
            for text_format in element.formatting:
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style=self._format_to_style(text_format),
                    fields=self._format_to_fields(text_format),
                    start_index=text_format.start,
                    end_index=text_format.end,
                )
                requests.append(style_request)

        # Apply paragraph style if this is a title or subtitle
        if element.element_type in (ElementType.TITLE, ElementType.SUBTITLE):
            paragraph_style = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": "CENTER",
                    },
                    "fields": "alignment",
                }
            }
            requests.append(paragraph_style)
        # Apply horizontal alignment if specified and this is not a title/subtitle
        elif hasattr(element, "horizontal_alignment") and element.horizontal_alignment:
            alignment_map = {
                AlignmentType.LEFT: "START",
                AlignmentType.CENTER: "CENTER",
                AlignmentType.RIGHT: "END",
                AlignmentType.JUSTIFY: "JUSTIFIED",
            }
            api_alignment = alignment_map.get(element.horizontal_alignment, "START")

            paragraph_style = {
                "updateParagraphStyle": {
                    "objectId": element.object_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": api_alignment,
                    },
                    "fields": "alignment",
                }
            }
            requests.append(paragraph_style)

        # Apply custom styling from directives
        if hasattr(element, "directives") and element.directives and "color" in element.directives:
            # Apply text color if specified
            color_value = element.directives["color"]

            # Handle both string and tuple color values
            if isinstance(color_value, tuple) and len(color_value) == 2:
                # If it's a tuple, extract the color type and value
                color_type, color_value = color_value
                # Only proceed if it's a color directive with a hex value
                if color_type != "color" or not isinstance(color_value, str):
                    color_value = None

            # Now we have either a string color_value or None
            if isinstance(color_value, str) and color_value.startswith("#"):
                rgb = self._hex_to_rgb(color_value)
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"foregroundColor": {"opaqueColor": {"rgbColor": rgb}}},
                    fields="foregroundColor",
                    range_type="ALL",
                )
                requests.append(style_request)

        # Apply font size if specified
        if (
            hasattr(element, "directives")
            and element.directives
            and "fontsize" in element.directives
        ):
            font_size = element.directives["fontsize"]
            if isinstance(font_size, int | float):
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"fontSize": {"magnitude": font_size, "unit": "PT"}},
                    fields="fontSize",
                    range_type="ALL",
                )
                requests.append(style_request)

        # Apply background color if specified
        if (
            hasattr(element, "directives")
            and element.directives
            and "background" in element.directives
        ):
            background_directive = element.directives["background"]
            # Check if the directive is the tuple format from DirectiveParser
            if isinstance(background_directive, tuple) and len(background_directive) == 2:
                bg_type, bg_value = background_directive
                # Check if it's a color and the value is a string starting with #
                if bg_type == "color" and isinstance(bg_value, str) and bg_value.startswith("#"):
                    try:
                        rgb = self._hex_to_rgb(bg_value)
                        # Generate the API request to update the shape's background fill
                        shape_properties_request = {
                            "updateShapeProperties": {
                                "objectId": element.object_id,
                                # Use the correct field mask for shape background fill color
                                "fields": "shapeProperties.shapeBackgroundFill.solidFill.color",
                                "shapeProperties": {
                                    "shapeBackgroundFill": {
                                        "solidFill": {"color": {"opaqueColor": {"rgbColor": rgb}}}
                                    }
                                },
                            }
                        }
                        requests.append(shape_properties_request)
                        logger.debug(
                            f"Generated background color request for element {element.object_id}"
                        )
                    except ValueError as e:
                        logger.warning(
                            f"Invalid hex color '{bg_value}' for background directive: {e}"
                        )

        return requests

    def _generate_list_element_requests(
        self, element: ListElement, slide_id: str, bullet_type: str
    ) -> list[dict]:
        """
        Generate requests for a list element (bulleted or numbered).

        Args:
            element: The list element
            slide_id: The slide ID
            bullet_type: The type of bullets to use

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Create shape
        create_shape_request = {
            "createShape": {
                "objectId": element.object_id,
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
        }
        requests.append(create_shape_request)

        # Prepare text with line breaks
        list_text = ""
        text_ranges = []  # Track the range of each item for formatting
        current_index = 0

        def process_item(item, level=0):
            nonlocal list_text, current_index

            # Add indentation based on level
            indent = "    " * level
            item_text = f"{indent}{item.text}\n"

            # Track the range of this item in the final text
            start_index = current_index + len(indent)
            end_index = start_index + len(item.text)
            text_ranges.append((item, start_index, end_index))

            # Add to the full text
            list_text += item_text
            current_index += len(item_text)

            # Process children recursively
            for child in item.children:
                process_item(child, level + 1)

        # Process all items
        for item in element.items:
            process_item(item)

        # Insert the text
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": list_text,
            }
        }
        requests.append(insert_text_request)

        # Apply bullet formatting
        bullet_request = {
            "createParagraphBullets": {
                "objectId": element.object_id,
                "textRange": {"type": "ALL"},
                "bulletPreset": bullet_type,
            }
        }
        requests.append(bullet_request)

        # Apply text formatting for each item
        for item, start, _end in text_ranges:
            if hasattr(item, "formatting") and item.formatting:
                for text_format in item.formatting:
                    # Adjust start and end indices relative to the item's position
                    adjusted_start = start + text_format.start
                    adjusted_end = start + text_format.end

                    style_request = self._apply_text_formatting(
                        element_id=element.object_id,
                        style=self._format_to_style(text_format),
                        fields=self._format_to_fields(text_format),
                        start_index=adjusted_start,
                        end_index=adjusted_end,
                    )
                    requests.append(style_request)

        # Apply custom styling from directives
        if hasattr(element, "directives") and element.directives and "color" in element.directives:
            # Apply text color if specified
            color_value = element.directives["color"]

            # Handle both string and tuple color values
            if isinstance(color_value, tuple) and len(color_value) == 2:
                # If it's a tuple, extract the color type and value
                color_type, color_value = color_value
                # Only proceed if it's a color directive with a hex value
                if color_type != "color" or not isinstance(color_value, str):
                    color_value = None

            # Now we have either a string color_value or None
            if isinstance(color_value, str) and color_value.startswith("#"):
                rgb = self._hex_to_rgb(color_value)
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"foregroundColor": {"opaqueColor": {"rgbColor": rgb}}},
                    fields="foregroundColor",
                    range_type="ALL",
                )
                requests.append(style_request)

        return requests

    def _generate_image_element_requests(self, element: ImageElement, slide_id: str) -> list[dict]:
        """
        Generate requests for an image element.

        Args:
            element: The image element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (300, 200))

        # Create image
        create_image_request = {
            "createImage": {
                "objectId": element.object_id,
                "url": element.url,
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
        requests.append(create_image_request)

        # Add alt text if present
        if element.alt_text:
            alt_text_request = {
                "updateImageProperties": {
                    "objectId": element.object_id,
                    "fields": "imageProperties.description",
                    "imageProperties": {"description": element.alt_text},
                }
            }
            requests.append(alt_text_request)

        return requests

    def _generate_table_element_requests(self, element: TableElement, slide_id: str) -> list[dict]:
        """
        Generate requests for a table element.

        Args:
            element: The table element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Create table
        row_count = len(element.rows) + (1 if element.headers else 0)
        col_count = max(
            len(element.headers) if element.headers else 0,
            max(len(row) for row in element.rows) if element.rows else 0,
        )

        create_table_request = {
            "createTable": {
                "objectId": element.object_id,
                "rows": row_count,
                "columns": col_count,
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
        requests.append(create_table_request)

        # Insert header text if present
        row_index = 0
        if element.headers:
            for col_index, header in enumerate(element.headers):
                if col_index < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": row_index,
                                "columnIndex": col_index,
                            },
                            "text": header,
                            "insertionIndex": 0,
                        }
                    }
                    requests.append(insert_text_request)

            # Set header style (bold)
            for col_index in range(min(len(element.headers), col_count)):
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"bold": True},
                    fields="bold",
                    range_type="ALL",
                    cell_location={
                        "rowIndex": row_index,
                        "columnIndex": col_index,
                    },
                )
                requests.append(style_request)

                # Add cell fill for header
                fill_request = {
                    "updateTableCellProperties": {
                        "objectId": element.object_id,
                        "tableRange": {
                            "location": {
                                "rowIndex": row_index,
                                "columnIndex": col_index,
                            },
                            "rowSpan": 1,
                            "columnSpan": 1,
                        },
                        "tableCellProperties": {
                            "tableCellBackgroundFill": {
                                "solidFill": {
                                    "color": {
                                        "rgbColor": {
                                            "red": 0.95,
                                            "green": 0.95,
                                            "blue": 0.95,
                                        }
                                    }
                                }
                            }
                        },
                        "fields": "tableCellProperties.tableCellBackgroundFill.solidFill.color",
                    }
                }
                requests.append(fill_request)

            row_index += 1

        # Insert row text
        for row_idx, row in enumerate(element.rows):
            for col_idx, cell in enumerate(row):
                if col_idx < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": row_idx + row_index,
                                "columnIndex": col_idx,
                            },
                            "text": cell,
                            "insertionIndex": 0,
                        }
                    }
                    requests.append(insert_text_request)

        # Apply table styles if specified in directives
        if hasattr(element, "directives") and element.directives and "border" in element.directives:
            # Apply border style to all cells
            border_style_request = {
                "updateTableBorderProperties": {
                    "objectId": element.object_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": row_count,
                        "columnSpan": col_count,
                    },
                    "borderPosition": "ALL",
                    "tableBorderProperties": {
                        "weight": {
                            "magnitude": 1,
                            "unit": "PT",
                        },
                        "dashStyle": "SOLID",
                    },
                    "fields": "tableBorderProperties.weight,tableBorderProperties.dashStyle",
                }
            }
            requests.append(border_style_request)

        return requests

    def _generate_code_element_requests(self, element: CodeElement, slide_id: str) -> list[dict]:
        """
        Generate requests for a code element.

        Args:
            element: The code element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 150))

        # Create shape
        create_shape_request = {
            "createShape": {
                "objectId": element.object_id,
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
        }
        requests.append(create_shape_request)

        # Insert code text
        insert_text_request = {
            "insertText": {
                "objectId": element.object_id,
                "insertionIndex": 0,
                "text": element.code,
            }
        }
        requests.append(insert_text_request)

        # Add code formatting (monospace font, background)
        style_request = self._apply_text_formatting(
            element_id=element.object_id,
            style={
                "fontFamily": "Courier New",
                "backgroundColor": {
                    "opaqueColor": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
                },
            },
            fields="fontFamily,backgroundColor",
            range_type="ALL",
        )
        requests.append(style_request)

        # Add shape background
        shape_background_request = {
            "updateShapeProperties": {
                "objectId": element.object_id,
                "fields": "shapeProperties.shapeBackgroundFill.solidFill.color",
                "shapeProperties": {
                    "shapeBackgroundFill": {
                        "solidFill": {
                            "color": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
                        }
                    }
                },
            }
        }
        requests.append(shape_background_request)

        # Add language label if specified
        if element.language and element.language != "text":
            # Create label shape
            label_id = f"{element.object_id}_label"
            create_label_request = {
                "createShape": {
                    "objectId": label_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 80, "unit": "PT"},
                            "height": {"magnitude": 20, "unit": "PT"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": position[0],
                            "translateY": position[1] - 20,  # Above code block
                            "unit": "PT",
                        },
                    },
                }
            }
            requests.append(create_label_request)

            # Insert label text
            insert_label_request = {
                "insertText": {
                    "objectId": label_id,
                    "insertionIndex": 0,
                    "text": element.language,
                }
            }
            requests.append(insert_label_request)

            # Style label
            style_label_request = self._apply_text_formatting(
                element_id=label_id,
                style={
                    "fontFamily": "Arial",
                    "fontSize": {"magnitude": 10, "unit": "PT"},
                    "foregroundColor": {
                        "opaqueColor": {"rgbColor": {"red": 0.3, "green": 0.3, "blue": 0.3}}
                    },
                },
                fields="fontFamily,fontSize,foregroundColor",
                range_type="ALL",
            )
            requests.append(style_label_request)

            # Center text in label
            center_label_request = {
                "updateParagraphStyle": {
                    "objectId": label_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "alignment": "CENTER",
                    },
                    "fields": "alignment",
                }
            }
            requests.append(center_label_request)

        return requests

    def _generate_quote_element_requests(self, element: TextElement, slide_id: str) -> list[dict]:
        """
        Generate requests for a quote element.

        Args:
            element: The quote element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        # Similar to text element but with special formatting
        requests = self._generate_text_element_requests(element, slide_id)

        # Add blockquote styling
        style_request = self._apply_text_formatting(
            element_id=element.object_id,
            style={
                "italic": True,
                "fontFamily": "Georgia",
            },
            fields="italic,fontFamily",
            range_type="ALL",
        )
        requests.append(style_request)

        # Add indentation
        paragraph_style = {
            "updateParagraphStyle": {
                "objectId": element.object_id,
                "textRange": {"type": "ALL"},
                "style": {
                    "indentStart": {
                        "magnitude": 36,
                        "unit": "PT",
                    },
                    "indentEnd": {
                        "magnitude": 36,
                        "unit": "PT",
                    },
                },
                "fields": "indentStart,indentEnd",
            }
        }
        requests.append(paragraph_style)

        return requests

    def _generate_footer_element_requests(self, element: TextElement, slide_id: str) -> list[dict]:
        """
        Generate requests for a footer element.

        Args:
            element: The footer element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        # Similar to text element but with special positioning and style
        requests = self._generate_text_element_requests(element, slide_id)

        # Add footer styling
        style_request = self._apply_text_formatting(
            element_id=element.object_id,
            style={
                "fontSize": {"magnitude": 10, "unit": "PT"},
                "foregroundColor": {
                    "opaqueColor": {"rgbColor": {"red": 0.5, "green": 0.5, "blue": 0.5}}
                },
            },
            fields="fontSize,foregroundColor",
            range_type="ALL",
        )
        requests.append(style_request)

        return requests

    def _create_notes_request(self, slide: Slide) -> dict:
        """
        Create a request to add notes to a slide.

        Args:
            slide: The slide to add notes to

        Returns:
            Dictionary with the update speaker notes request
        """
        return {
            "updateSlideProperties": {
                "objectId": slide.object_id,
                "slideProperties": {
                    "notesPage": {"notesProperties": {"speakerNotesText": slide.notes}}
                },
                "fields": "notesPage.notesProperties.speakerNotesText",
            }
        }

    def _apply_text_formatting(
        self,
        element_id: str,
        style: dict[str, Any],
        fields: str,
        range_type: str = None,
        start_index: int = None,
        end_index: int = None,
        cell_location: dict[str, int] = None,
    ) -> dict:
        """
        Helper method to create properly formatted text style requests.

        Args:
            element_id: ID of the element to update
            style: Style dictionary to apply
            fields: Fields to update
            range_type: Type of range (e.g., "ALL") or None for specific indices
            start_index: Start index for specific range
            end_index: End index for specific range
            cell_location: Location of a cell in a table (dict with rowIndex and columnIndex)

        Returns:
            Dictionary with the update text style request
        """
        # Safety check - prevent accidental mixing of range_type with indices
        if range_type and (start_index is not None or end_index is not None):
            logger.warning(
                f"Mixed text range specification detected: range_type={range_type} with "
                f"start_index={start_index}, end_index={end_index}. Defaulting to range_type only."
            )
            # Force indices to None to avoid mixing
            start_index = None
            end_index = None

        request = {
            "updateTextStyle": {
                "objectId": element_id,
                "style": style,
                "fields": fields,
            }
        }

        # We need to be explicit and never mix type and indices in the textRange
        # The Google Slides API treats unspecified type as RANGE_TYPE_UNSPECIFIED
        # which causes conflicts if indices are also present
        if range_type:
            # Use type-based range (e.g., "ALL")
            request["updateTextStyle"]["textRange"] = {"type": range_type}
        elif start_index is not None and end_index is not None:
            # Use index-based range, with explicit FIXED_RANGE type
            request["updateTextStyle"]["textRange"] = {
                "type": "FIXED_RANGE",
                "startIndex": start_index,
                "endIndex": end_index,
            }
        else:
            # Default to ALL if neither is specified
            request["updateTextStyle"]["textRange"] = {"type": "ALL"}

        # Add cell location for table text styling if provided
        if cell_location:
            request["updateTextStyle"]["tableRange"] = {
                "location": cell_location,
                "rowSpan": 1,
                "columnSpan": 1,
            }

        return request

    def _format_to_style(self, text_format: TextFormat) -> dict[str, Any]:
        """
        Convert TextFormat to Google Slides TextStyle.

        Args:
            text_format: The text format

        Returns:
            Dictionary with the style
        """
        style = {}

        if text_format.format_type == TextFormatType.BOLD:
            style["bold"] = True
        elif text_format.format_type == TextFormatType.ITALIC:
            style["italic"] = True
        elif text_format.format_type == TextFormatType.UNDERLINE:
            style["underline"] = True
        elif text_format.format_type == TextFormatType.STRIKETHROUGH:
            style["strikethrough"] = True
        elif text_format.format_type == TextFormatType.CODE:
            # For inline code, use a monospace font and light gray background
            style["fontFamily"] = "Courier New"
            style["backgroundColor"] = {
                "opaqueColor": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}
            }
        elif text_format.format_type == TextFormatType.LINK:
            style["link"] = {"url": text_format.value}
        elif text_format.format_type == TextFormatType.COLOR:
            # Handle color values that may be strings or tuples
            color_value = text_format.value

            # Handle tuple color value
            if isinstance(color_value, tuple) and len(color_value) == 2:
                color_type, color_value = color_value
                # Only proceed if it's a color directive with a hex value
                if color_type != "color" or not isinstance(color_value, str):
                    return style  # Return without adding color if invalid

            # Apply string color value
            if isinstance(color_value, str) and color_value.startswith("#"):
                rgb = self._hex_to_rgb(color_value)
                style["foregroundColor"] = {"opaqueColor": {"rgbColor": rgb}}

        return style

    def _format_to_fields(self, text_format: TextFormat) -> str:
        """
        Convert TextFormat to fields string for updateTextStyle.

        Args:
            text_format: The text format

        Returns:
            String with the fields to update
        """
        if text_format.format_type == TextFormatType.BOLD:
            return "bold"
        if text_format.format_type == TextFormatType.ITALIC:
            return "italic"
        if text_format.format_type == TextFormatType.UNDERLINE:
            return "underline"
        if text_format.format_type == TextFormatType.STRIKETHROUGH:
            return "strikethrough"
        if text_format.format_type == TextFormatType.CODE:
            return "fontFamily,backgroundColor"
        if text_format.format_type == TextFormatType.LINK:
            return "link"
        if text_format.format_type == TextFormatType.COLOR:
            return "foregroundColor"

        return ""

    def _generate_id(self, prefix: str = "") -> str:
        """
        Generate a unique ID string.

        Args:
            prefix: Optional prefix for the ID

        Returns:
            String with the generated ID
        """
        if prefix:
            return f"{prefix}_{uuid.uuid4().hex[:8]}"
        return uuid.uuid4().hex[:8]

    def _hex_to_rgb(self, hex_color: str) -> dict[str, float]:
        """
        Convert hex color to RGB values for Google Slides API.

        Args:
            hex_color: Hex color string (e.g., "#FF5733")

        Returns:
            Dictionary with red, green, blue values between 0-1
        """
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Handle shorthand hex
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])

        # Convert to RGB
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        return {"red": r, "green": g, "blue": b}
