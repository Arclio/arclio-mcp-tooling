# File: packages/markdowndeck/src/markdowndeck/visualization/renderer.py
# Purpose: Handles the drawing of individual elements onto a Matplotlib axis.
# Key Changes:
# - REFACTORED: `render_sections` is a new function to recursively render section boundaries.
# - REFACTORED: `_render_text` now uses `calculate_text_bbox` for accurate text wrapping and honors `valign` and `ha` directives for precise positioning within the bounding box.
# - REFACTORED: All renderers are updated to handle new directive formats and provide clearer visualizations.

import logging
import textwrap
from io import BytesIO

import matplotlib.patches as patches
import requests
from PIL import Image as PILImage

from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.models import ElementType, Section
from markdowndeck.models.elements.list import ListItem
from markdowndeck.visualization.utils import (
    _get_font_for_element,
    parse_border_directive,
    parse_color,
)

logger = logging.getLogger(__name__)

SECTION_COLORS = [
    "#FF5733",
    "#335BFF",
    "#33FF57",
    "#C70039",
    "#900C3F",
    "#581845",
    "#FFC300",
]


def render_sections(ax, root_section: Section, level=0):
    """Recursively renders a section and its children's bounding boxes."""
    if not root_section or not root_section.position or not root_section.size:
        return

    pos_x, pos_y = root_section.position
    size_w, size_h = root_section.size
    color = SECTION_COLORS[level % len(SECTION_COLORS)]

    # Draw the bounding box for the section
    rect = patches.Rectangle(
        (pos_x, pos_y),
        size_w,
        size_h,
        linewidth=1.2,
        edgecolor=color,
        facecolor="none",
        linestyle="--",
        alpha=0.8,
        zorder=level + 0.1,  # Ensure deeper sections are drawn on top
    )
    ax.add_patch(rect)

    # Label the section
    label = f"{root_section.type.capitalize()}"
    if root_section.id:
        short_id = root_section.id.split("-")[-1]
        label += f" ({short_id})"

    ax.text(
        pos_x + 3,
        pos_y + 3,
        label,
        fontsize=7,
        color=color,
        va="top",
        ha="left",
        zorder=10 + level,
        bbox={
            "boxstyle": "round,pad=0.2",
            "facecolor": "white",
            "alpha": 0.7,
            "edgecolor": "none",
        },
    )

    # Recurse for child sections
    for child in root_section.children:
        if isinstance(child, Section):
            render_sections(ax, child, level + 1)


def render_elements(ax, elements):
    """Iterates through renderable elements and calls the appropriate renderer."""
    if not elements:
        return
    for element in elements:
        if not (element and element.position and element.size):
            logger.warning(f"Skipping render for element with missing layout: {element}")
            continue

        # Draw the element's main bounding box with styles from directives
        _draw_element_box(ax, element)

        # Dispatch to the specific renderer function for the element's content
        renderer_map = {
            ElementType.TITLE: _render_text,
            ElementType.SUBTITLE: _render_text,
            ElementType.TEXT: _render_text,
            ElementType.QUOTE: _render_text,
            ElementType.FOOTER: _render_text,
            ElementType.CODE: _render_code,  # Use a specific renderer for code
            ElementType.BULLET_LIST: _render_list,
            ElementType.ORDERED_LIST: _render_list,
            ElementType.IMAGE: _render_image,
            ElementType.TABLE: _render_table,
        }
        renderer_func = renderer_map.get(element.element_type)
        if renderer_func:
            renderer_func(ax, element)


def _draw_element_box(ax, element):
    """Draws the bounding box for an element with styling from directives."""
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})

    bg_color_val = directives.get("background")
    bg_color = parse_color(bg_color_val, default_color="none")

    border_props = parse_border_directive(directives.get("border")) or {
        "width": 1.0,
        "style": "-",
        "color": "#bbbbbb",
    }

    rect = patches.Rectangle(
        (pos_x, pos_y),
        size_w,
        size_h,
        linewidth=border_props["width"],
        edgecolor=border_props["color"],
        facecolor=bg_color,
        linestyle=border_props["style"],
        alpha=0.6,
        zorder=2,
    )
    ax.add_patch(rect)


def _render_text(ax, element):
    """Renders a text-based element using accurate font metrics for wrapping."""
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})
    content = getattr(element, "text", "")
    if not content:
        return

    font_size, font_family = _get_font_for_element(element)
    font_color = parse_color(directives.get("color"), default_color="#000000")

    # Handle padding directive
    padding = float(directives.get("padding", 5.0))
    text_area_width = size_w - (padding * 2)

    # Horizontal alignment
    ha_map = {"left": "left", "center": "center", "right": "right", "justify": "left"}
    ha = ha_map.get(directives.get("align", "left"), "left")

    # Vertical alignment
    va_map = {"top": "top", "middle": "center", "bottom": "bottom"}
    va = va_map.get(directives.get("valign", "top"), "top")

    # Calculate actual text block height for precise vertical alignment
    _wrapped_width, wrapped_height, _ = calculate_text_bbox(content, font_size, font_family, max_width=text_area_width)

    # Calculate text position
    text_x = pos_x + padding
    if ha == "center":
        text_x = pos_x + size_w / 2
    elif ha == "right":
        text_x = pos_x + size_w - padding

    text_y = pos_y + padding
    if va == "center":
        text_y = pos_y + (size_h - wrapped_height) / 2
    elif va == "bottom":
        text_y = pos_y + size_h - wrapped_height - padding

    # Draw the text
    ax.text(
        text_x,
        text_y,
        content,
        fontsize=font_size,
        family=font_family,
        color=font_color,
        ha=ha,
        va="top",
        wrap=True,
        zorder=3,
        bbox={"boxstyle": "square,pad=0", "fc": "none", "ec": "none"},
    )


def _render_code(ax, element):
    """Renders a code element with monospace font."""
    # This can be similar to _render_text but forces a monospace font
    # and has different default padding/colors.
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})
    content = getattr(element, "code", "")
    if not content:
        return

    # Force monospace font for code
    font_size, _ = _get_font_for_element(element)
    font_family = "monospace"
    font_color = parse_color(directives.get("color"), default_color="#333333")

    padding = 8.0
    text_area_width = size_w - (padding * 2)

    _wrapped_width, wrapped_height, _ = calculate_text_bbox(content, font_size, font_family, max_width=text_area_width)

    text_x = pos_x + padding
    text_y = pos_y + padding

    ax.text(
        text_x,
        text_y,
        content,
        fontsize=font_size,
        family=font_family,
        color=font_color,
        ha="left",
        va="top",
        wrap=True,
        zorder=3,
        bbox={"boxstyle": "square,pad=0", "fc": "none", "ec": "none"},
    )


def _render_list(ax, element):
    """Renders a list element with indentation and bullets."""
    pos_x, pos_y = element.position
    size_w, _ = element.size
    items = getattr(element, "items", [])
    if not items:
        return

    font_size, font_family = _get_font_for_element(element)
    color = parse_color(element.directives.get("color"), default_color="#000000")

    current_y = pos_y + 5  # Start with some top padding

    def render_item(item: ListItem, level: int, index: int):
        nonlocal current_y
        indent = level * 20
        bullet = "•"
        if element.element_type == ElementType.ORDERED_LIST:
            bullet = f"{index + 1}."

        # Render bullet/number
        ax.text(
            pos_x + 10 + indent,
            current_y,
            bullet,
            fontsize=font_size,
            family=font_family,
            color=color,
            ha="right",
            va="top",
            zorder=3,
        )

        # Render text
        text_width = size_w - (30 + indent + 10)
        _, text_height, _ = calculate_text_bbox(item.text, font_size, font_family, text_width)
        ax.text(
            pos_x + 30 + indent,
            current_y,
            item.text,
            fontsize=font_size,
            family=font_family,
            color=color,
            ha="left",
            va="top",
            wrap=True,
            zorder=3,
            bbox={"boxstyle": "square,pad=0", "fc": "none", "ec": "none"},
        )

        current_y += text_height + 4  # Add line spacing

        for child_idx, child in enumerate(item.children):
            render_item(child, level + 1, child_idx)

    for item_idx, item in enumerate(items):
        render_item(item, 0, item_idx)


def _render_table(ax, element):
    """Renders a structured grid for a table with truncated content."""
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    headers = getattr(element, "headers", [])
    rows = getattr(element, "rows", [])
    num_rows = len(rows) + (1 if headers else 0)
    num_cols = len(headers) if headers else (len(rows[0]) if rows else 0)
    if num_cols == 0 or num_rows == 0:
        return

    col_width = size_w / num_cols
    row_height = size_h / num_rows
    font_size, font_family = _get_font_for_element(element)

    # Draw grid
    for i in range(num_cols + 1):
        ax.plot(
            [pos_x + i * col_width, pos_x + i * col_width],
            [pos_y, pos_y + size_h],
            color="#cccccc",
            lw=0.7,
            zorder=2.1,
        )
    for i in range(num_rows + 1):
        ax.plot(
            [pos_x, pos_x + size_w],
            [pos_y + i * row_height, pos_y + i * row_height],
            color="#cccccc",
            lw=0.7,
            zorder=2.1,
        )

    # Render content
    def render_cell(text, r, c, is_header=False):
        cell_x, cell_y = pos_x + c * col_width, pos_y + r * row_height
        wrapped_text = "\n".join(textwrap.wrap(str(text), width=15))
        ax.text(
            cell_x + 5,
            cell_y + 5,
            wrapped_text,
            fontsize=font_size,
            family=font_family,
            ha="left",
            va="top",
            zorder=3,
            weight="bold" if is_header else "normal",
        )

    if headers:
        for c, header in enumerate(headers):
            render_cell(header, 0, c, is_header=True)
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            render_cell(cell, r + (1 if headers else 0), c)


def _render_image(ax, element):
    """Renders an image from a URL or a placeholder on failure."""
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    url = getattr(element, "url", "")

    try:
        response = requests.get(url, stream=True, timeout=3)
        response.raise_for_status()
        img = PILImage.open(BytesIO(response.content))
        ax.imshow(
            img,
            extent=(pos_x, pos_x + size_w, pos_y, pos_y + size_h),
            aspect="auto",
            zorder=2.5,
        )
    except Exception as e:
        logger.warning(f"Failed to render image from {url}: {e}")
        ax.text(
            pos_x + size_w / 2,
            pos_y + size_h / 2,
            f"[Image Load Error]\n{url[:50]}...",
            ha="center",
            va="center",
            fontsize=8,
            color="red",
            zorder=3,
        )


def render_slide_background(ax, slide, slide_width, slide_height):
    """Renders the slide background color or image."""
    bg_color = "#FFFFFF"
    bg_directive = getattr(slide, "background", None)

    if bg_directive:
        bg_type = bg_directive.get("type")
        bg_value = bg_directive.get("value")
        if bg_type == "color":
            bg_color = parse_color(bg_value, default_color="#F0F0F0")
        elif bg_type == "image":
            # Render background image
            try:
                response = requests.get(bg_value, stream=True, timeout=3)
                response.raise_for_status()
                img = PILImage.open(BytesIO(response.content))
                ax.imshow(
                    img,
                    extent=(0, slide_width, 0, slide_height),
                    aspect="auto",
                    zorder=0,
                )
                return  # Skip drawing solid color background
            except Exception as e:
                logger.warning(f"Failed to render background image from {bg_value}: {e}")
                bg_color = "#E0E0E0"  # Fallback color on image load failure

    background_rect = patches.Rectangle(
        (0, 0),
        slide_width,
        slide_height,
        facecolor=bg_color,
        edgecolor="none",
        zorder=0,
    )
    ax.add_patch(background_rect)


def render_metadata_overlay(ax, slide, slide_idx, slide_width):
    """Renders slide-level metadata like ID and notes status."""
    title_element = slide.get_title_element()
    title_text = f"Slide {slide_idx + 1}"
    if title_element and title_element.text:
        title_text += f": {title_element.text[:40]}"
        if len(title_element.text) > 40:
            title_text += "..."

    ax.text(slide_width / 2, -15, title_text, fontsize=10, ha="center", va="bottom")

    metadata = [f"ID: {slide.object_id or 'N/A'}"]
    if hasattr(slide, "notes") and slide.notes:
        metadata.append("Notes: Yes")
    if getattr(slide, "is_continuation", False):
        metadata.append("Continuation: Yes")

    ax.text(
        5,
        -5,
        "\n".join(metadata),
        fontsize=6,
        color="gray",
        va="bottom",
        ha="left",
        zorder=5,
    )
