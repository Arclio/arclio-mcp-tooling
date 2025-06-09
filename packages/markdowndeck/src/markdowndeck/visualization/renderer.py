"""
Core rendering functions for the SlideVisualizer.

This module provides a library of functions to render different components
of a slide, including zones, sections, elements, and metadata. It's designed
to work with the final, laid-out slide models from the refactored architecture.

Enhanced with better element validation and error handling.
"""

import logging
import textwrap
from io import BytesIO

import matplotlib.patches as patches
import requests
from PIL import Image as PILImage

from markdowndeck.models import ElementType
from markdowndeck.models.elements.list import ListItem
from markdowndeck.visualization.utils import parse_border_directive, parse_color

logger = logging.getLogger(__name__)

# --- Configuration Constants ---

# Colors for different structural components
ZONE_COLORS = {"header": "blue", "body": "green", "footer": "red"}
SECTION_COLORS = ["#FF5733", "#335BFF", "#33FF57", "#C70039", "#900C3F", "#581845"]

# Default font sizes for different element types
ELEMENT_FONT_SIZES = {
    "title": 18,
    "subtitle": 14,
    "text": 9,
    "bullet_list": 9,
    "ordered_list": 9,
    "table": 8,
    "code": 8,
    "quote": 9,
    "footer": 7,
    "unknown": 8,
}

# --- Zone and Section Renderers ---


def render_layout_zones(ax, layout_manager):
    """Renders the header, body, and footer zones based on LayoutManager dimensions."""
    # Access zone attributes from the position_calculator
    calc = layout_manager.position_calculator
    zones = {
        "header": (
            calc.header_left,
            calc.header_top,
            calc.header_width,
            calc.header_height,
        ),
        "body": (
            calc.body_left,
            calc.body_top,
            calc.body_width,
            calc.body_height,
        ),
        "footer": (
            calc.footer_left,
            calc.footer_top,
            calc.footer_width,
            calc.footer_height,
        ),
    }

    for name, (x, y, w, h) in zones.items():
        rect = patches.Rectangle(
            (x, y),
            w,
            h,
            linewidth=1,
            edgecolor=ZONE_COLORS[name],
            facecolor="none",
            linestyle="--",
            alpha=0.5,
            zorder=0.5,
        )
        ax.add_patch(rect)
        ax.text(
            x + 5,
            y + 12,
            name.upper(),
            fontsize=7,
            color=ZONE_COLORS[name],
            alpha=0.7,
            zorder=0.6,
        )


def render_sections(ax, sections, level=0):
    """Recursively renders all sections and subsections with nested coloring."""
    if not sections:
        return

    for idx, section in enumerate(sections):
        if not (_has_valid_position(section) and _has_valid_size(section)):
            continue

        pos_x, pos_y = section.position
        size_w, size_h = section.size
        color = SECTION_COLORS[level % len(SECTION_COLORS)]

        rect = patches.Rectangle(
            (pos_x, pos_y),
            size_w,
            size_h,
            linewidth=1.2,
            edgecolor=color,
            facecolor="none",
            linestyle=(0, (2, 2)),  # Dotted line (offset, (dash_pattern))
            alpha=0.6,
            zorder=1,
        )
        ax.add_patch(rect)

        # Create a concise label
        label = f"Sec: {section.id or idx}"
        ax.text(
            pos_x,
            pos_y - 2,
            label,
            fontsize=6,
            color=color,
            va="bottom",
            ha="left",
            zorder=1,
            bbox={
                "boxstyle": "round,pad=0.1",
                "facecolor": "white",
                "alpha": 0.8,
                "edgecolor": "none",
            },
        )

        child_sections = [c for c in section.children if hasattr(c, "children")]
        if child_sections:
            render_sections(ax, child_sections, level + 1)


# --- Element Renderer ---


def render_elements(ax, elements):
    """Iterates through elements and calls the appropriate renderer with enhanced validation."""
    if not elements:
        logger.debug("No elements to render")
        return

    logger.info(f"Rendering {len(elements)} elements")

    for i, element in enumerate(elements):
        # Enhanced validation with detailed logging
        if not _has_valid_position(element):
            logger.error(
                f"Element {i} ({getattr(element, 'element_type', 'unknown')}) missing valid position: "
                f"position={getattr(element, 'position', 'MISSING')}"
            )
            continue

        if not _has_valid_size(element):
            logger.error(
                f"Element {i} ({getattr(element, 'element_type', 'unknown')}) missing valid size: "
                f"size={getattr(element, 'size', 'MISSING')}"
            )
            continue

        element_type = getattr(element, "element_type", None)
        if not element_type:
            logger.error(f"Element {i} missing element_type")
            continue

        renderer_map = {
            ElementType.TITLE: _render_text,
            ElementType.SUBTITLE: _render_text,
            ElementType.TEXT: _render_text,
            ElementType.QUOTE: _render_text,
            ElementType.FOOTER: _render_text,
            ElementType.CODE: _render_code,
            ElementType.BULLET_LIST: _render_list,
            ElementType.ORDERED_LIST: _render_list,
            ElementType.IMAGE: _render_image,
            ElementType.TABLE: _render_table,
        }

        renderer_func = renderer_map.get(element_type)
        if renderer_func:
            try:
                logger.debug(
                    f"Rendering {element_type} element at {element.position} with size {element.size}"
                )
                renderer_func(ax, element)
            except Exception as e:
                logger.error(
                    f"Error rendering {element_type} element: {e}", exc_info=True
                )
        else:
            logger.warning(f"No renderer for element type: {element_type}")


def _has_valid_position(obj):
    """Enhanced check if object has a valid position attribute."""
    if not hasattr(obj, "position"):
        return False

    position = obj.position
    if position is None:
        return False

    if not isinstance(position, tuple | list):
        return False

    if len(position) < 2:
        return False

    # Check that position values are numeric
    try:
        float(position[0])
        float(position[1])
        return True
    except (ValueError, TypeError):
        return False


def _has_valid_size(obj):
    """Enhanced check if object has a valid size attribute."""
    if not hasattr(obj, "size"):
        return False

    size = obj.size
    if size is None:
        return False

    if not isinstance(size, tuple | list):
        return False

    if len(size) < 2:
        return False

    # Check that size values are numeric and positive
    try:
        w, h = float(size[0]), float(size[1])
        return w > 0 and h > 0
    except (ValueError, TypeError):
        return False


# --- Specific Element Renderers ---


def _render_text(ax, element):
    """Renders a text-based element (Text, Title, Quote, Footer) with enhanced error handling."""
    try:
        pos_x, pos_y = float(element.position[0]), float(element.position[1])
        size_w, size_h = float(element.size[0]), float(element.size[1])
    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Invalid position/size for text element: {e}")
        return

    directives = getattr(element, "directives", {})

    # Draw bounding box
    _draw_element_box(ax, element)

    # Prepare text styling
    content = getattr(element, "text", "")
    if not content:
        logger.debug("Text element has no content")
        return

    # Get element type string for font size lookup
    element_type_str = _get_element_type_string(element)

    font_size = float(
        directives.get("fontsize", ELEMENT_FONT_SIZES.get(element_type_str, 9))
    )
    color = parse_color(directives.get("color"), default_color="#000000")

    # Enhanced horizontal alignment handling
    h_align = _get_horizontal_alignment(element)
    v_align = directives.get("valign", "top")

    # Map to Matplotlib alignments
    ha_map = {"left": "left", "center": "center", "right": "right"}
    va_map = {"top": "top", "middle": "center", "bottom": "bottom"}
    ha = ha_map.get(h_align, "left")
    va = va_map.get(v_align, "top")

    # Calculate text position with padding
    padding = float(directives.get("padding", 5))
    text_x = pos_x + (
        size_w / 2 if ha == "center" else padding if ha == "left" else size_w - padding
    )
    text_y = pos_y + (
        size_h / 2 if va == "center" else padding if va == "top" else size_h - padding
    )

    # Wrap and render text
    wrapped_text = _wrap_text(content, font_size, size_w - padding * 2)
    ax.text(
        text_x,
        text_y,
        wrapped_text,
        fontsize=font_size,
        color=color,
        ha=ha,
        va=va,
        wrap=True,
        zorder=3,
    )


def _get_element_type_string(element):
    """Get element type as string for font size lookup."""
    element_type = getattr(element, "element_type", None)
    if element_type is None:
        return "unknown"

    # Handle both string and enum types
    if hasattr(element_type, "value"):
        return element_type.value
    return str(element_type)


def _get_horizontal_alignment(element):
    """Get horizontal alignment string, handling enum and string types."""
    alignment = getattr(element, "horizontal_alignment", None)

    if alignment is None:
        return "left"

    # Handle enum types
    if hasattr(alignment, "value"):
        return alignment.value

    # Handle string types
    if isinstance(alignment, str):
        return alignment

    # Fallback
    return "left"


def _render_code(ax, element):
    """Renders a code element with monospaced font."""
    # Similar to text, but with different defaults
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})

    content = getattr(element, "code", "")
    if not content:
        return

    padding = 8
    wrapped_text = _wrap_text(
        content, ELEMENT_FONT_SIZES["code"], size_w - padding * 2, True
    )

    ax.text(
        pos_x + padding,
        pos_y + padding,
        wrapped_text,
        fontsize=ELEMENT_FONT_SIZES["code"],
        color=parse_color(directives.get("color"), default_color="#333333"),
        family="monospace",
        ha="left",
        va="top",
        wrap=True,
        zorder=3,
    )


def _render_list(ax, element):
    """Renders a list element with proper indentation."""
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_h = element.size[1]
    items = getattr(element, "items", [])

    if not items:
        return

    def format_list_item(item: ListItem, level: int, item_idx: int):
        indent = "  " * level
        if (
            hasattr(element, "element_type")
            and element.element_type == ElementType.ORDERED_LIST
        ):
            bullet = f"{item_idx + 1}."
        else:
            bullet = "•"
        return f"{indent}{bullet} {item.text}"

    # Simple text representation for now
    display_text = ""
    for item_idx, item in enumerate(items):
        display_text += format_list_item(item, 0, item_idx) + "\\n"
        if hasattr(item, "children") and item.children:
            for child_idx, child in enumerate(item.children):
                display_text += format_list_item(child, 1, child_idx) + "\\n"

    ax.text(
        pos_x + 8,
        pos_y + size_h / 2,
        display_text.strip(),
        fontsize=ELEMENT_FONT_SIZES["bullet_list"],
        ha="left",
        va="center",
        wrap=True,
        zorder=3,
    )


def _render_table(ax, element):
    """Renders a simplified visual representation of a table with actual content."""
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_w, size_h = element.size

    # Get table dimensions
    headers = getattr(element, "headers", [])
    rows = getattr(element, "rows", [])

    num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
    num_rows = (1 if headers else 0) + len(rows)

    if num_cols == 0 or num_rows == 0:
        # Fallback to placeholder if no content
        ax.text(
            pos_x + 5, pos_y + 5, "[Empty Table]", fontsize=8, color="gray", zorder=3
        )
        return

    col_width = size_w / num_cols
    row_height = size_h / num_rows

    # Draw grid lines
    for i in range(1, num_cols):
        ax.plot(
            [pos_x + i * col_width, pos_x + i * col_width],
            [pos_y, pos_y + size_h],
            color="gray",
            lw=0.5,
            zorder=2,
        )
    for i in range(1, num_rows):
        ax.plot(
            [pos_x, pos_x + size_w],
            [pos_y + i * row_height, pos_y + i * row_height],
            color="gray",
            lw=0.5,
            zorder=2,
        )

    # Render table content
    current_row = 0

    # Render headers if they exist
    if headers:
        for col_idx, header in enumerate(headers):
            cell_x = pos_x + col_idx * col_width
            cell_y = pos_y + current_row * row_height

            # Truncate long headers to fit in cell
            display_text = header[:10] + "..." if len(header) > 10 else header

            ax.text(
                cell_x + col_width / 2,
                cell_y + row_height / 2,
                display_text,
                fontsize=ELEMENT_FONT_SIZES["table"],
                ha="center",
                va="center",
                weight="bold",
                zorder=3,
            )
        current_row += 1

    # Render data rows (limit to first few rows to avoid overcrowding)
    max_rows_to_show = min(len(rows), 3)  # Show max 3 data rows
    for row_idx in range(max_rows_to_show):
        row = rows[row_idx]
        for col_idx, cell_value in enumerate(
            row[:num_cols]
        ):  # Ensure we don't exceed columns
            cell_x = pos_x + col_idx * col_width
            cell_y = pos_y + current_row * row_height

            # Convert cell value to string and truncate if needed
            cell_str = str(cell_value) if cell_value is not None else ""
            display_text = cell_str[:8] + "..." if len(cell_str) > 8 else cell_str

            ax.text(
                cell_x + col_width / 2,
                cell_y + row_height / 2,
                display_text,
                fontsize=ELEMENT_FONT_SIZES["table"],
                ha="center",
                va="center",
                zorder=3,
            )
        current_row += 1

    # If there are more rows than we're showing, add an indicator
    if len(rows) > max_rows_to_show:
        ax.text(
            pos_x + size_w / 2,
            pos_y + size_h - 5,
            f"... +{len(rows) - max_rows_to_show} more rows",
            fontsize=6,
            ha="center",
            va="bottom",
            style="italic",
            color="gray",
            zorder=3,
        )


def _render_image(ax, element):
    """Renders an image or placeholder with error handling."""
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    url = getattr(element, "url", "")

    if not url:
        ax.text(
            pos_x + size_w / 2,
            pos_y + size_h / 2,
            "[No Image URL]",
            ha="center",
            va="center",
            fontsize=8,
            color="gray",
            zorder=3,
        )
        return

    try:
        response = requests.get(url, stream=True, timeout=5)
        response.raise_for_status()
        img = PILImage.open(BytesIO(response.content))
        ax.imshow(
            img,
            extent=(pos_x, pos_x + size_w, pos_y + size_h, pos_y),
            aspect="auto",
            zorder=2,
        )
    except Exception as e:
        logger.warning(f"Failed to render image from {url}: {e}")
        ax.text(
            pos_x + size_w / 2,
            pos_y + size_h / 2,
            "[Image Error]",
            ha="center",
            va="center",
            fontsize=8,
            color="red",
            zorder=3,
        )


# --- Helper Rendering Functions ---


def _draw_element_box(ax, element):
    """Draws the bounding box for an element with styling from directives."""
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})
    element_type_str = _get_element_type_string(element)

    # Element Background
    face_color = {"text": "#fff2cc", "code": "#d0e0e3", "image": "#fce5cd"}.get(
        element_type_str, "#f3f3f3"
    )
    bg_directive = directives.get("background")
    if bg_directive:
        face_color = parse_color(bg_directive, face_color)

    # Element Border
    edge_color, line_width, line_style = "dimgray", 0.5, "-"
    border_info = parse_border_directive(directives.get("border"))
    if border_info:
        edge_color = border_info["color"]
        line_width = border_info["width"]
        line_style = border_info["style"]

    rect = patches.Rectangle(
        (pos_x, pos_y),
        size_w,
        size_h,
        linewidth=line_width,
        edgecolor=edge_color,
        facecolor=face_color,
        linestyle=line_style,
        alpha=0.6,
        zorder=1.5,
    )
    ax.add_patch(rect)


def _wrap_text(text, font_size, box_width, is_monospace=False):
    """Calculates wrapping for text within a given box width."""
    avg_char_width_factor = 0.7 if is_monospace else 0.5
    chars_per_line = max(1, int(box_width / (font_size * avg_char_width_factor)))
    return "\\n".join(
        textwrap.wrap(text, width=chars_per_line, replace_whitespace=False)
    )


def render_slide_background(ax, slide, slide_width, slide_height):
    """
    Renders the slide background based on the slide's background property.
    """
    if not hasattr(slide, "background") or not slide.background:
        background_color = "white"
    else:
        background_type = slide.background.get("type")
        background_value = slide.background.get("value")

        if background_type == "color":
            background_color = (
                background_value
                if background_value and background_value.startswith("#")
                else "#f5f5f5"
            )
        elif background_type == "image":
            logger.info(
                f"Background image not rendered in visualization: {background_value}"
            )
            background_color = "#f0f0f0"
        else:
            background_color = "white"

    background_rect = patches.Rectangle(
        (0, 0),
        slide_width,
        slide_height,
        facecolor=background_color,
        edgecolor="none",
        alpha=0.8,
        zorder=0,
    )
    ax.add_patch(background_rect)


def render_metadata_overlay(ax, slide, slide_idx):
    """Renders slide-level metadata like layout, notes, etc."""
    metadata = [f"Slide {slide_idx + 1} (ID: {slide.object_id or 'N/A'})"]
    if hasattr(slide, "layout") and slide.layout:
        metadata.append(
            f"Layout: {slide.layout.value if hasattr(slide.layout, 'value') else slide.layout}"
        )
    if hasattr(slide, "notes") and slide.notes:
        metadata.append("Notes: Yes")
    if hasattr(slide, "background") and slide.background:
        metadata.append(f"BG: {slide.background.get('type', 'unknown')}")

    ax.text(
        5,
        5,
        "\\n".join(metadata),
        fontsize=6,
        color="black",
        alpha=0.8,
        va="top",
        ha="left",
        zorder=5,
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": "lightyellow",
            "alpha": 0.7,
        },
    )
