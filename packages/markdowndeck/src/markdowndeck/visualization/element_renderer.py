import logging
import re
import textwrap
import io  # For image handling
import requests  # For fetching images
from PIL import Image as PILImage  # For image handling, aliased to avoid conflict
import numpy as np

import matplotlib.patches as patches
import matplotlib.font_manager as fm
import matplotlib.gridspec as gridspec
from matplotlib.table import Table

from markdowndeck.models.elements.list import ListElement
from markdowndeck.models.elements.table import TableElement

logger = logging.getLogger(__name__)

# Updated and more comprehensive color mapping for elements
ELEMENT_COLORS = {
    "title": "#cfe2f3",  # Light blue
    "subtitle": "#d9ead3",  # Light green
    "text": "#fff2cc",  # Light yellow
    "bullet_list": "#e0e0e0",  # Light grey for lists
    "ordered_list": "#d9d2e9",  # Light purple for lists
    "image": "#fce5cd",  # Light orange for image placeholder box
    "table": "#f4cccc",  # Light red
    "code": "#d0e0e3",  # Light teal/cyan for code block background
    "quote": "#fffacd",  # Lemon chiffon for quotes
    "footer": "#ead1dc",  # Light pink
    "unknown": "#f3f3f3",  # Very light grey
}

# Simple mapping for common CSS color names to hex for Matplotlib
# (Matplotlib understands some names, but hex is safer)
NAMED_COLORS_HEX = {
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#008000",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "brown": "#A52A2A",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#C0C0C0",
    "gold": "#FFD700",
    "transparent": "none",
    "aqua": "#00FFFF",
    "teal": "#008080",
    "navy": "#000080",
    "olive": "#808000",
    "maroon": "#800000",
    "lime": "#00FF00",
    "fuchsia": "#FF00FF",
    # Google Slides Theme Colors (Approximate Visual Mapping)
    "BACKGROUND1": "#FFFFFF",  # Often white or light
    "BACKGROUND2": "#F3F3F3",  # Often a slightly off-white or gray
    "TEXT1": "#000000",  # Often black or dark
    "TEXT2": "#555555",  # Often a secondary dark gray
    "ACCENT1": "#4A86E8",  # Default blue
    "ACCENT2": "#FF9900",  # Default orange
    "ACCENT3": "#3C78D8",  # Another blue
    "ACCENT4": "#6AA84F",  # Default green
    "ACCENT5": "#A64D79",  # Default purple
    "ACCENT6": "#CC0000",  # Default red
    "HYPERLINK": "#1155CC",  # Default link blue
}

# Default font sizes for different element types
DEFAULT_FONT_SIZES = {
    "title": 20,
    "subtitle": 16,
    "text": 10,
    "bullet_list": 10,
    "ordered_list": 10,
    "table": 9,
    "code": 8,
    "quote": 10,
    "footer": 8,
    "unknown": 10,
}


def parse_color(color_value_input, default_color="#000000"):
    """
    Parse a color value (hex, named, or theme constant) into a Matplotlib-compatible format.
    """
    if not isinstance(color_value_input, str):
        return default_color  # Fallback for unexpected types

    color_value = color_value_input.strip().lower()

    if color_value.startswith("#"):  # Hex color
        return color_value_input.strip()  # Return original case for hex

    if color_value in NAMED_COLORS_HEX:  # Known named color or theme color mapped
        return NAMED_COLORS_HEX[color_value]

    # If it's a theme color name not in our direct map, try uppercasing
    if color_value.upper() in NAMED_COLORS_HEX:
        return NAMED_COLORS_HEX[color_value.upper()]

    logger.warning(
        f"Unknown color value '{color_value_input}', defaulting to {default_color}."
    )
    return default_color


def parse_border_directive(border_str):
    """
    Parse a border directive string (e.g., "1pt solid #cccccc") into components.
    Returns: dict with 'width' (float), 'style' (str), 'color' (str) or None if unparseable.
    """
    if not border_str or not isinstance(border_str, str):
        return None

    parts = border_str.lower().split()
    border_props = {"width": 1.0, "style": "solid", "color": "#000000"}  # Defaults

    for part in parts:
        if part.endswith("pt") or part.endswith("px"):
            try:
                border_props["width"] = float(part.rstrip("ptx"))
            except ValueError:
                pass
        elif part in ["solid", "dashed", "dotted", "dashdot"]:  # Matplotlib linestyles
            border_props["style"] = part
        elif (
            part.startswith("#")
            or part in NAMED_COLORS_HEX
            or part.upper() in NAMED_COLORS_HEX
        ):
            border_props["color"] = parse_color(part, border_props["color"])

    # Convert Matplotlib linestyle if needed
    linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
    border_props["style"] = linestyle_map.get(border_props["style"], "-")

    return border_props


def render_elements(ax, elements, slide_width, slide_height, show_metadata=True):
    """
    Render all elements in a slide with enhanced styling.
    """
    for el_idx, element in enumerate(elements):
        if (
            not hasattr(element, "position")
            or element.position is None
            or not hasattr(element, "size")
            or element.size is None
        ):
            logger.warning(f"Skipping element {el_idx} due to missing position/size.")
            continue

        pos_x, pos_y = element.position
        size_w, size_h = element.size
        element_type_value = getattr(
            getattr(element, "element_type", None), "value", "unknown"
        )

        directives = getattr(element, "directives", {})

        # Element Background
        face_color = ELEMENT_COLORS.get(element_type_value, ELEMENT_COLORS["unknown"])
        bg_directive = directives.get("background")
        if bg_directive:
            # Directive parser returns ('color', val) or ('url', val) or ('value', val)
            if isinstance(bg_directive, tuple) and bg_directive[0] == "color":
                face_color = parse_color(bg_directive[1], face_color)
            elif isinstance(bg_directive, str):  # Direct color string
                face_color = parse_color(bg_directive, face_color)
            # Note: Background URLs for element backgrounds are complex for matplotlib patches,
            # focusing on color for now. Slide backgrounds handle URLs.

        # Element Border
        edge_color = "dimgray"
        line_width = 1
        line_style = "-"
        border_directive_str = directives.get("border")
        if border_directive_str:
            parsed_border = parse_border_directive(border_directive_str)
            if parsed_border:
                edge_color = parsed_border["color"]
                line_width = parsed_border["width"]
                line_style = parsed_border["style"]

        # Create the element background rectangle
        rect = patches.Rectangle(
            (pos_x, pos_y),
            size_w,
            size_h,
            linewidth=line_width,
            edgecolor=edge_color,
            facecolor=face_color,
            linestyle=line_style,
            alpha=(
                0.6 if face_color != "none" else 0
            ),  # More opaque for better visibility if colored
            zorder=1,
        )
        ax.add_patch(rect)

        # Special handling for different element types
        if (
            element_type_value == "table"
            and hasattr(element, "headers")
            and hasattr(element, "rows")
        ):
            render_table(ax, element, pos_x, pos_y, size_w, size_h, directives)
        elif element_type_value == "image" and hasattr(element, "url") and element.url:
            try_render_image(ax, element.url, pos_x, pos_y, size_w, size_h)
        else:
            # Extract and render the content for other element types
            content = extract_element_content(element)
            render_element_content(
                ax,
                element,
                content,
                pos_x,
                pos_y,
                size_w,
                size_h,
                element_type_value,
                directives,
            )

        if show_metadata:
            render_element_metadata(
                ax, element, el_idx, element_type_value, pos_x, pos_y
            )


def extract_element_content(element):
    """Extracts displayable content string from an element."""
    if hasattr(element, "text"):
        content = element.text
        return re.sub(r"", "", content, flags=re.DOTALL) if content else ""
    if hasattr(element, "code"):
        return element.code or ""
    if hasattr(element, "items") and element.items:
        # More detailed list representation needed in render_element_content
        return "[List Items]"
    if hasattr(element, "url"):
        return f"[Image: {element.url[:50]}{'...' if len(element.url) > 50 else ''}]"
    if hasattr(element, "headers") and hasattr(element, "rows"):
        return f"[Table: {element.get_column_count()}x{element.get_row_count()}]"
    return ""


def render_element_content(
    ax,
    element,
    content_summary,
    pos_x,
    pos_y,
    size_w,
    size_h,
    element_type_value,
    directives,
):
    """
    Renders the content of an element with enhanced styling and layout handling.
    """
    # Skip rendering if we're handling a table or image separately
    if (element_type_value == "table" and hasattr(element, "headers")) or (
        element_type_value == "image" and hasattr(element, "url") and element.url
    ):
        return

    # Get text content based on element type
    text_content = ""
    if hasattr(element, "text"):
        text_content = getattr(element, "text", "")
    elif hasattr(element, "code"):
        text_content = getattr(element, "code", "")
    elif element_type_value in ["bullet_list", "ordered_list"] and hasattr(
        element, "items"
    ):
        text_content = format_list_for_display(element)
    else:  # Fallback to content_summary for unknown or simple cases
        text_content = content_summary

    if not text_content.strip():
        return

    # --- Enhanced Styling from Directives ---

    # Font size with better defaults based on element type
    default_size = DEFAULT_FONT_SIZES.get(element_type_value, 10)
    font_size_directive = directives.get("fontsize", default_size)
    try:
        font_size = float(font_size_directive)
    except ValueError:
        font_size = default_size

    # Font color
    font_color = parse_color(directives.get("color", "#000000"))  # Default black

    # Font family with better handling
    font_family_directive = directives.get("font-family", "sans-serif")

    # Font weight and style based on element type and formatting
    font_weight = "normal"
    font_style = "normal"

    # Apply special formatting based on element type
    if element_type_value == "title":
        font_weight = "bold"
    elif element_type_value == "subtitle":
        font_weight = "medium"
    elif element_type_value == "code":
        font_family_directive = "monospace"  # Force monospace for code

    # Override with any explicit formatting if available
    if hasattr(element, "formatting"):
        for fmt in element.formatting:
            if hasattr(fmt, "format_type") and hasattr(fmt.format_type, "value"):
                if fmt.format_type.value == "bold":
                    font_weight = "bold"
                if fmt.format_type.value == "italic":
                    font_style = "italic"

    # Alignment handling
    h_align = getattr(element, "horizontal_alignment", None)
    v_align = getattr(element, "vertical_alignment", None)

    ha_map = {
        "left": "left",
        "center": "center",
        "right": "right",
        "justify": "left",  # Justify approx as left
    }
    va_map = {"top": "top", "middle": "center", "bottom": "bottom"}

    matplotlib_ha = ha_map.get(h_align.value if h_align else "left", "left")
    matplotlib_va = va_map.get(v_align.value if v_align else "top", "top")

    # Text position with proper padding
    padding = float(directives.get("padding", 5))
    text_x = pos_x + padding
    text_y = pos_y + padding
    text_box_width = size_w - (2 * padding)

    # Adjust text position based on alignment
    if matplotlib_ha == "center":
        text_x = pos_x + size_w / 2
    elif matplotlib_ha == "right":
        text_x = pos_x + size_w - padding

    if matplotlib_va == "center":
        text_y = pos_y + size_h / 2
    elif matplotlib_va == "bottom":
        text_y = pos_y + size_h - padding

    # Improved text wrapping calculation based on font properties
    # Monospace fonts are wider, adjust char_width assumption
    is_monospace = font_family_directive.lower() in [
        "monospace",
        "courier",
        "courier new",
    ]

    # Better approximation of chars per line based on font properties
    avg_char_width_factor = 0.6 if is_monospace else 0.5
    font_size_factor = font_size / 10  # Scale relative to a 10pt font

    # Calculate width in characters, taking into account font size and style
    # Bold text takes up more space
    style_factor = 1.2 if font_weight == "bold" else 1.0

    # Calculate maximum characters per line
    chars_per_line = max(
        1,
        int(text_box_width / (font_size_factor * style_factor * avg_char_width_factor)),
    )

    # Smarter wrapping that better preserves structure
    if element_type_value in ["bullet_list", "ordered_list"]:
        # Lists already have line breaks, no need for additional wrapping
        wrapped_text = text_content
    elif element_type_value == "code":
        # For code blocks, preserve indentation and line breaks
        wrapped_lines = []
        for line in text_content.splitlines():
            if len(line) <= chars_per_line:
                wrapped_lines.append(line)
            else:
                # Soft wrap code lines that are too long
                wrapped_lines.extend(
                    textwrap.wrap(
                        line,
                        width=chars_per_line,
                        break_on_hyphens=False,
                        replace_whitespace=False,
                        drop_whitespace=False,
                    )
                )
        wrapped_text = "\n".join(wrapped_lines)
    else:
        # Regular text wrapping for other content
        wrapped_text = "\n".join(
            textwrap.wrap(
                text_content,
                width=chars_per_line,
                replace_whitespace=False,
                break_long_words=True,
            )
        )

    # Render the text with enhanced styling
    ax.text(
        text_x,
        text_y,
        wrapped_text,
        fontsize=font_size,
        color=font_color,
        family=font_family_directive,
        weight=font_weight,
        style=font_style,
        va=matplotlib_va,
        ha=matplotlib_ha,
        wrap=True,
        zorder=3,
        # Add a slight background to make text more readable over element background
        bbox=(
            {
                "facecolor": "white",
                "alpha": 0.2 if element_type_value not in ["code", "quote"] else 0.4,
                "pad": 2,
                "edgecolor": "none",
            }
            if font_color != "white"
            else None
        ),
    )

    # For code blocks, add a gutter with line numbers
    if element_type_value == "code" and wrapped_text:
        lines = wrapped_text.split("\n")
        if len(lines) > 1:
            # Create line numbers
            line_numbers = "\n".join(str(i + 1) for i in range(len(lines)))
            # Add the line numbers in the gutter
            ax.text(
                pos_x + 2,  # Close to the left edge
                text_y,
                line_numbers,
                fontsize=font_size * 0.8,  # Slightly smaller
                color="gray",
                family="monospace",
                va=matplotlib_va,
                ha="right",
                zorder=3,
            )


def render_table(ax, element, pos_x, pos_y, size_w, size_h, directives):
    """
    Renders a proper visual table in the element's bounding box.
    """
    if not (hasattr(element, "headers") and hasattr(element, "rows") and element.rows):
        # Not a proper table or no data
        ax.text(
            pos_x + size_w / 2,
            pos_y + size_h / 2,
            "[Empty Table]",
            fontsize=8,
            ha="center",
            va="center",
            color="darkred",
            zorder=3,
        )
        return

    # Get table dimensions
    num_cols = element.get_column_count()
    num_rows = element.get_row_count() + (
        1 if element.headers else 0
    )  # +1 for header row

    if num_cols == 0 or num_rows == 0:
        return

    # Create grid for the table
    grid_height = min(num_rows, 10)  # Limit to 10 rows for visualization
    has_headers = element.headers is not None and len(element.headers) > 0

    # Calculate cell sizes
    cell_width = size_w / num_cols
    cell_height = size_h / grid_height

    # Create a mini subplot for the table (for better control)
    table_ax = ax.inset_axes([pos_x, pos_y, size_w, size_h], transform=ax.transData)
    table_ax.set_xlim(0, 1)
    table_ax.set_ylim(0, 1)
    table_ax.axis("off")

    # Create matplotlib Table instance
    table = Table(table_ax, bbox=[0, 0, 1, 1])

    # Cell styling
    header_color = parse_color(directives.get("header-color", "#E6E6E6"))  # Light gray
    cell_color = parse_color(directives.get("cell-color", "#FFFFFF"))  # White
    border_color = parse_color(directives.get("border-color", "#CCCCCC"))  # Light gray

    # Font settings
    cell_text_size = float(directives.get("fontsize", DEFAULT_FONT_SIZES["table"]))
    header_text_size = cell_text_size + 1  # Headers slightly larger

    # Process table headers
    if has_headers:
        for col_idx, header in enumerate(element.headers[:num_cols]):
            if header is None:
                header = ""
            cell = table.add_cell(
                0,
                col_idx,
                1.0 / num_cols,
                1.0 / grid_height,
                text=str(header),
                loc="center",
                facecolor=header_color,
            )
            cell.set_text_props(fontsize=header_text_size, weight="bold", wrap=True)
            cell.set_edgecolor(border_color)

    # Process table rows (with limit to avoid excessive rows)
    displayed_rows = element.rows[
        : min(len(element.rows), grid_height - 1 if has_headers else grid_height)
    ]
    for row_idx, row in enumerate(displayed_rows):
        table_row = row_idx + 1 if has_headers else row_idx  # Adjust for header
        for col_idx, cell_content in enumerate(row[:num_cols]):
            if cell_content is None:
                cell_content = ""
            # Create table cell
            cell = table.add_cell(
                table_row,
                col_idx,
                1.0 / num_cols,
                1.0 / grid_height,
                text=str(cell_content),
                loc="center",
                facecolor=cell_color,
            )
            cell.set_text_props(fontsize=cell_text_size, wrap=True)
            cell.set_edgecolor(border_color)

    # If there are more rows than we're displaying, add an indicator
    if len(element.rows) > grid_height - (1 if has_headers else 0):
        more_rows = len(element.rows) - (grid_height - (1 if has_headers else 0))
        # Add text to indicate there are more rows
        table_ax.text(
            0.5,
            0.01,  # Bottom center
            f"+{more_rows} more rows",
            transform=table_ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=7,
            style="italic",
            color="gray",
        )

    # Add the table to the axes
    table_ax.add_table(table)


def try_render_image(ax, url, x, y, width, height):
    """
    Enhanced image renderer with better sizing, fetching and error handling.
    """
    try:
        # Use a proper timeout to avoid hanging
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, stream=True, timeout=5, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Process the image
        img_data = response.content
        img = PILImage.open(io.BytesIO(img_data))

        # Convert to numpy array for matplotlib
        img_array = np.array(img)

        # Calculate aspect ratio and position for better fit
        img_aspect = img.width / img.height
        box_aspect = width / height

        # Determine how to fit the image (maintain aspect ratio)
        if img_aspect > box_aspect:  # Image is wider than box
            render_width = width
            render_height = width / img_aspect
            # Center vertically
            render_x = x
            render_y = y + (height - render_height) / 2
        else:  # Image is taller than box
            render_height = height
            render_width = height * img_aspect
            # Center horizontally
            render_x = x + (width - render_width) / 2
            render_y = y

        # Ensure extent is properly calculated for inverted y-axis
        ax.imshow(
            img_array,
            extent=(
                render_x,
                render_x + render_width,
                render_y + render_height,  # Bottom (larger in matplotlib coords)
                render_y,  # Top (smaller in matplotlib coords)
            ),
            aspect="auto",
            zorder=2,
        )

        # Add a thin border around the image
        border = patches.Rectangle(
            (render_x, render_y),
            render_width,
            render_height,
            linewidth=0.5,
            edgecolor="black",
            facecolor="none",
            zorder=2.5,
        )
        ax.add_patch(border)

        logger.debug(f"Successfully rendered image from URL: {url}")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching image from {url}")
        ax.text(
            x + width / 2,
            y + height / 2,
            f"[Image Fetch Timeout]\n{url[:30]}...",
            color="red",
            ha="center",
            va="center",
            fontsize=8,
            zorder=2,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.8},
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch image from {url}: {e}")
        ax.text(
            x + width / 2,
            y + height / 2,
            f"[Image Fetch Error]\n{url[:30]}...",
            color="red",
            ha="center",
            va="center",
            fontsize=8,
            zorder=2,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.8},
        )
    except PILImage.UnidentifiedImageError:
        logger.warning(f"Cannot identify image file from {url}.")
        ax.text(
            x + width / 2,
            y + height / 2,
            f"[Invalid Image Format]\n{url[:30]}...",
            color="red",
            ha="center",
            va="center",
            fontsize=8,
            zorder=2,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.8},
        )
    except Exception as e:
        logger.error(f"Unexpected error rendering image {url}: {e}")
        ax.text(
            x + width / 2,
            y + height / 2,
            f"[Image Render Error]\n{url[:30]}...",
            color="red",
            ha="center",
            va="center",
            fontsize=8,
            zorder=2,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "alpha": 0.8},
        )


def format_list_for_display(element: ListElement) -> str:
    """
    Enhanced formatting of list items for display, including better indentation.
    """
    if not element.items:
        return ""

    lines = []
    is_ordered = element.element_type.value == "ordered_list"

    def _format_items(items_list, level):
        for i, item in enumerate(items_list):
            prefix = "  " * level
            if is_ordered:
                prefix += f"{i+1}. "
            else:
                prefix += "• "

            # Truncate long items for display
            item_text = item.text
            if len(item_text) > 100:
                item_text = item_text[:97] + "..."

            lines.append(prefix + item_text)

            if item.children:
                _format_items(item.children, level + 1)

    _format_items(element.items, 0)
    return "\n".join(lines)


def render_element_metadata(ax, element, el_idx, element_type_value, pos_x, pos_y):
    """Renders element metadata (type, ID) as a small badge."""
    metadata_label = f"ID:{getattr(element, 'object_id', 'N/A')}"
    ax.text(
        pos_x + 2,
        pos_y + 2,
        f"{el_idx}:{element_type_value}\n{metadata_label}",
        fontsize=5,
        color="black",
        alpha=0.9,
        va="top",
        ha="left",
        zorder=4,
        bbox={"boxstyle": "round,pad=0.1", "fc": "yellow", "alpha": 0.5, "ec": "grey"},
    )
