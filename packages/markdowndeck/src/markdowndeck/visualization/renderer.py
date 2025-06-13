import logging
from io import BytesIO

import matplotlib.patches as patches
import requests
from PIL import Image as PILImage

from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.models import ElementType
from markdowndeck.models.elements.list import ListItem
from markdowndeck.visualization.utils import (
    _get_font_for_element,
    parse_border_directive,
    parse_color,
)

logger = logging.getLogger(__name__)

SECTION_COLORS = ["#FF5733", "#335BFF", "#33FF57", "#C70039", "#900C3F", "#581845"]


def render_sections(ax, root_section, level=0):
    """Recursively renders a section and its children's bounding boxes."""
    if not root_section or not root_section.position or not root_section.size:
        return

    pos_x, pos_y = root_section.position
    size_w, size_h = root_section.size
    color = SECTION_COLORS[level % len(SECTION_COLORS)]

    rect = patches.Rectangle(
        (pos_x, pos_y),
        size_w,
        size_h,
        linewidth=1.0,
        edgecolor=color,
        facecolor="none",
        linestyle="--",
        alpha=0.7,
        zorder=1,
    )
    ax.add_patch(rect)

    label = f"Sec: {root_section.type}"
    if root_section.id and "root" not in root_section.id:
        label = f"{root_section.type} ({root_section.id.split('-')[-1]})"

    ax.text(
        pos_x + 2,
        pos_y - 2,
        label,
        fontsize=6,
        color=color,
        va="bottom",
        ha="left",
        zorder=1.1,
        bbox={
            "boxstyle": "round,pad=0.1",
            "facecolor": "white",
            "alpha": 0.8,
            "edgecolor": "none",
        },
    )

    for child in root_section.children:
        if isinstance(child, type(root_section)):
            render_sections(ax, child, level + 1)


def render_elements(ax, elements):
    """Iterates through renderable elements and calls the appropriate renderer."""
    if not elements:
        return
    for element in elements:
        if not (element and element.position and element.size):
            logger.warning(
                f"Skipping render for element with missing layout: {element}"
            )
            continue

        renderer_map = {
            ElementType.TITLE: _render_text,
            ElementType.SUBTITLE: _render_text,
            ElementType.TEXT: _render_text,
            ElementType.QUOTE: _render_text,
            ElementType.FOOTER: _render_text,
            ElementType.CODE: _render_text,
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

    bg_color = parse_color(directives.get("background"), default_color="#f0f0f0")

    border_props = parse_border_directive(directives.get("border")) or {
        "width": 0.8,
        "style": "-",
        "color": "#888888",
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
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_w, size_h = element.size
    directives = getattr(element, "directives", {})
    content = getattr(element, "text", "")
    if not content:
        return

    font_size, font_family = _get_font_for_element(element)
    font_color = parse_color(directives.get("color"), default_color="#000000")

    padding = float(directives.get("padding", 5.0))
    ha = directives.get("align", "left")
    va = directives.get("valign", "top")

    # Use font_metrics to get accurate wrapped text dimensions
    wrapped_text_width, wrapped_text_height = calculate_text_bbox(
        content, font_size, font_family, max_width=(size_w - 2 * padding)
    )

    # Position text box based on alignment
    if ha == "center":
        text_x = pos_x + size_w / 2
    elif ha == "right":
        text_x = pos_x + size_w - padding
    else:  # left
        text_x = pos_x + padding

    if va == "middle":
        text_y = pos_y + (size_h - wrapped_text_height) / 2
    elif va == "bottom":
        text_y = pos_y + size_h - wrapped_text_height - padding
    else:  # top
        text_y = pos_y + padding

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
        bbox={
            "boxstyle": f"square,pad=0",
            "fc": "none",
            "ec": "none",
            "width": size_w - 2 * padding,
            "height": size_h - 2 * padding,
        },
    )


def _render_list(ax, element):
    """Renders a list element with indentation and bullets."""
    _draw_element_box(ax, element)
    pos_x, pos_y = element.position
    size_w, _ = element.size
    items = getattr(element, "items", [])
    if not items:
        return

    font_size, font_family = _get_font_for_element(element)
    color = parse_color(element.directives.get("color"), default_color="#000000")

    current_y = pos_y + 5  # Start with some top padding

    def render_item(item: ListItem, level: int):
        nonlocal current_y
        indent = level * 20
        bullet = "•"
        if element.element_type == ElementType.ORDERED_LIST:
            # Simplified numbering for visualization
            bullet = f"{item.idx+1}."

        # Render bullet/number
        ax.text(
            pos_x + 10 + indent,
            current_y,
            bullet,
            fontsize=font_size,
            family=font_family,
            color=color,
            ha="left",
            va="top",
            zorder=3,
        )

        # Render text
        text_width = size_w - (30 + indent)
        _, text_height = calculate_text_bbox(
            item.text, font_size, font_family, text_width
        )
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
            bbox={
                "boxstyle": "square,pad=0",
                "fc": "none",
                "ec": "none",
                "width": text_width,
            },
        )

        current_y += text_height + 4  # Add line spacing

        for child_idx, child in enumerate(item.children):
            child.idx = child_idx
            render_item(child, level + 1)

    for item_idx, item in enumerate(items):
        item.idx = item_idx
        render_item(item, 0)


def _render_table(ax, element):
    """Renders a structured grid for a table with truncated content."""
    _draw_element_box(ax, element)
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
    for i in range(1, num_cols):
        ax.plot(
            [pos_x + i * col_width, pos_x + i * col_width],
            [pos_y, pos_y + size_h],
            color="#cccccc",
            lw=0.7,
            zorder=2.1,
        )
    for i in range(1, num_rows):
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
    _draw_element_box(ax, element)
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
            "[Image Load Error]",
            ha="center",
            va="center",
            fontsize=8,
            color="red",
            zorder=3,
        )


def render_slide_background(ax, slide, slide_width, slide_height):
    """Renders the slide background color."""
    bg_color = "#FFFFFF"
    if hasattr(slide, "background") and slide.background:
        bg_color = parse_color(slide.background.get("value"), default_color="#F0F0F0")

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
    title = slide.get_title_element()
    title_text = f"Slide {slide_idx + 1}: {getattr(title, 'text', 'Untitled')}"
    ax.text(slide_width / 2, -15, title_text, fontsize=10, ha="center", va="bottom")

    metadata = [f"ID: {slide.object_id or 'N/A'}"]
    if hasattr(slide, "notes") and slide.notes:
        metadata.append("Notes: Yes")

    ax.text(
        5,
        5,
        "\n".join(metadata),
        fontsize=6,
        color="gray",
        va="top",
        ha="left",
        zorder=5,
    )
