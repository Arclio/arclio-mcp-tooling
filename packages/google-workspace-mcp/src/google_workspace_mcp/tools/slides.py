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
    logger.info(f"Executing create_slide in presentation '{presentation_id}' with layout '{layout}'")
    if not presentation_id or not presentation_id.strip():
        raise ValueError("Presentation ID cannot be empty")
    # Optional: Validate layout against known predefined layouts?

    slides_service = SlidesService()
    result = slides_service.create_slide(presentation_id=presentation_id, layout=layout)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating slide"))

    return result


@mcp.tool(
    name="add_text_to_slide",
    description="Adds text to a specified slide in a Google Slides presentation.",
)
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
        raise ValueError(f"Invalid shape_type '{shape_type}' provided. Must be one of {valid_shape_types}.")

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


@mcp.tool(
    name="add_formatted_text_to_slide",
    description="Adds rich-formatted text (with bold, italic, etc.) to a slide.",
)
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


@mcp.tool(
    name="add_bulleted_list_to_slide",
    description="Adds a bulleted list to a slide in a Google Slides presentation.",
)
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


@mcp.tool(
    name="add_slide_notes",
    description="Adds presenter notes to a slide in a Google Slides presentation.",
)
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
    logger.info(f"Executing delete_slide: slide '{slide_id}' from presentation '{presentation_id}'")
    if not presentation_id or not slide_id:
        raise ValueError("Presentation ID and Slide ID are required")

    slides_service = SlidesService()
    result = slides_service.delete_slide(presentation_id=presentation_id, slide_id=slide_id)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error deleting slide"))

    return result


@mcp.tool(
    name="create_presentation_from_markdown",
    description="Creates a Google Slides presentation from structured Markdown content with enhanced formatting support using markdowndeck.",
)
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
    if not title or not title.strip() or not markdown_content or not markdown_content.strip():
        raise ValueError("Title and markdown content are required")

    slides_service = SlidesService()
    result = slides_service.create_presentation_from_markdown(title=title, markdown_content=markdown_content)

    if isinstance(result, dict) and result.get("error"):
        raise ValueError(result.get("message", "Error creating presentation from Markdown"))

    return result
