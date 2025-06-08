"""Renderer for slide metadata."""

import re


def render_metadata(ax, slide, slide_width):
    """
    Render slide metadata like layout, notes, etc.

    Args:
        ax: Matplotlib axis
        slide: The slide to render metadata for
        slide_width: Width of the slide in points
    """
    metadata_text = []

    # Add layout if available
    if hasattr(slide, "layout") and slide.layout:
        layout_value = getattr(slide.layout, "value", slide.layout)
        metadata_text.append(f"Layout: {layout_value}")

    # Add note about speaker notes if present
    if hasattr(slide, "notes") and slide.notes:
        note_length = len(slide.notes)
        metadata_text.append(f"Speaker notes: {note_length} chars")

    # Add footer info if present
    if hasattr(slide, "footer") and slide.footer:
        clean_footer = re.sub(r"<!--.*?-->", "", slide.footer, flags=re.DOTALL)
        if clean_footer.strip():
            # Truncate footer if too long
            if len(clean_footer) > 30:
                clean_footer = clean_footer[:27] + "..."
            metadata_text.append(f'Footer: "{clean_footer}"')

    # Add transition info if present
    if hasattr(slide, "transition") and slide.transition:
        metadata_text.append(f"Transition: {slide.transition}")

    # Add background info if present
    if hasattr(slide, "background") and slide.background:
        if isinstance(slide.background, dict):
            # Convert dict to compact string
            bg_info = ", ".join(f"{k}:{v}" for k, v in slide.background.items())
            metadata_text.append(f"Background: {bg_info}")
        else:
            metadata_text.append(f"Background: {slide.background}")

    # Render metadata if we have any
    if metadata_text:
        ax.text(
            slide_width - 10,
            10,  # Near top-right
            "\n".join(metadata_text),
            fontsize=6,
            color="dimgray",
            alpha=0.8,
            va="top",
            ha="right",
            bbox={
                "boxstyle": "round,pad=0.3",
                "facecolor": "white",
                "alpha": 0.7,
                "edgecolor": "lightgray",
            },
            zorder=5,
        )
