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
) -> dict[str, Any]:
    """
    Create a new presentation.

    Args:
        title: The title for the new presentation.

    Returns:
        Created presentation data or raises error.
    """
    logger.info(f"Executing create_presentation with title: '{title}'")
    if not title or not title.strip():
        raise ValueError("Presentation title cannot be empty")

    slides_service = SlidesService()
    result = slides_service.create_presentation(title=title)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating presentation"))

    return result


@mcp.tool(
    name="create_slide",
    description="Adds a new slide to a Google Slides presentation with a specified layout.",
)
async def create_slide(
    presentation_id: str,
    layout: str = "TITLE_AND_BODY",
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
    description="Adds an image to a slide in a Google Slides presentation from a publicly accessible URL with precise positioning support. For full-height coverage, only specify size_height. For full-width coverage, only specify size_width. For exact dimensions, specify both.",
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
    description="Creates a text box with text content and font formatting in one operation. Perfect for adding text boxes to slides with specific font requirements.",
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
) -> dict[str, Any]:
    """
    Create a text box with text and font formatting.

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
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating text box with text"))

    return result


@mcp.tool(
    name="update_text_formatting",
    description="Updates formatting of text in an existing text box with support for bold, italic, code formatting, font size, and font family. Supports applying different formatting to specific text ranges within the same textbox.",
)
async def update_text_formatting(
    presentation_id: str,
    element_id: str,
    formatted_text: str,
    font_size: float | None = None,
    font_family: str | None = None,
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
        start_index=start_index,
        end_index=end_index,
    )

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error updating text formatting"))

    return result
