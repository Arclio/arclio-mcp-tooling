"""
Main slide visualizer class for MarkdownDeck.

This module provides the SlideVisualizer, a powerful tool for inspecting
the output of the layout engine before generating API calls. It's designed
to work with the refactored, decoupled architecture of MarkdownDeck.

Enhanced with robust fallback handling for elements missing layout data.
"""

import logging

import matplotlib.pyplot as plt

from markdowndeck.layout import LayoutManager
from markdowndeck.models import ElementType
from markdowndeck.visualization.renderer import (
    render_elements,
    render_layout_zones,
    render_metadata_overlay,
    render_sections,
    render_slide_background,
)

logger = logging.getLogger(__name__)


class SlideVisualizer:
    """
    Visualizes slides with detailed layout representation for debugging.

    This class accurately renders the output of the LayoutManager, showing
    slide zones, section boundaries, and element positions and sizes.
    Enhanced with robust fallback handling for elements missing layout data.
    """

    def __init__(self, slide_width=720, slide_height=405):
        """Initialize with standard slide dimensions."""
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.aspect_ratio = slide_width / slide_height
        self.layout_manager = LayoutManager(slide_width, slide_height)

    def visualize(
        self,
        slides_or_deck,
        show_zones=True,
        show_sections=True,
        show_metadata=True,
        display=True,
        save_to=None,
    ):
        """
        Visualize one or more slides.

        Args:
            slides_or_deck: A single Slide object, a list of Slides, or a Deck.
            show_zones: If True, renders header/body/footer zone boundaries.
            show_sections: If True, renders section and subsection boundaries.
            show_metadata: If True, renders slide-level metadata.
            display: If True, shows the plot immediately.
            save_to: If a filename is provided, saves the plot to that file.

        Returns:
            The matplotlib Figure object if display is False and save_to is None.
        """
        if hasattr(slides_or_deck, "slides"):
            slides = slides_or_deck.slides
        elif isinstance(slides_or_deck, list):
            slides = slides_or_deck
        else:
            slides = [slides_or_deck]

        if not slides:
            logger.warning("No slides to visualize.")
            return None

        num_slides = len(slides)

        # TASK_003: Always use single column layout for better slide deck review
        cols = 1
        rows = num_slides

        # Warn if visualizing many slides (may result in very large output)
        if num_slides > 10:
            logger.warning(
                f"Visualizing {num_slides} slides in single column - output may be very large. "
                f"Consider debugging a smaller subset of slides for better performance."
            )

        fig_width = 8 * cols  # Keep 8 inches width for readability
        fig_height = (fig_width / cols / self.aspect_ratio) * rows
        fig, axes = plt.subplots(
            rows, cols, figsize=(fig_width, fig_height), squeeze=False
        )
        axes = axes.flatten()

        for i, slide in enumerate(slides):
            ax = axes[i]
            self._render_single_slide(
                ax, slide, i, show_zones, show_sections, show_metadata
            )

        for j in range(num_slides, len(axes)):
            axes[j].set_visible(False)

        fig.tight_layout(pad=2.0)

        if save_to:
            fig.savefig(save_to, dpi=150)
            logger.info(f"Visualization saved to {save_to}")
            plt.close(fig)
            return save_to

        if display:
            plt.show()
            plt.close(fig)
            return None

        return fig

    def _render_single_slide(
        self, ax, slide, slide_idx, show_zones, show_sections, show_metadata
    ):
        """Renders a single slide onto a given Matplotlib axis with enhanced debugging."""
        ax.set_xlim(-10, self.slide_width + 10)
        ax.set_ylim(self.slide_height + 10, -10)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"Slide {slide_idx + 1}: {slide.object_id}", fontsize=10)
        ax.grid(True, linestyle=":", linewidth=0.5, color="lightgray")

        render_slide_background(ax, slide, self.slide_width, self.slide_height)

        if show_zones:
            render_layout_zones(ax, self.layout_manager)
        if show_sections and hasattr(slide, "sections"):
            render_sections(ax, slide.sections)

        # Enhanced debugging - check finalized IR state
        total_renderable_elements = len(getattr(slide, "renderable_elements", []))
        total_sections = len(getattr(slide, "sections", []))
        logger.info(
            f"Slide {slide_idx + 1}: {total_renderable_elements} renderable elements, {total_sections} sections"
        )

        # Per TASK_005: Use renderable_elements as authoritative source after OverflowManager
        all_elements = getattr(slide, "renderable_elements", [])

        # Check for slides that haven't been processed by OverflowManager
        if not all_elements and total_sections > 0:
            logger.warning(
                f"Slide {slide_idx + 1} has empty renderable_elements but {total_sections} sections. "
                "This slide may not have been processed by the OverflowManager yet."
            )

        if all_elements:
            logger.info(
                f"Rendering {len(all_elements)} elements from slide.renderable_elements"
            )

            # Debug each element's positioning state
            for element in all_elements:
                self._debug_element_state_detailed(element)

            # Render all elements with fallback handling
            self._render_elements_with_fallbacks(
                ax, all_elements, "renderable-elements"
            )
        else:
            logger.info(
                "No elements found in slide.renderable_elements - slide may be empty or requires OverflowManager processing"
            )

        if show_metadata:
            render_metadata_overlay(ax, slide, slide_idx)

    def _debug_element_state_detailed(self, element):
        """Enhanced debug helper to log detailed element positioning state."""
        element_type = getattr(element, "element_type", "UNKNOWN")
        element_id = getattr(element, "object_id", "no_id")

        # Get actual attribute values with type information
        position_attr = getattr(element, "position", "MISSING_ATTR")
        size_attr = getattr(element, "size", "MISSING_ATTR")

        position_type = type(position_attr).__name__
        size_type = type(size_attr).__name__

        # Additional context about the element
        text_content = (
            getattr(element, "text", "")[:50] + "..."
            if len(getattr(element, "text", "")) > 50
            else getattr(element, "text", "")
        )

        logger.warning(
            f"PIPELINE_DEBUG: Element {element_type} ({element_id}): "
            f"position={position_attr} (type: {position_type}), "
            f"size={size_attr} (type: {size_type}), "
            f"content_preview='{text_content}'"
        )

        # Log if this element has any parent references that might have position data
        if hasattr(element, "_parent_section"):
            parent_section = element._parent_section
            parent_pos = getattr(parent_section, "position", "NO_PARENT_POS")
            parent_size = getattr(parent_section, "size", "NO_PARENT_SIZE")
            logger.warning(
                f"PIPELINE_DEBUG: Element {element_type} has parent section with "
                f"position={parent_pos}, size={parent_size}"
            )

    def _render_elements_with_fallbacks(self, ax, elements, context=""):
        """Render elements with robust fallback handling for missing layout data."""
        if not elements:
            return

        logger.info(f"Rendering {len(elements)} elements in context: {context}")

        # Pre-process elements to ensure they have valid position and size
        processed_elements = []

        for i, element in enumerate(elements):
            # Create a copy to avoid modifying the original
            element_copy = self._create_element_with_fallbacks(element, i, context)
            processed_elements.append(element_copy)

        # Use the existing renderer with processed elements
        render_elements(ax, processed_elements)

    def _create_element_with_fallbacks(self, element, index, context):
        """Create an element copy with fallback position and size if missing."""
        from copy import deepcopy

        element_copy = deepcopy(element)

        # Check and fix position
        if not self._has_valid_position(element_copy):
            fallback_position = self._get_fallback_position(
                element_copy, index, context
            )
            element_copy.position = fallback_position
            logger.info(
                f"Applied fallback position {fallback_position} to {element_copy.element_type}"
            )

        # Check and fix size
        if not self._has_valid_size(element_copy):
            fallback_size = self._get_fallback_size(element_copy)
            element_copy.size = fallback_size
            logger.info(
                f"Applied fallback size {fallback_size} to {element_copy.element_type}"
            )

        return element_copy

    def _has_valid_position(self, element):
        """Check if element has a valid position attribute."""
        return (
            hasattr(element, "position")
            and element.position is not None
            and isinstance(element.position, tuple | list)
            and len(element.position) >= 2
            and all(isinstance(x, int | float) for x in element.position[:2])
        )

    def _has_valid_size(self, element):
        """Check if element has a valid size attribute."""
        return (
            hasattr(element, "size")
            and element.size is not None
            and isinstance(element.size, tuple | list)
            and len(element.size) >= 2
            and all(isinstance(x, int | float) for x in element.size[:2])
            and element.size[0] > 0
            and element.size[1] > 0
        )

    def _get_fallback_position(self, element, index, context):
        """Get fallback position based on element type and context."""
        element_type = getattr(element, "element_type", None)

        if element_type == ElementType.TITLE:
            return (60, 60)  # Header zone
        if element_type == ElementType.SUBTITLE:
            return (60, 100)  # Below title
        if element_type == ElementType.FOOTER:
            return (60, 340)  # Footer zone
        # Body elements - distribute vertically
        start_y = 160  # Start of body zone
        spacing = 80
        x_offset = 60
        return (x_offset, start_y + (index * spacing))

    def _get_fallback_size(self, element):
        """Get fallback size based on element type."""
        element_type = getattr(element, "element_type", None)

        if element_type == ElementType.TITLE:
            return (600, 40)
        if element_type == ElementType.SUBTITLE:
            return (500, 30)
        if element_type == ElementType.FOOTER:
            return (600, 25)
        if element_type == ElementType.TEXT:
            return (500, 60)
        if element_type in (ElementType.BULLET_LIST, ElementType.ORDERED_LIST):
            return (500, 100)
        if element_type == ElementType.TABLE:
            return (500, 120)
        if element_type == ElementType.CODE:
            return (500, 80)
        if element_type == ElementType.IMAGE:
            return (300, 200)
        if element_type == ElementType.QUOTE:
            return (480, 70)
        return (400, 50)  # Generic fallback
