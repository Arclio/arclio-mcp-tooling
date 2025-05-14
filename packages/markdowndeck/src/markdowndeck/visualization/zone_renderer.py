"""Renderer for slide zones (header, body, footer)."""

import matplotlib.patches as patches


def render_zones(ax, slide_width, slide_height):
    """
    Render the header, body, and footer zones of a slide.

    Args:
        ax: Matplotlib axis
        slide_width: Width of the slide in points
        slide_height: Height of the slide in points
    """
    # Define zone heights
    header_zone_height = 80
    footer_zone_height = 30
    body_zone_height = slide_height - header_zone_height - footer_zone_height

    # Render header zone
    header_zone = patches.Rectangle(
        (0, 0),
        slide_width,
        header_zone_height,
        linewidth=1,
        edgecolor="blue",
        facecolor="none",
        linestyle="--",
        alpha=0.3,
        zorder=0,
    )
    ax.add_patch(header_zone)

    # Add small label for header zone
    ax.text(
        5,
        5,
        "Header",
        fontsize=6,
        color="blue",
        alpha=0.5,
        bbox={"boxstyle": "round,pad=0.1", "facecolor": "white", "alpha": 0.5},
        zorder=0,
    )

    # Render body zone
    body_zone = patches.Rectangle(
        (0, header_zone_height),
        slide_width,
        body_zone_height,
        linewidth=1,
        edgecolor="green",
        facecolor="none",
        linestyle="--",
        alpha=0.3,
        zorder=0,
    )
    ax.add_patch(body_zone)

    # Add small label for body zone
    ax.text(
        5,
        header_zone_height + 5,
        "Body",
        fontsize=6,
        color="green",
        alpha=0.5,
        bbox={"boxstyle": "round,pad=0.1", "facecolor": "white", "alpha": 0.5},
        zorder=0,
    )

    # Render footer zone
    footer_zone = patches.Rectangle(
        (0, slide_height - footer_zone_height),
        slide_width,
        footer_zone_height,
        linewidth=1,
        edgecolor="red",
        facecolor="none",
        linestyle="--",
        alpha=0.3,
        zorder=0,
    )
    ax.add_patch(footer_zone)

    # Add small label for footer zone
    ax.text(
        5,
        slide_height - footer_zone_height + 5,
        "Footer",
        fontsize=6,
        color="red",
        alpha=0.5,
        bbox={"boxstyle": "round,pad=0.1", "facecolor": "white", "alpha": 0.5},
        zorder=0,
    )
