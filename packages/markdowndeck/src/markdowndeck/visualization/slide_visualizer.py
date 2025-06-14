import logging

import matplotlib.pyplot as plt

from markdowndeck.layout import LayoutManager
from markdowndeck.models import Section
from markdowndeck.visualization.renderer import (
    render_elements,
    render_metadata_overlay,
    render_sections,
    render_slide_background,
)

logger = logging.getLogger(__name__)


class SlideVisualizer:
    """
    Visualizes slides with detailed layout representation for debugging,
    fully aligned with the current system architecture.
    """

    def __init__(self, slide_width=720, slide_height=405):
        """Initialize with standard slide dimensions."""
        self.slide_width = slide_width
        self.slide_height = slide_height
        self.layout_manager = LayoutManager(slide_width, slide_height)

    def visualize(
        self,
        slides_or_deck,
        show_sections=True,
        display=True,
        save_to=None,
    ):
        """
        Visualize one or more slides.

        Args:
            slides_or_deck: A single Slide object, a list of Slides, or a Deck.
            show_sections: If True, renders section and subsection boundaries.
            display: If True, shows the plot immediately.
            save_to: If a filename is provided, saves the plot to that file.
        """
        slides = self._get_slides_from_input(slides_or_deck)
        if not slides:
            logger.warning("No slides to visualize.")
            return

        num_slides = len(slides)
        fig, axes = self._setup_figure(num_slides)

        for i, slide in enumerate(slides):
            self._render_single_slide(axes[i], slide, i, show_sections)

        self._finalize_figure(fig, axes, num_slides, save_to, display)

    def _get_slides_from_input(self, slides_or_deck):
        """Standardizes input to a list of slides."""
        if hasattr(slides_or_deck, "slides"):
            return slides_or_deck.slides
        return slides_or_deck if isinstance(slides_or_deck, list) else [slides_or_deck]

    def _setup_figure(self, num_slides):
        """Sets up the Matplotlib figure and axes."""
        cols = 1
        rows = num_slides
        aspect_ratio = self.slide_width / self.slide_height
        fig_width = 8
        fig_height = (fig_width / aspect_ratio) * rows + (1 * rows)

        fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height), squeeze=False)
        return fig, axes.flatten()

    def _render_single_slide(self, ax, slide, slide_idx, show_sections):
        """Renders a single slide onto a given Matplotlib axis."""
        ax.set_xlim(0, self.slide_width)
        ax.set_ylim(self.slide_height, 0)  # Inverted Y-axis like most GUI coordinates
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect("equal", adjustable="box")
        ax.set_facecolor("#e0e0e0")

        render_slide_background(ax, slide, self.slide_width, self.slide_height)
        render_metadata_overlay(ax, slide, slide_idx, self.slide_width)

        # REFACTORED: Intelligently determine what to render based on slide state
        elements_to_render = []
        root_section_to_render = None

        if getattr(slide, "renderable_elements", None):
            # Finalized state: `renderable_elements` is the source of truth
            elements_to_render = slide.renderable_elements
            logger.debug(f"Slide {slide_idx + 1} is Finalized. Rendering from `renderable_elements`.")
        elif getattr(slide, "root_section", None):
            # Positioned state: Traverse root_section to find elements
            def extract_elements(section):
                _elements = []
                for child in section.children:
                    if isinstance(child, Section):
                        _elements.extend(extract_elements(child))
                    else:
                        _elements.append(child)
                return _elements

            elements_to_render = extract_elements(slide.root_section)
            # Also render meta-elements from the `elements` inventory
            elements_to_render.extend([e for e in slide.elements if e.element_type.value in ["title", "subtitle", "footer"]])
            root_section_to_render = slide.root_section
            logger.debug(f"Slide {slide_idx + 1} is Positioned. Rendering from `root_section` and meta-elements.")
        else:
            # Unpositioned or simple state: use the `elements` inventory
            elements_to_render = slide.elements
            logger.debug(f"Slide {slide_idx + 1} is Unpositioned. Rendering from `elements`.")

        # Render section boundaries if requested and available
        if show_sections and root_section_to_render:
            render_sections(ax, root_section_to_render)

        # Render the elements themselves
        render_elements(ax, elements_to_render)

    def _finalize_figure(self, fig, axes, num_slides, save_to, display):
        """Handles saving or displaying the final figure."""
        for j in range(num_slides, len(axes)):
            axes[j].set_visible(False)
        fig.tight_layout(pad=3.0, h_pad=4.0)

        if save_to:
            fig.savefig(save_to, dpi=150, bbox_inches="tight")
            logger.info(f"Visualization saved to {save_to}")
        if display:
            plt.show()

        plt.close(fig)
