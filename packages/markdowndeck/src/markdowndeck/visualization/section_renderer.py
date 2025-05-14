"""Renderer for slide sections."""

import matplotlib.patches as patches

# Colors for section levels
SECTION_COLORS = ["red", "blue", "green", "purple", "orange"]


def render_sections(ax, sections, parent_color_idx=0):
    """
    Render sections and subsections in a slide.

    Args:
        ax: Matplotlib axis
        sections: List of sections to render
        parent_color_idx: Color index for parent section (for nesting)
    """
    for idx, section in enumerate(sections):
        if (
            not hasattr(section, "position")
            or not section.position
            or not hasattr(section, "size")
            or not section.size
        ):
            continue

        # Get section properties
        pos_x, pos_y = section.position
        size_w, size_h = section.size

        # Choose color based on nesting level
        color_idx = (parent_color_idx + 1) % len(SECTION_COLORS)
        section_color = SECTION_COLORS[color_idx]

        # Draw section boundary (dotted line, very light)
        rect = patches.Rectangle(
            (pos_x, pos_y),
            size_w,
            size_h,
            linewidth=1,
            edgecolor=section_color,
            facecolor="none",
            linestyle="-.",
            alpha=0.4,
            zorder=0.5,
        )
        ax.add_patch(rect)

        # Create section label
        section_label = get_section_label(section, idx)

        # Add section label as a small tag in the corner
        ax.text(
            pos_x + 2,
            pos_y + 2,
            section_label,
            fontsize=6,
            color=section_color,
            bbox={
                "boxstyle": "round,pad=0.1",
                "facecolor": "white",
                "alpha": 0.7,
                "edgecolor": section_color,
            },
            va="top",
            ha="left",
            zorder=0.7,
        )

        # Recursively render subsections
        if hasattr(section, "subsections") and section.subsections:
            render_sections(ax, section.subsections, color_idx)


def get_section_label(section, idx):
    """
    Create a concise label for a section.

    Args:
        section: The section to label
        idx: Index of the section

    Returns:
        Concise section label
    """
    # Start with a basic label
    section_label = f"Sec{idx}"

    # Add section ID if available
    if hasattr(section, "id") and section.id:
        section_label = f"{section.id}"

    # Add type if available
    if hasattr(section, "type") and section.type:
        section_label += f":{section.type}"

    # Add compact representation of directives if present
    if hasattr(section, "directives") and section.directives:
        # Limit to just a few key directives to keep it compact
        key_directives = []

        if "cols" in section.directives:
            key_directives.append(f"c{section.directives['cols']}")

        if "rows" in section.directives:
            key_directives.append(f"r{section.directives['rows']}")

        if "width" in section.directives:
            key_directives.append(f"w{section.directives['width']}")

        if "align" in section.directives:
            key_directives.append(f"a{section.directives['align']}")

        if key_directives:
            section_label += f" [{','.join(key_directives)}]"

    return section_label
