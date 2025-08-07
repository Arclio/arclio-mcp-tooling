"""
Slides tools for Google Slides operations.
"""

import logging
from typing import Any

from google_workspace_mcp.app import mcp  # Import from central app module
from google_workspace_mcp.services.drive import DriveService
from google_workspace_mcp.services.sheets_service import SheetsService
from google_workspace_mcp.services.slides import SlidesService

logger = logging.getLogger(__name__)


# --- Slides Tool Functions --- #


# @mcp.tool(
#     name="get_presentation",
# )
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


# @mcp.tool(
#     name="get_slides",
#     description="Retrieves all slides from a presentation with their elements and notes.",
# )
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
)
async def create_presentation(
    title: str,
    parent_folder_id: str | None | bool = None,
    shared_drive_id: str | None | bool = None,
    delete_default_slide: bool = False,
) -> dict[str, Any]:
    """
    Create a new presentation, optionally in a specific folder.

    Args:
        title: The title for the new presentation.
        parent_folder_id: Optional parent folder ID to create the presentation within.
        shared_drive_id: Optional shared drive ID to create the presentation in a shared drive.
        delete_default_slide: If True, deletes the default slide created by Google Slides API.

    Returns:
        Created presentation data or raises error.
    """
    # Convert False/empty values to None for proper handling
    parent_folder_id_clean: str | None = None
    shared_drive_id_clean: str | None = None

    if parent_folder_id and parent_folder_id is not False and parent_folder_id != "":
        parent_folder_id_clean = str(parent_folder_id)
    if shared_drive_id and shared_drive_id is not False and shared_drive_id != "":
        shared_drive_id_clean = str(shared_drive_id)

    logger.info(
        f"Executing create_presentation with title: '{title}', parent_folder_id: {parent_folder_id_clean}, "
        f"shared_drive_id: {shared_drive_id_clean}, delete_default_slide: {delete_default_slide}"
    )
    if not title or not title.strip():
        raise ValueError("Presentation title cannot be empty")

    slides_service = SlidesService()
    result = slides_service.create_presentation(
        title=title,
        parent_folder_id=parent_folder_id_clean,
        shared_drive_id=shared_drive_id_clean,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating presentation"))

    # Extract essential information
    presentation_id = result.get("presentationId")
    if not presentation_id:
        raise ValueError("Failed to get presentation ID from creation result")

        # Prepare clean response
    clean_result = {
        "presentationId": presentation_id,
        "title": title,
        "status": "created_successfully",
        "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
    }

    # Add folder information and move status if applicable
    if parent_folder_id_clean:
        clean_result["parent_folder_id"] = parent_folder_id_clean
    if shared_drive_id_clean:
        clean_result["shared_drive_id"] = shared_drive_id_clean

    # Include folder move status
    folder_move_status = result.get("folder_move_status")
    if folder_move_status:
        if folder_move_status.get("success"):
            clean_result["folder_placement"] = "successful"
            clean_result["moved_to_folder_id"] = folder_move_status.get(
                "moved_to_folder_id"
            )
        else:
            clean_result["folder_placement"] = "failed"
            clean_result["folder_error"] = folder_move_status.get("error")
    elif parent_folder_id_clean or shared_drive_id_clean:
        # Folder was requested but no status found - this shouldn't happen
        clean_result["folder_placement"] = "unknown"

    # If requested, delete the default slide
    if delete_default_slide and presentation_id:
        # Get the first slide ID and delete it
        presentation_data = slides_service.get_presentation(
            presentation_id=presentation_id
        )
        if presentation_data.get("slides") and len(presentation_data["slides"]) > 0:
            first_slide_id = presentation_data["slides"][0]["objectId"]
            delete_result = slides_service.delete_slide(
                presentation_id=presentation_id, slide_id=first_slide_id
            )
            if isinstance(delete_result, dict) and delete_result.get("error"):
                logger.warning(
                    f"Failed to delete default slide: {delete_result.get('message')}"
                )
                clean_result["default_slide_deleted"] = False
                clean_result["delete_error"] = delete_result.get("message")
            else:
                logger.info("Successfully deleted default slide")
                clean_result["default_slide_deleted"] = True
                clean_result["status"] = "created_successfully_no_default_slide"
        else:
            clean_result["default_slide_deleted"] = False
            clean_result["delete_error"] = "No slides found to delete"

    return clean_result


# @mcp.tool(
#     name="create_slide",
#     description="Adds a new slide to a Google Slides presentation with a specified layout.",
# )
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


# @mcp.tool(
#     name="add_image_to_slide",
#     description="Adds a single image to a slide from a publicly accessible URL with smart sizing. For creating complete slides with multiple elements, use create_slide_with_elements instead for better performance. For full-height coverage, only specify size_height. For full-width coverage, only specify size_width. For exact dimensions, specify both.",
# )
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


# @mcp.tool(
#     name="add_table_to_slide",
#     description="Adds a table to a slide in a Google Slides presentation.",
# )
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


# @mcp.tool(
#     name="duplicate_slide",
# )
async def duplicate_slide(
    presentation_id: str,
    slide_id: str,
    insert_at_index: int | None = None,
) -> dict[str, Any]:
    """
    Duplicate a slide in a presentation.

    Args:
        presentation_id: The ID of the presentation where the new slide will be created.
        slide_id: The ID of the slide to duplicate.
        insert_at_index: Optional index where to insert the duplicated slide.

    Crucial Note: The slide_id MUST belong to the SAME presentation specified by presentation_id.
    You cannot duplicate a slide from one presentation into another using this tool.

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


# @mcp.tool(
#     name="delete_slide",
# )
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


# @mcp.tool(
#     name="create_textbox_with_text",
# )
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


# @mcp.tool(
#     name="slides_batch_update",
# )
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


# @mcp.tool(
#     name="create_slide_from_template_data",
# )
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
                    "text": "John's Company Campaign",
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


# @mcp.tool(
#     name="create_slide_with_elements",
# )
async def create_slide_with_elements(
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
    Create a complete slide with multiple elements in one batch operation.
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
                    "content": "Description text...",
                    "position": {"x": 282, "y": 1327, "width": 600, "height": 234},
                    "style": {
                        "fontSize": 12,
                        "fontFamily": "Roboto",
                        "color": "#000000",  # Black text (alternative to textColor)
                        "foregroundColor": "#333333"  # Dark gray text (alternative to textColor/color)
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

    Text Color Support:
        - "textColor" or "color": "#FFFFFF"
        - "foregroundColor": "#333333"
        - Supports 6-character and 8-character hex codes with alpha: "#FFFFFF", "#FFFFFF80"
        - Supports CSS rgba() format: "rgba(255, 255, 255, 0.5)"
        - Supports RGB objects: {"r": 255, "g": 255, "b": 255} or {"red": 1.0, "green": 1.0, "blue": 1.0}

    Background Color Support:
        - "backgroundColor": "#FFFFFF80" - Semi-transparent white background
        - "backgroundColor": "rgba(255, 255, 255, 0.5)" - Semi-transparent white background (CSS format)
        - Supports same color formats as text colors
        - 8-character hex codes supported: "#FFFFFF80" (alpha channel properly applied)
        - CSS rgba() format supported: "rgba(255, 255, 255, 0.5)" (alpha channel properly applied)
        - CSS rgb() format supported: "rgb(255, 255, 255)" (fully opaque)
        - Works in main "style" object for entire text box background
        - Creates semi-transparent background for the entire text box shape

    Background Image Requirements:
        - Maximum file size: 50 MB
        - Maximum resolution: 25 megapixels
        - Supported formats: PNG, JPEG, GIF only
        - HTTPS URLs recommended
        - Will automatically stretch to fill slide (may distort aspect ratio)

    Advanced textRanges formatting:
        For mixed formatting within a single textbox, use "textRanges" instead of "style":
        - textRanges: Array of formatting ranges - now supports TWO formats:

        FORMAT 1 - Content-based (RECOMMENDED - no index calculation needed):
        "textRanges": [
            {"content": "43.4M", "style": {"fontSize": 25, "bold": true}},
            {"content": "TOTAL IMPRESSIONS", "style": {"fontSize": 7.5}}
        ]

        FORMAT 2 - Index-based (legacy support):
        "textRanges": [
            {"startIndex": 0, "endIndex": 5, "style": {"fontSize": 25, "bold": true}},
            {"startIndex": 6, "endIndex": 23, "style": {"fontSize": 7.5}}
        ]

        - Content-based ranges automatically find text and calculate indices
        - Index-based ranges include auto-correction for common off-by-one errors
        - Allows different fonts, sizes, colors, and formatting for different parts of text
        - Perfect for stats with large numbers + small labels in same textbox
        - Each textRange can have its own textColor and backgroundColor

    Table Formatting Best Practices:
        - Use "firstColumnBold": true to emphasize categories/left column
        - Headers: Bold with colored backgrounds (e.g., "#ff6b6b" for brand consistency)
        - Structure: Clear headers with organized data rows

    Chart Element Support:
        - Type: "chart" - Creates and embeds Google Charts from data
        - Content format:
            {
                "chart_type": "BAR" | "LINE" | "PIE" | "COLUMN",
                "data": [["Headers"], ["Row1"], ["Row2"], ...],
                "title": "Chart Title"
            }
        - Supported chart types: BAR, COLUMN (vertical bars), LINE, PIE
        - Data format: First row = headers, subsequent rows = data
        - Position: Standard x, y, width, height in points (PT)
        - Charts automatically create temporary Google Sheets in dedicated folder
        - Charts are theme-aware and integrate with slide design
        - Example:
            {
                "type": "chart",
                "content": {
                    "chart_type": "BAR",
                    "data": [["Month", "Revenue"], ["Jan", 2500], ["Feb", 3100], ["Mar", 2800]],
                    "title": "Monthly Revenue Trend"
                },
                "position": {"x": 100, "y": 400, "width": 480, "height": 320}
            }

    Usage Examples:
        # NEW OPTIMIZED WAY - Single API call to create slide with elements:
        result = await create_slide_with_elements(
            presentation_id="abc123",
            elements=[
                {
                    "type": "textbox",
                    "content": "Slide Title",
                    "position": {"x": 100, "y": 100, "width": 400, "height": 50},
                    "style": {"fontSize": 18, "bold": True, "textColor": "#FFFFFF"}
                },
                {
                    "type": "image",
                    "content": "https://images.unsplash.com/...",
                    "position": {"x": 375, "y": 35, "width": 285, "height": 215}
                }
            ],
            create_slide=True,  # Creates slide AND adds elements
            layout="BLANK",
            background_color="#f8cdcd4f"
        )
        # Returns: {"slideId": "auto_generated_id", "slideCreated": True, "elementsAdded": 2}

        # Add elements to existing slide (original behavior):
        result = await create_slide_with_elements(
            presentation_id="abc123",
            slide_id="existing_slide_123",
            elements=[...],
            create_slide=False  # Only adds elements (default)
        )

        # Create slide without elements (just background):
        result = await create_slide_with_elements(
            presentation_id="abc123",
            create_slide=True,
            background_image_url="https://images.unsplash.com/..."
        )

    Returns:
        Response data confirming slide creation or raises error
    """
    logger.info(
        f"Executing create_slide_with_elements (create_slide={create_slide}, elements={len(elements or [])})"
    )

    if not presentation_id:
        raise ValueError("Presentation ID is required")

    if not create_slide and not slide_id:
        raise ValueError("slide_id is required when create_slide=False")

    if elements and not isinstance(elements, list):
        raise ValueError("Elements must be a list")

    slides_service = SlidesService()
    result = slides_service.create_slide_with_elements(
        presentation_id=presentation_id,
        slide_id=slide_id,
        elements=elements,
        background_color=background_color,
        background_image_url=background_image_url,
        create_slide=create_slide,
        layout=layout,
        insert_at_index=insert_at_index,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating slide with elements"))

    return result


# @mcp.tool(
#     name="set_slide_background",
# )
async def set_slide_background(
    presentation_id: str,
    slide_id: str,
    background_color: str | None = None,
    background_image_url: str | None = None,
) -> dict[str, Any]:
    """
    Set the background of a slide to either a solid color or an image.

    Args:
        presentation_id: The ID of the presentation
        slide_id: The ID of the slide
        background_color: Optional background color (e.g., "#f8cdcd4f", "#ffffff")
        background_image_url: Optional background image URL (takes precedence over color)

    Background Image Requirements:
        - Maximum file size: 50 MB
        - Maximum resolution: 25 megapixels
        - Supported formats: PNG, JPEG, GIF only
        - HTTPS URLs recommended
        - Will automatically stretch to fill entire slide
        - May distort aspect ratio to fit slide dimensions

    Returns:
        Response data confirming background update or raises error
    """
    logger.info(f"Setting background for slide '{slide_id}'")
    if not presentation_id or not slide_id:
        raise ValueError("Presentation ID and Slide ID are required")

    if not background_color and not background_image_url:
        raise ValueError(
            "Either background_color or background_image_url must be provided"
        )

    slides_service = SlidesService()

    # Create the appropriate background request
    if background_image_url:
        logger.info(f"Setting slide background image: {background_image_url}")
        requests = [
            {
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
        ]
    else:
        logger.info(f"Setting slide background color: {background_color}")
        requests = [
            {
                "updatePageProperties": {
                    "objectId": slide_id,
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {
                                "color": {
                                    "rgbColor": slides_service._hex_to_rgb(
                                        background_color or "#ffffff"
                                    )
                                }
                            }
                        }
                    },
                    "fields": "pageBackgroundFill.solidFill.color",
                }
            }
        ]

    result = slides_service.batch_update(presentation_id, requests)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error setting slide background"))

    return result


# @mcp.tool(
#     name="convert_template_zones_to_pt",
# )
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


# @mcp.tool(
#     name="update_text_formatting",
# )
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


@mcp.tool(
    name="create_multiple_slides_with_elements",
)
async def create_multiple_slides_with_elements(
    presentation_id: str,
    slides_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create multiple slides with their elements in a single batch operation.
    PERFECT FOR BULK SLIDE CREATION - eliminates the need for multiple API calls!

    This is the solution you've been looking for! Instead of:
    - await create_slide() x5 calls
    - await create_slide_with_elements() x5 calls
    You can now do everything in ONE batch API call!

    Args:
        presentation_id: The ID of the presentation
        slides_data: List of slide dictionaries, each containing:
            [
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
                            "content": "https://images.unsplash.com/photo-1565299507177-b0ac66763828",
                            "position": {"x": 200, "y": 200, "width": 300, "height": 200}
                        },
                        {
                            "type": "table",
                            "content": {
                                "headers": ["Category", "Value"],
                                "rows": [["Impressions", "43.4M"], ["Engagement", "134K"]]
                            },
                            "position": {"x": 100, "y": 400, "width": 400, "height": 150},
                            "style": {"fontSize": 12, "headerStyle": {"bold": True}}
                        },
                        {
                            "type": "chart",
                            "content": {
                                "chart_type": "PIE",
                                "data": [["Category", "Value"], ["Desktop", 60], ["Mobile", 40]],
                                "title": "Traffic Sources"
                            },
                            "position": {"x": 500, "y": 200, "width": 300, "height": 250}
                        }
                    ]
                },
                {
                    "layout": "TITLE_AND_BODY",
                    "background_color": "#e0e0e0",
                    "elements": [
                        {
                            "type": "textbox",
                            "content": "Slide 2 Content",
                            "position": {"x": 100, "y": 150, "width": 500, "height": 300},
                            "style": {"fontSize": 14, "textAlignment": "LEFT"}
                        }
                    ]
                }
                # ... add up to 3 more slides for a total of 5
            ]

    Returns:
        Response data with all created slide IDs and operation details:
        {
            "slideIds": ["slide_12345_0", "slide_12345_1", ...],
            "slidesCreated": 5,
            "totalRequests": 25,
            "totalElements": 8,
            "result": "success"
        }

    Usage Example - Create 5 slides with elements in ONE API call:
        slides_data = [
            {
                "layout": "BLANK",
                "background_color": "#f0f0f0",
                "elements": [
                    {
                        "type": "textbox",
                        "content": "Campaign Overview",
                        "position": {"x": 100, "y": 100, "width": 600, "height": 80},
                        "style": {"fontSize": 28, "bold": True, "textAlignment": "CENTER"}
                    },
                    {
                        "type": "image",
                        "content": "https://images.unsplash.com/photo-1565299507177-b0ac66763828",
                        "position": {"x": 400, "y": 200, "width": 300, "height": 200}
                    }
                ]
            },
            {
                "layout": "BLANK",
                "elements": [
                    {
                        "type": "textbox",
                        "content": "Key Metrics",
                        "position": {"x": 100, "y": 50, "width": 600, "height": 60},
                        "style": {"fontSize": 24, "bold": True}
                    },
                    {
                        "type": "table",
                        "content": {
                            "headers": ["Metric", "Value"],
                            "rows": [
                                ["Total Impressions", "43.4M"],
                                ["Total Engagements", "134K"],
                                ["Ad Equivalency", "$9.1M"]
                            ]
                        },
                        "position": {"x": 100, "y": 150, "width": 500, "height": 200},
                        "style": {"fontSize": 14, "headerStyle": {"bold": True, "backgroundColor": "#4CAF50"}}
                    }
                ]
            },
            {
                "layout": "BLANK",
                "background_image_url": "https://images.unsplash.com/photo-1557804506-669a67965ba0",
                "elements": [
                    {
                        "type": "textbox",
                        "content": "Results Summary",
                        "position": {"x": 100, "y": 400, "width": 600, "height": 100},
                        "style": {"fontSize": 18, "textColor": "#FFFFFF", "backgroundColor": "#00000080"}
                    }
                ]
            },
            {
                "layout": "BLANK",
                "elements": [
                    {
                        "type": "textbox",
                        "content": "Next Steps",
                        "position": {"x": 100, "y": 100, "width": 600, "height": 400},
                        "style": {"fontSize": 16, "textAlignment": "LEFT"}
                    }
                ]
            },
            {
                "layout": "BLANK",
                "elements": [
                    {
                        "type": "textbox",
                        "content": "Thank You",
                        "position": {"x": 200, "y": 250, "width": 400, "height": 100},
                        "style": {"fontSize": 32, "bold": True, "textAlignment": "CENTER"}
                    }
                ]
            }
        ]

        result = await create_multiple_slides_with_elements(
            presentation_id="your_presentation_id",
            slides_data=slides_data
        )

    Benefits:
        - Reduces from 10+ API calls to 1 API call
        - Much faster execution (3-5x speed improvement)
        - Atomic operation (all slides succeed or all fail)
        - Perfect for creating slide decks programmatically
        - Supports all element types: textbox, image, table
        - Supports slide backgrounds and layouts
    """
    logger.info(f"Creating {len(slides_data)} slides with batch operation")

    if not presentation_id:
        raise ValueError("Presentation ID is required")

    if not slides_data or not isinstance(slides_data, list):
        raise ValueError("slides_data must be a non-empty list of slide dictionaries")

    slides_service = SlidesService()
    result = slides_service.create_multiple_slides_with_elements(
        presentation_id=presentation_id, slides_data=slides_data
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating multiple slides"))

    return result


@mcp.tool(name="share_file")
async def share_file(
    file_id: str,
    sharing_type: str,
    role: str = "reader",
    domain: str | None = None,
    email_address: str | None = None,
    send_notification: bool = True,
) -> dict[str, Any]:
    """
    Shares any Google Drive file (docs, sheets, slides, folders, etc.).

    Args:
        file_id: The ID of the Google Drive file to share.
        sharing_type: Type of sharing ("domain", "user", "public").
        role: Permission role ("reader", "commenter", "writer"). Defaults to "reader".
        domain: Domain name (required for sharing_type="domain").
        email_address: Email address (required for sharing_type="user").
        send_notification: Send email notification for user sharing. Defaults to True.

    Returns:
        Dictionary with sharing confirmation and file link.

    Examples:
        share_file("abc123", "domain", "reader", domain="rizzbuzz.com")
        share_file("abc123", "user", "writer", email_address="user@example.com")
        share_file("abc123", "public", "reader")
    """
    logger.info(
        f"Executing share_file for file ID: '{file_id}', type: '{sharing_type}'"
    )

    if not file_id or not file_id.strip():
        raise ValueError("File ID cannot be empty.")

    # Validate sharing_type
    valid_sharing_types = ["domain", "user", "public"]
    if sharing_type not in valid_sharing_types:
        raise ValueError(
            f"Invalid sharing_type '{sharing_type}'. Must be one of {valid_sharing_types}."
        )

    # Validate role
    valid_roles = ["reader", "commenter", "writer"]
    if role not in valid_roles:
        raise ValueError(f"Invalid role '{role}'. Must be one of {valid_roles}.")

    drive_service = DriveService()

    # Handle different sharing types
    if sharing_type == "domain":
        if not domain or not domain.strip():
            raise ValueError("Domain parameter is required for domain sharing.")

        result = drive_service.share_file_with_domain(
            file_id=file_id, domain=domain, role=role
        )

        if isinstance(result, dict) and result.get("error"):
            raise ValueError(result.get("message", "Failed to share file with domain."))

        return_data = {
            "success": True,
            "message": f"File successfully shared with the '{domain}' domain with '{role}' access.",
            "file_id": file_id,
            "file_link": f"https://drive.google.com/file/d/{file_id}/view",
            "sharing_type": sharing_type,
            "domain": domain,
            "role": role,
        }

    elif sharing_type == "user":
        if not email_address or not email_address.strip():
            raise ValueError("Email address parameter is required for user sharing.")

        result = drive_service.share_file_with_user(
            file_id=file_id,
            email_address=email_address,
            role=role,
            send_notification=send_notification,
        )

        if isinstance(result, dict) and result.get("error"):
            raise ValueError(result.get("message", "Failed to share file with user."))

        return_data = {
            "success": True,
            "message": f"File successfully shared with '{email_address}' with '{role}' access.",
            "file_id": file_id,
            "file_link": f"https://drive.google.com/file/d/{file_id}/view",
            "sharing_type": sharing_type,
            "email_address": email_address,
            "role": role,
            "notification_sent": send_notification,
        }

    elif sharing_type == "public":
        result = drive_service.share_file_publicly(file_id=file_id, role=role)

        if isinstance(result, dict) and result.get("error"):
            raise ValueError(result.get("message", "Failed to share file publicly."))

        return_data = {
            "success": True,
            "message": f"File successfully shared publicly with '{role}' access.",
            "file_id": file_id,
            "file_link": f"https://drive.google.com/file/d/{file_id}/view",
            "sharing_type": sharing_type,
            "access_type": "public",
            "role": role,
        }

    return return_data


# @mcp.tool(name="insert_chart_from_data")
async def insert_chart_from_data(
    presentation_id: str,
    slide_id: str,
    chart_type: str,
    data: list[list[Any]],
    title: str,
    position_x: float = 50.0,
    position_y: float = 50.0,
    size_width: float = 480.0,
    size_height: float = 320.0,
) -> dict[str, Any]:
    """
    Creates and embeds a native, theme-aware Google Chart into a slide from a data table.
    This tool handles the entire process: creating a data sheet in a dedicated Drive folder,
    generating the chart, and embedding it into the slide.

    Supported `chart_type` values:
    - 'BAR': For bar charts. The API creates a vertical column chart.
    - 'LINE': For line charts.
    - 'PIE': For pie charts.
    - 'COLUMN': For vertical column charts (identical to 'BAR').

    Required `data` format:
    The data must be a list of lists, where the first inner list contains the column headers.
    Example: [["Month", "Revenue"], ["Jan", 2500], ["Feb", 3100], ["Mar", 2800]]

    Args:
        presentation_id: The ID of the presentation to add the chart to.
        slide_id: The ID of the slide where the chart will be placed.
        chart_type: The type of chart to create ('BAR', 'LINE', 'PIE', 'COLUMN').
        data: A list of lists containing the chart data, with headers in the first row.
        title: The title that will appear on the chart.
        position_x: The X-coordinate for the chart's top-left corner on the slide (in points).
        position_y: The Y-coordinate for the chart's top-left corner on the slide (in points).
        size_width: The width of the chart on the slide (in points).
        size_height: The height of the chart on the slide (in points).

    Returns:
        A dictionary confirming the chart creation and embedding.
    """
    logger.info(
        f"Executing insert_chart_from_data: type='{chart_type}', title='{title}'"
    )
    sheets_service = SheetsService()
    slides_service = SlidesService()
    drive_service = DriveService()

    spreadsheet_id = None
    try:
        # 1. Get the dedicated folder for storing data sheets
        data_folder_id = drive_service._get_or_create_data_folder()

        # 2. Create a temporary Google Sheet for the data
        sheet_title = f"[Chart Data] - {title}"
        sheet_result = sheets_service.create_spreadsheet(title=sheet_title)
        if not sheet_result:
            raise RuntimeError("Failed to create data sheet: No result returned")
        if sheet_result.get("error"):
            raise RuntimeError(
                f"Failed to create data sheet: {sheet_result.get('message')}"
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

        # 3. Write the data to the temporary sheet
        num_rows = len(data)
        num_cols = len(data[0]) if data else 0
        if num_rows == 0 or num_cols < 2:
            raise ValueError(
                "Data must have at least one header row and one data column."
            )

        range_a1 = f"Sheet1!A1:{chr(ord('A') + num_cols - 1)}{num_rows}"
        write_result = sheets_service.write_range(spreadsheet_id, range_a1, data)
        if not write_result:
            raise RuntimeError("Failed to write data to sheet: No result returned")
        if write_result.get("error"):
            raise RuntimeError(
                f"Failed to write data to sheet: {write_result.get('message')}"
            )

        # 4. Create the chart object within the sheet
        metadata = sheets_service.get_spreadsheet_metadata(spreadsheet_id)
        if not metadata or not metadata.get("sheets"):
            raise RuntimeError("Failed to get spreadsheet metadata or no sheets found")
        sheet_id_numeric = metadata["sheets"][0]["properties"]["sheetId"]

        # --- START OF FIX: Map user-friendly chart type to API-specific chart type ---
        chart_type_upper = chart_type.upper()
        if chart_type_upper in ["BAR", "COLUMN"]:
            api_chart_type = "COLUMN"
        elif chart_type_upper == "PIE":
            api_chart_type = "PIE_CHART"
        else:
            api_chart_type = chart_type_upper
        # --- END OF FIX ---

        chart_result = sheets_service.create_chart_on_sheet(
            spreadsheet_id, sheet_id_numeric, api_chart_type, num_rows, num_cols, title
        )
        if not chart_result:
            raise RuntimeError("Failed to create chart in sheet: No result returned")
        if chart_result.get("error"):
            raise RuntimeError(
                f"Failed to create chart in sheet: {chart_result.get('message')}"
            )
        chart_id = chart_result["chartId"]

        # 5. Embed the chart into the Google Slide
        embed_result = slides_service.embed_sheets_chart(
            presentation_id,
            slide_id,
            spreadsheet_id,
            chart_id,
            position=(position_x, position_y),
            size=(size_width, size_height),
        )
        if not embed_result or embed_result.get("error"):
            raise RuntimeError(
                f"Failed to embed chart into slide: {embed_result.get('message')}"
            )

        return {
            "success": True,
            "message": f"Successfully added native '{title}' chart to slide.",
            "presentation_id": presentation_id,
            "slide_id": slide_id,
            "chart_element_id": embed_result.get("element_id"),
        }

    except Exception as e:
        logger.error(f"Chart creation workflow failed: {e}", exc_info=True)
        # Re-raise to ensure the MCP framework catches it and reports an error
        raise RuntimeError(f"An error occurred during the chart creation process: {e}")
