"""
Slides tools for Google Slides operations.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.slides import SlidesService

logger = logging.getLogger(__name__)


# --- Slides Tool Functions --- #


@mcp.tool(
    name="get_presentation",
    description="Get a presentation by ID with its metadata and content.",
)
async def get_presentation(presentation_id: str) -> dict[str, Any]:
    """
    Get presentation information including all slides and content.

    Args:
        presentation_id: The ID of the presentation.

    Returns:
        Presentation data dictionary or raises error.
    """
    logger.info(f"Executing get_presentation tool with ID: '{presentation_id}'")
    if not presentation_id or not presentation_id.strip():
        raise ValueError("Presentation ID is required")

    slides_service = SlidesService()
    result = slides_service.get_presentation(presentation_id=presentation_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error getting presentation"))

    # Return raw service result
    return result


@mcp.tool(
    name="get_slides",
    description="Retrieves all slides from a presentation with their elements and notes.",
)
async def get_slides(presentation_id: str) -> dict[str, Any]:
    """
    Retrieves all slides from a presentation.

    Args:
        presentation_id: The ID of the presentation.

    Returns:
        A dictionary containing the list of slides or an error message.
    """
    logger.info(f"Executing get_slides tool from presentation: '{presentation_id}'")
    if not presentation_id or not presentation_id.strip():
        raise ValueError("Presentation ID is required")

    slides_service = SlidesService()
    slides = slides_service.get_slides(presentation_id=presentation_id)

    if isinstance(slides, dict) and slides.get("error"):
        raise ValueError(slides.get("message", "Error getting slides"))

    if not slides:
        return {"message": "No slides found in this presentation."}

    # Return raw service result
    return {"count": len(slides), "slides": slides}


@mcp.tool(
    name="create_presentation",
    description="Creates a new Google Slides presentation with the specified title.",
)
async def create_presentation(
    title: str,
    delete_default_slide: bool = False,
) -> dict[str, Any]:
    """
    Create a new presentation.

    Args:
        title: The title for the new presentation.
        delete_default_slide: If True, deletes the default slide created by Google Slides API.

    Returns:
        Created presentation data or raises error.
    """
    logger.info(
        f"Executing create_presentation with title: '{title}', delete_default_slide: {delete_default_slide}"
    )
    if not title or not title.strip():
        raise ValueError("Presentation title cannot be empty")

    slides_service = SlidesService()
    result = slides_service.create_presentation(title=title)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating presentation"))

    # If requested, delete the default slide
    if delete_default_slide and result.get("presentationId"):
        # Get the first slide ID and delete it
        presentation_data = slides_service.get_presentation(
            presentation_id=result["presentationId"]
        )
        if presentation_data.get("slides") and len(presentation_data["slides"]) > 0:
            first_slide_id = presentation_data["slides"][0]["objectId"]
            delete_result = slides_service.delete_slide(
                presentation_id=result["presentationId"], slide_id=first_slide_id
            )
            if isinstance(delete_result, dict) and delete_result.get("error"):
                logger.warning(
                    f"Failed to delete default slide: {delete_result.get('message')}"
                )
            else:
                logger.info("Successfully deleted default slide")

    return result


@mcp.tool(
    name="create_slide",
    description="Adds a new slide to a Google Slides presentation with a specified layout.",
)
async def create_slide(
    presentation_id: str,
    layout: str = "BLANK",
) -> dict[str, Any]:
    """
    Add a new slide to a presentation.

    Args:
        presentation_id: The ID of the presentation.
        layout: The layout for the new slide (e.g., TITLE_AND_BODY, TITLE_ONLY, BLANK).

    Returns:
        Response data confirming slide creation or raises error.
    """
    logger.info(
        f"Executing create_slide in presentation '{presentation_id}' with layout '{layout}'"
    )
    if not presentation_id or not presentation_id.strip():
        raise ValueError("Presentation ID cannot be empty")
    # Optional: Validate layout against known predefined layouts?

    slides_service = SlidesService()
    result = slides_service.create_slide(presentation_id=presentation_id, layout=layout)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating slide"))

    return result


# @mcp.tool(
#     name="add_text_to_slide",
#     description="Adds text to a specified slide in a Google Slides presentation.",
# )
async def add_text_to_slide(
    presentation_id: str,
    slide_id: str,
    text: str,
    shape_type: str = "TEXT_BOX",
    position_x: float = 100.0,
    position_y: float = 100.0,
    size_width: float = 400.0,
    size_height: float = 100.0,
) -> dict[str, Any]:
    """
    Add text to a slide by creating a text box.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        text: The text content to add.
        shape_type: Type of shape (default TEXT_BOX). Must be 'TEXT_BOX'.
        position_x: X coordinate for position (default 100.0 PT).
        position_y: Y coordinate for position (default 100.0 PT).
        size_width: Width of the text box (default 400.0 PT).
        size_height: Height of the text box (default 100.0 PT).

    Returns:
        Response data confirming text addition or raises error.
    """
    logger.info(f"Executing add_text_to_slide on slide '{slide_id}'")
    if not presentation_id or not slide_id or text is None:
        raise ValueError("Presentation ID, Slide ID, and Text are required")

    # Validate shape_type
    valid_shape_types = {"TEXT_BOX"}
    if shape_type not in valid_shape_types:
        raise ValueError(
            f"Invalid shape_type '{shape_type}' provided. Must be one of {valid_shape_types}."
        )

    slides_service = SlidesService()
    result = slides_service.add_text(
        presentation_id=presentation_id,
        slide_id=slide_id,
        text=text,
        shape_type=shape_type,
        position=(position_x, position_y),
        size=(size_width, size_height),
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding text to slide"))

    return result


# @mcp.tool(
#     name="add_formatted_text_to_slide",
#     description="Adds rich-formatted text (with bold, italic, etc.) to a slide.",
# )
async def add_formatted_text_to_slide(
    presentation_id: str,
    slide_id: str,
    text: str,
    position_x: float = 100.0,
    position_y: float = 100.0,
    size_width: float = 400.0,
    size_height: float = 100.0,
) -> dict[str, Any]:
    """
    Add formatted text to a slide with markdown-style formatting.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        text: The text content with formatting (use ** for bold, * for italic).
        position_x: X coordinate for position (default 100.0 PT).
        position_y: Y coordinate for position (default 100.0 PT).
        size_width: Width of the text box (default 400.0 PT).
        size_height: Height of the text box (default 100.0 PT).

    Returns:
        Response data confirming text addition or raises error.
    """
    logger.info(f"Executing add_formatted_text_to_slide on slide '{slide_id}'")
    if not presentation_id or not slide_id or text is None:
        raise ValueError("Presentation ID, Slide ID, and Text are required")

    slides_service = SlidesService()
    result = slides_service.add_formatted_text(
        presentation_id=presentation_id,
        slide_id=slide_id,
        formatted_text=text,
        position=(position_x, position_y),
        size=(size_width, size_height),
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding formatted text to slide"))

    return result


# @mcp.tool(
#     name="add_bulleted_list_to_slide",
#     description="Adds a bulleted list to a slide in a Google Slides presentation.",
# )
async def add_bulleted_list_to_slide(
    presentation_id: str,
    slide_id: str,
    items: list[str],
    position_x: float = 100.0,
    position_y: float = 100.0,
    size_width: float = 400.0,
    size_height: float = 200.0,
) -> dict[str, Any]:
    """
    Add a bulleted list to a slide.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        items: List of bullet point text items.
        position_x: X coordinate for position (default 100.0 PT).
        position_y: Y coordinate for position (default 100.0 PT).
        size_width: Width of the text box (default 400.0 PT).
        size_height: Height of the text box (default 200.0 PT).

    Returns:
        Response data confirming list addition or raises error.
    """
    logger.info(f"Executing add_bulleted_list_to_slide on slide '{slide_id}'")
    if not presentation_id or not slide_id or not items:
        raise ValueError("Presentation ID, Slide ID, and Items are required")

    slides_service = SlidesService()
    result = slides_service.add_bulleted_list(
        presentation_id=presentation_id,
        slide_id=slide_id,
        items=items,
        position=(position_x, position_y),
        size=(size_width, size_height),
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding bulleted list to slide"))

    return result


@mcp.tool(
    name="add_image_to_slide",
    description="Adds a single image to a slide from a publicly accessible URL with smart sizing. For creating complete slides with multiple elements, use create_slide_with_elements instead for better performance. For full-height coverage, only specify size_height. For full-width coverage, only specify size_width. For exact dimensions, specify both.",
)
async def add_image_to_slide(
    presentation_id: str,
    slide_id: str,
    image_url: str,
    position_x: float = 100.0,
    position_y: float = 100.0,
    size_width: float | None = None,
    size_height: float | None = None,
    unit: str = "PT",
) -> dict[str, Any]:
    """
    Add an image to a slide from a publicly accessible URL.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        image_url: The publicly accessible URL of the image to add.
        position_x: X coordinate for position (default 100.0).
        position_y: Y coordinate for position (default 100.0).
        size_width: Optional width of the image. If not specified, uses original size or scales proportionally with height.
        size_height: Optional height of the image. If not specified, uses original size or scales proportionally with width.
        unit: Unit type - "PT" for points or "EMU" for English Metric Units (default "PT").

    Returns:
        Response data confirming image addition or raises error.

    Note:
        Image Sizing Best Practices:
        - For full-height coverage: Only specify size_height parameter
        - For full-width coverage: Only specify size_width parameter
        - For exact dimensions: Specify both size_height and size_width
        - Omitting a dimension allows proportional auto-scaling while maintaining aspect ratio
    """
    logger.info(
        f"Executing add_image_to_slide on slide '{slide_id}' with image '{image_url}'"
    )
    logger.info(f"Position: ({position_x}, {position_y}) {unit}")
    if size_width and size_height:
        logger.info(f"Size: {size_width} x {size_height} {unit}")

    if not presentation_id or not slide_id or not image_url:
        raise ValueError("Presentation ID, Slide ID, and Image URL are required")

    # Basic URL validation
    if not image_url.startswith(("http://", "https://")):
        raise ValueError("Image URL must be a valid HTTP or HTTPS URL")

    # Validate unit
    if unit not in ["PT", "EMU"]:
        raise ValueError(
            "Unit must be either 'PT' (points) or 'EMU' (English Metric Units)"
        )

    slides_service = SlidesService()

    # Prepare size parameter
    size = None
    if size_width is not None and size_height is not None:
        size = (size_width, size_height)

    # Use the enhanced add_image method with unit support
    result = slides_service.add_image_with_unit(
        presentation_id=presentation_id,
        slide_id=slide_id,
        image_url=image_url,
        position=(position_x, position_y),
        size=size,
        unit=unit,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding image to slide"))

    return result


@mcp.tool(
    name="add_table_to_slide",
    description="Adds a table to a slide in a Google Slides presentation.",
)
async def add_table_to_slide(
    presentation_id: str,
    slide_id: str,
    rows: int,
    columns: int,
    data: list[list[str]],
    position_x: float = 100.0,
    position_y: float = 100.0,
    size_width: float = 400.0,
    size_height: float = 200.0,
) -> dict[str, Any]:
    """
    Add a table to a slide.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        rows: Number of rows in the table.
        columns: Number of columns in the table.
        data: 2D array of strings containing table data.
        position_x: X coordinate for position (default 100.0 PT).
        position_y: Y coordinate for position (default 100.0 PT).
        size_width: Width of the table (default 400.0 PT).
        size_height: Height of the table (default 200.0 PT).

    Returns:
        Response data confirming table addition or raises error.
    """
    logger.info(f"Executing add_table_to_slide on slide '{slide_id}'")
    if not presentation_id or not slide_id:
        raise ValueError("Presentation ID and Slide ID are required")

    if rows < 1 or columns < 1:
        raise ValueError("Rows and columns must be positive integers")

    if len(data) > rows or any(len(row) > columns for row in data):
        raise ValueError("Data dimensions exceed specified table size")

    slides_service = SlidesService()
    result = slides_service.add_table(
        presentation_id=presentation_id,
        slide_id=slide_id,
        rows=rows,
        columns=columns,
        data=data,
        position=(position_x, position_y),
        size=(size_width, size_height),
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding table to slide"))

    return result


# @mcp.tool(
#     name="add_slide_notes",
#     description="Adds presenter notes to a slide in a Google Slides presentation.",
# )
async def add_slide_notes(
    presentation_id: str,
    slide_id: str,
    notes: str,
) -> dict[str, Any]:
    """
    Add presenter notes to a slide.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        notes: The notes content to add.

    Returns:
        Response data confirming notes addition or raises error.
    """
    logger.info(f"Executing add_slide_notes on slide '{slide_id}'")
    if not presentation_id or not slide_id or not notes:
        raise ValueError("Presentation ID, Slide ID, and Notes are required")

    slides_service = SlidesService()
    result = slides_service.add_slide_notes(
        presentation_id=presentation_id,
        slide_id=slide_id,
        notes_text=notes,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error adding notes to slide"))

    return result


@mcp.tool(
    name="duplicate_slide",
    description="Duplicates a slide in a Google Slides presentation.",
)
async def duplicate_slide(
    presentation_id: str,
    slide_id: str,
    insert_at_index: int | None = None,
) -> dict[str, Any]:
    """
    Duplicate a slide in a presentation.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide to duplicate.
        insert_at_index: Optional index where to insert the duplicated slide.

    Returns:
        Response data with the new slide ID or raises error.
    """
    logger.info(f"Executing duplicate_slide for slide '{slide_id}'")
    if not presentation_id or not slide_id:
        raise ValueError("Presentation ID and Slide ID are required")

    slides_service = SlidesService()
    result = slides_service.duplicate_slide(
        presentation_id=presentation_id,
        slide_id=slide_id,
        insert_at_index=insert_at_index,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error duplicating slide"))

    return result


@mcp.tool(
    name="delete_slide",
    description="Deletes a slide from a Google Slides presentation.",
)
async def delete_slide(
    presentation_id: str,
    slide_id: str,
) -> dict[str, Any]:
    """
    Delete a slide from a presentation.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide to delete.

    Returns:
        Response data confirming slide deletion or raises error.
    """
    logger.info(
        f"Executing delete_slide: slide '{slide_id}' from presentation '{presentation_id}'"
    )
    if not presentation_id or not slide_id:
        raise ValueError("Presentation ID and Slide ID are required")

    slides_service = SlidesService()
    result = slides_service.delete_slide(
        presentation_id=presentation_id, slide_id=slide_id
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error deleting slide"))

    return result


# @mcp.tool(
#     name="create_presentation_from_markdown",
#     description="Creates a Google Slides presentation from structured Markdown content with enhanced formatting support using markdowndeck.",
# )
async def create_presentation_from_markdown(
    title: str,
    markdown_content: str,
) -> dict[str, Any]:
    """
    Create a Google Slides presentation from Markdown using the markdowndeck library.

    Args:
        title: The title for the new presentation.
        markdown_content: Markdown content structured for slides.

    Returns:
        Created presentation data or raises error.
    """
    logger.info(f"Executing create_presentation_from_markdown with title '{title}'")
    if (
        not title
        or not title.strip()
        or not markdown_content
        or not markdown_content.strip()
    ):
        raise ValueError("Title and markdown content are required")

    slides_service = SlidesService()
    result = slides_service.create_presentation_from_markdown(
        title=title, markdown_content=markdown_content
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            result.get("message", "Error creating presentation from Markdown")
        )

    return result


@mcp.tool(
    name="create_textbox_with_text",
    description="Creates a single text box with text content, font formatting, and alignment. For creating complete slides with multiple elements, use create_slide_with_elements instead for better performance. Good for adding individual text boxes to existing slides.",
)
async def create_textbox_with_text(
    presentation_id: str,
    slide_id: str,
    text: str,
    position_x: float,
    position_y: float,
    size_width: float,
    size_height: float,
    unit: str = "EMU",
    element_id: str | None = None,
    font_family: str = "Arial",
    font_size: float = 12,
    text_alignment: str | None = None,
    vertical_alignment: str | None = None,
) -> dict[str, Any]:
    """
    Create a text box with text, font formatting, and alignment.

    Args:
        presentation_id: The ID of the presentation.
        slide_id: The ID of the slide.
        text: The text content to insert.
        position_x: X coordinate for position.
        position_y: Y coordinate for position.
        size_width: Width of the text box.
        size_height: Height of the text box.
        unit: Unit type - "PT" for points or "EMU" for English Metric Units (default "EMU").
        element_id: Optional custom element ID, auto-generated if not provided.
        font_family: Font family (e.g., "Playfair Display", "Roboto", "Arial").
        font_size: Font size in points (e.g., 25, 7.5).
        text_alignment: Optional horizontal alignment ("LEFT", "CENTER", "RIGHT", "JUSTIFY").
        vertical_alignment: Optional vertical alignment ("TOP", "MIDDLE", "BOTTOM").

    Returns:
        Response data confirming text box creation or raises error.
    """
    logger.info(f"Executing create_textbox_with_text on slide '{slide_id}'")
    if not presentation_id or not slide_id or text is None:
        raise ValueError("Presentation ID, Slide ID, and Text are required")

    slides_service = SlidesService()
    result = slides_service.create_textbox_with_text(
        presentation_id=presentation_id,
        slide_id=slide_id,
        text=text,
        position=(position_x, position_y),
        size=(size_width, size_height),
        unit=unit,
        element_id=element_id,
        font_family=font_family,
        font_size=font_size,
        text_alignment=text_alignment,
        vertical_alignment=vertical_alignment,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating text box with text"))

    return result


@mcp.tool(
    name="slides_batch_update",
    description="Apply a list of raw Google Slides API update requests to a presentation in a single batch operation. Allows creating multiple elements (text boxes, images, shapes) efficiently in one API call instead of multiple individual calls.",
)
async def slides_batch_update(
    presentation_id: str,
    requests: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Apply a list of raw Google Slides API update requests to a presentation.
    For advanced users familiar with Slides API request structures.

    Args:
        presentation_id: The ID of the presentation
        requests: List of Google Slides API request objects (e.g., createShape, insertText, updateTextStyle, createImage, etc.)

    Returns:
        Response data confirming batch operation or raises error

    Example request structure:
    [
        {
            "createShape": {
                "objectId": "textbox1",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": "slide_id",
                    "size": {"width": {"magnitude": 300, "unit": "PT"}, "height": {"magnitude": 50, "unit": "PT"}},
                    "transform": {"translateX": 100, "translateY": 100, "unit": "PT"}
                }
            }
        },
        {
            "insertText": {
                "objectId": "textbox1",
                "text": "Hello World"
            }
        }
    ]
    """
    logger.info(f"Executing slides_batch_update with {len(requests)} requests")
    if not presentation_id or not requests:
        raise ValueError("Presentation ID and requests list are required")

    if not isinstance(requests, list):
        raise ValueError("Requests must be a list of API request objects")

    slides_service = SlidesService()
    result = slides_service.batch_update(
        presentation_id=presentation_id, requests=requests
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error executing batch update"))

    return result


@mcp.tool(
    name="create_slide_from_template_data",
    description="Create a complete slide with multiple elements (title, description, stats, image) in a single batch operation. Much faster than individual API calls - reduces 15+ calls to 1 call.",
)
async def create_slide_from_template_data(
    presentation_id: str,
    slide_id: str,
    template_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a complete slide from template data in a single batch operation.

    Args:
        presentation_id: The ID of the presentation
        slide_id: The ID of the slide
        template_data: Dictionary containing slide elements, example:
            {
                "title": {
                    "text": "Frank's RedHot Campaign",
                    "position": {"x": 32, "y": 35, "width": 330, "height": 40},
                    "style": {"fontSize": 18, "fontFamily": "Roboto"}
                },
                "description": {
                    "text": "Campaign description...",
                    "position": {"x": 32, "y": 95, "width": 330, "height": 160},
                    "style": {"fontSize": 12, "fontFamily": "Roboto"}
                },
                "stats": [
                    {"value": "43.4M", "label": "TOTAL IMPRESSIONS", "position": {"x": 374.5, "y": 268.5}},
                    {"value": "134K", "label": "TOTAL ENGAGEMENTS", "position": {"x": 516.5, "y": 268.5}},
                    {"value": "4.8B", "label": "AGGREGATE READERSHIP", "position": {"x": 374.5, "y": 350.5}},
                    {"value": "$9.1M", "label": "AD EQUIVALENCY", "position": {"x": 516.5, "y": 350.5}}
                ],
                "image": {
                    "url": "https://images.unsplash.com/...",
                    "position": {"x": 375, "y": 35},
                    "size": {"width": 285, "height": 215}
                }
            }

    Returns:
        Response data confirming slide creation or raises error
    """
    logger.info(f"Executing create_slide_from_template_data on slide '{slide_id}'")
    if not presentation_id or not slide_id or not template_data:
        raise ValueError("Presentation ID, Slide ID, and Template Data are required")

    if not isinstance(template_data, dict):
        raise ValueError("Template data must be a dictionary")

    slides_service = SlidesService()
    result = slides_service.create_slide_from_template_data(
        presentation_id=presentation_id, slide_id=slide_id, template_data=template_data
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(
            result.get("message", "Error creating slide from template data")
        )

    return result


@mcp.tool(
    name="create_slide_with_elements",
    description="Create a complete slide with multiple elements (text boxes, images) in a single batch operation. Generic approach that treats all content as positioned elements. Perfect for creating template-based slides efficiently.",
)
async def create_slide_with_elements(
    presentation_id: str,
    slide_id: str,
    elements: list[dict[str, Any]],
    background_color: str | None = None,
) -> dict[str, Any]:
    """
    Create a complete slide with multiple elements in one batch operation.

    Args:
        presentation_id: The ID of the presentation
        slide_id: The ID of the slide
        elements: List of element dictionaries, example:
            [
                {
                    "type": "textbox",
                    "content": "Slide Title",
                    "position": {"x": 282, "y": 558, "width": 600, "height": 45},
                    "style": {"fontSize": 25, "fontFamily": "Playfair Display", "bold": True, "textAlignment": "CENTER", "verticalAlignment": "MIDDLE"}
                },
                {
                    "type": "textbox",
                    "content": "Description text...",
                    "position": {"x": 282, "y": 1327, "width": 600, "height": 234},
                    "style": {"fontSize": 12, "fontFamily": "Roboto"}
                },
                {
                    "type": "textbox",
                    "content": "43.4M",
                    "position": {"x": 333, "y": 4059, "width": 122, "height": 79},
                    "style": {"fontSize": 25, "fontFamily": "Playfair Display", "bold": True}
                },
                {
                    "type": "image",
                    "content": "https://drive.google.com/file/d/.../view",
                    "position": {"x": 675, "y": 0, "width": 238, "height": 514}
                }
            ]
        background_color: Optional slide background color (e.g., "#f8cdcd4f")

    Returns:
        Response data confirming slide creation or raises error
    """
    logger.info(
        f"Executing create_slide_with_elements on slide '{slide_id}' with {len(elements)} elements"
    )
    if not presentation_id or not slide_id or not elements:
        raise ValueError("Presentation ID, Slide ID, and Elements are required")

    if not isinstance(elements, list):
        raise ValueError("Elements must be a list")

    slides_service = SlidesService()
    result = slides_service.create_slide_with_elements(
        presentation_id=presentation_id,
        slide_id=slide_id,
        elements=elements,
        background_color=background_color,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating slide with elements"))

    return result


@mcp.tool(
    name="convert_template_zones_to_pt",
    description="Convert template zones from EMU coordinates to PT coordinates for easier usage in slide creation. Simplifies coordinate handling for LLM.",
)
async def convert_template_zones_to_pt(
    template_zones: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert template zones coordinates from EMU to PT for easier slide element creation.

    Args:
        template_zones: Template zones from extract_template_zones_only

    Returns:
        Template zones with additional PT coordinates (x_pt, y_pt, width_pt, height_pt)
    """
    logger.info(f"Converting {len(template_zones)} template zones to PT coordinates")
    if not template_zones:
        raise ValueError("Template zones are required")

    slides_service = SlidesService()
    result = slides_service.convert_template_zones_to_pt(template_zones)

    return {"success": True, "converted_zones": result}


@mcp.tool(
    name="update_text_formatting",
    description="Updates formatting of text in an existing text box with support for bold, italic, code formatting, font size, font family, and text alignment. Supports applying different formatting to specific text ranges within the same textbox.",
)
async def update_text_formatting(
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
    Update formatting of text in an existing text box.

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
    logger.info(f"Executing update_text_formatting on element '{element_id}'")
    if not presentation_id or not element_id or not formatted_text:
        raise ValueError("Presentation ID, Element ID, and Formatted Text are required")

    slides_service = SlidesService()
    result = slides_service.update_text_formatting(
        presentation_id=presentation_id,
        element_id=element_id,
        formatted_text=formatted_text,
        font_size=font_size,
        font_family=font_family,
        text_alignment=text_alignment,
        vertical_alignment=vertical_alignment,
        start_index=start_index,
        end_index=end_index,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error updating text formatting"))

    return result
