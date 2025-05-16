import logging
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from io import BytesIO
import requests
from PIL import Image as PILImage
import numpy as np
import math

# Import the enhanced renderers
from markdowndeck.visualization.element_renderer import render_elements
from markdowndeck.visualization.metadata_renderer import render_metadata
from markdowndeck.visualization.section_renderer import render_sections
from markdowndeck.visualization.zone_renderer import render_zones

logger = logging.getLogger(__name__)


class SlideVisualizer:
    """Visualizes slides with detailed content representation for debugging layout issues."""

    def __init__(self):
        """Initialize the slide visualizer."""
        self.slide_width = 720  # Standard slide width in points (Google Slides default)
        self.slide_height = 405  # Standard slide height in points (16:9 aspect ratio)

    def visualize(
        self,
        slides_or_deck,
        figsize=None,  # Default to None for auto-sizing
        scale_factor=1.0,  # Scale factor to adjust overall size
        max_height=100,  # Maximum height in inches to prevent excessive figure size
        layout_mode="vertical",  # 'vertical', 'grid', or 'compact'
        max_slides=None,  # Maximum number of slides to display (None for all)
        show_zones=True,
        show_metadata=True,  # Controls metadata badges on elements and slide info
        display=True,
        dpi=100,  # DPI setting for the figure
        vertical_spacing=0.1,  # Vertical spacing between slides (proportion)
        horizontal_spacing=0.1,  # Horizontal spacing between slides in grid layouts
        tight_layout=False,  # Use tight_layout instead of constrained_layout
    ):
        """
        Visualize slides with improved sizing and layout options.

        Args:
            slides_or_deck: A slide, list of slides, or deck object
            figsize: Custom figure size as (width, height) in inches, or None for auto-sizing
            scale_factor: Multiplier to adjust the overall figure size
            max_height: Maximum height of the figure in inches (prevents excessive memory usage)
            layout_mode: How to arrange multiple slides - 'vertical', 'grid', or 'compact'
            max_slides: Maximum number of slides to display (None for all)
            show_zones: Whether to show header/body/footer zones
            show_metadata: Whether to show element metadata
            display: Whether to immediately display the figure
            dpi: DPI setting for the figure
            vertical_spacing: Spacing between slides vertically (proportion)
            horizontal_spacing: Spacing between slides horizontally in grid layouts
            tight_layout: Use tight_layout instead of constrained_layout (may help with spacing)

        Returns:
            The matplotlib figure if display=False, otherwise None
        """
        if hasattr(slides_or_deck, "slides"):  # Deck object
            slides = slides_or_deck.slides
        elif isinstance(slides_or_deck, list):  # List of slides
            slides = slides_or_deck
        else:  # Single slide
            slides = [slides_or_deck]

        num_slides = len(slides)
        if num_slides == 0:
            logger.warning("No slides to visualize.")
            return None

        # Apply max_slides limit if specified
        if max_slides is not None and max_slides > 0 and num_slides > max_slides:
            logger.info(
                f"Limiting visualization to {max_slides} of {num_slides} slides"
            )
            slides = slides[:max_slides]
            num_slides = len(slides)

        slide_aspect_ratio = self.slide_width / self.slide_height

        # Auto-calculate figure dimensions based on layout mode
        if figsize is None:
            # Base sizes - will be adjusted by layout mode
            if layout_mode == "vertical":
                # Calculate base width and height per slide
                base_width = 15 * scale_factor  # Default width in inches
                base_height_per_slide = (base_width / slide_aspect_ratio) * 1.05

                # Calculate grid dimensions
                cols = 1
                rows = num_slides

                # Calculate total figure size with minimal padding
                # Only add spacing between slides, not at edges
                spacing_factor = (
                    vertical_spacing * (num_slides - 1) / num_slides
                    if num_slides > 1
                    else 0
                )
                fig_width = base_width
                fig_height = min(
                    base_height_per_slide * rows * (1 + spacing_factor), max_height
                )

            elif layout_mode == "grid":
                # Grid layout aims for a more square overall figure
                base_width = 10 * scale_factor  # Smaller default for grid

                # Calculate optimal grid dimensions
                cols = max(1, int(math.sqrt(num_slides)))
                rows = math.ceil(num_slides / cols)

                # Calculate total figure size with minimal padding
                horiz_spacing_factor = (
                    horizontal_spacing * (cols - 1) / cols if cols > 1 else 0
                )
                vert_spacing_factor = (
                    vertical_spacing * (rows - 1) / rows if rows > 1 else 0
                )

                fig_width = base_width * cols * (1 + horiz_spacing_factor)
                fig_height = min(
                    (base_width / slide_aspect_ratio)
                    * rows
                    * (1 + vert_spacing_factor),
                    max_height,
                )

            else:  # "compact" or any other value
                # Compact tries to fit more slides by reducing base size
                base_width = 8 * scale_factor
                base_height_per_slide = (base_width / slide_aspect_ratio) * 1.02

                # For compact, use 2 columns when more than 3 slides
                cols = 2 if num_slides > 3 else 1
                rows = math.ceil(num_slides / cols)

                # Calculate total figure size with minimal padding
                horiz_spacing_factor = (
                    horizontal_spacing * (cols - 1) / cols if cols > 1 else 0
                )
                vert_spacing_factor = (
                    vertical_spacing * (rows - 1) / rows if rows > 1 else 0
                )

                fig_width = base_width * cols * (1 + horiz_spacing_factor)
                fig_height = min(
                    base_height_per_slide * rows * (1 + vert_spacing_factor), max_height
                )
        else:
            # Use provided figsize with adjustment for scale_factor
            if len(figsize) == 2:
                fig_width, fig_height = figsize
                fig_width *= scale_factor

                # If height is None, auto-calculate
                if fig_height is None:
                    if layout_mode == "grid":
                        cols = max(1, int(math.sqrt(num_slides)))
                        rows = math.ceil(num_slides / cols)
                    elif layout_mode == "compact":
                        cols = 2 if num_slides > 3 else 1
                        rows = math.ceil(num_slides / cols)
                    else:  # vertical
                        cols = 1
                        rows = num_slides

                    # Base height per slide, scaled
                    base_height_per_slide = (
                        fig_width / slide_aspect_ratio / cols
                    ) * 1.05

                    # Add minimal spacing between slides
                    spacing_height = (
                        base_height_per_slide * vertical_spacing * (rows - 1)
                    )
                    fig_height = min(
                        base_height_per_slide * rows + spacing_height, max_height
                    )
                else:
                    fig_height *= scale_factor
                    fig_height = min(fig_height, max_height)
            else:
                # Default if figsize format is incorrect
                fig_width = 15 * scale_factor
                fig_height = min(10 * num_slides * scale_factor, max_height)
                logger.warning("Invalid figsize format. Using defaults.")

        # For vertical layout, ensure height is sufficient for all slides
        if layout_mode == "vertical" and fig_height == max_height and num_slides > 3:
            logger.warning(
                f"Figure height capped at {max_height} inches; some slides may be compressed. "
                f"Consider using layout_mode='grid' or 'compact' for better visualization of many slides."
            )

        # Create figure based on layout preference
        if tight_layout:
            # Use tight_layout which sometimes works better for spacing
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
        else:
            # Use constrained_layout (default)
            fig = plt.figure(
                figsize=(fig_width, fig_height), dpi=dpi, constrained_layout=True
            )

        # Setup grid layout based on mode with minimal spacing
        if layout_mode == "grid" or (layout_mode == "compact" and num_slides > 3):
            # Use a grid layout
            cols = max(1, min(3, int(math.sqrt(num_slides))))  # Cap at 3 columns max
            rows = math.ceil(num_slides / cols)

            # Create the grid with minimal spacing
            gs = gridspec.GridSpec(
                rows,
                cols,
                figure=fig,
                hspace=vertical_spacing,  # Reduced vertical spacing
                wspace=horizontal_spacing,  # Reduced horizontal spacing
            )
        else:
            # Use vertical layout (default)
            gs = gridspec.GridSpec(
                num_slides,
                1,
                figure=fig,
                hspace=vertical_spacing,  # Reduced vertical spacing
            )

        # Render each slide
        for slide_idx, slide in enumerate(slides):
            if layout_mode == "grid" or (layout_mode == "compact" and num_slides > 3):
                row = slide_idx // cols
                col = slide_idx % cols
                ax = fig.add_subplot(gs[row, col])
            else:
                ax = fig.add_subplot(gs[slide_idx])

            self._setup_slide_axis(ax, slide, slide_idx)

            if show_zones:
                render_zones(ax, self.slide_width, self.slide_height)

            if hasattr(slide, "sections") and slide.sections:
                render_sections(ax, slide.sections)

            # Call the enhanced element renderer
            render_elements(
                ax, slide.elements, self.slide_width, self.slide_height, show_metadata
            )

            if show_metadata:  # This is for slide-level metadata text box
                render_metadata(ax, slide, self.slide_width)

        # Add a title if showing a subset of slides
        if max_slides is not None and max_slides < len(
            slides_or_deck.slides
            if hasattr(slides_or_deck, "slides")
            else slides_or_deck
        ):
            fig.suptitle(
                f"Showing {len(slides)} of {len(slides_or_deck.slides if hasattr(slides_or_deck, 'slides') else slides_or_deck)} slides",
                fontsize=12,
            )

        # Apply tight_layout if selected and not using constrained_layout
        if tight_layout:
            try:
                plt.tight_layout(
                    pad=0.5, h_pad=vertical_spacing * 20, w_pad=horizontal_spacing * 20
                )
            except Exception as e:
                logger.warning(f"Could not apply tight_layout perfectly: {e}")

        if display:
            plt.show()
            plt.close(fig)  # Clean up to prevent memory leaks
            return None
        return fig

    def _setup_slide_axis(self, ax, slide, slide_idx):
        """Set up the axis for a slide visualization with background support."""
        import matplotlib.patches as patches  # Keep import local if only used here

        title_text = f"Slide {slide_idx + 1} (ID: {slide.object_id or 'N/A'})"
        if hasattr(slide, "title") and slide.title:
            slide_title_preview = (
                slide.title[:40] + "..." if len(slide.title) > 40 else slide.title
            )
            title_text += f'\nTitle: "{slide_title_preview}"'

        # Reduce title padding to minimize gaps
        ax.set_title(title_text, fontsize=10, pad=5)

        # Trim axis limits to reduce padding
        ax.set_xlim(-10, self.slide_width + 10)
        ax.set_ylim(self.slide_height + 10, -10)  # Inverted Y-axis
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, linestyle=":", alpha=0.4)

        # Default slide background
        face_color = "#FEFEFE"  # Slightly off-white

        # Check for slide background
        if hasattr(slide, "background") and slide.background:
            # Handle different background types
            if isinstance(slide.background, dict):
                bg_type = slide.background.get("type")
                bg_value = slide.background.get("value")

                if bg_type == "color" and bg_value:
                    # For color backgrounds
                    face_color = bg_value
                elif bg_type == "image" and bg_value:
                    # For image backgrounds, we'll try to fetch and render the image
                    try:
                        response = requests.get(bg_value, stream=True, timeout=5)
                        response.raise_for_status()

                        img = PILImage.open(BytesIO(response.content))
                        img_array = np.array(img)

                        # Calculate aspect ratio and position to fill the slide
                        img_aspect = img.width / img.height
                        slide_aspect = self.slide_width / self.slide_height

                        if img_aspect > slide_aspect:  # Image is wider than slide
                            height = self.slide_height
                            width = height * img_aspect
                            x_offset = (width - self.slide_width) / 2
                            ax.imshow(
                                img_array,
                                extent=[
                                    -x_offset,
                                    width - x_offset,
                                    self.slide_height,
                                    0,
                                ],
                                aspect="auto",
                                zorder=0,
                                alpha=0.3,
                            )  # Semi-transparent
                        else:  # Image is taller than slide
                            width = self.slide_width
                            height = width / img_aspect
                            y_offset = (height - self.slide_height) / 2
                            ax.imshow(
                                img_array,
                                extent=[
                                    0,
                                    self.slide_width,
                                    height - y_offset,
                                    -y_offset,
                                ],
                                aspect="auto",
                                zorder=0,
                                alpha=0.3,
                            )  # Semi-transparent

                        # Still add the boundary rectangle on top for clarity
                        face_color = (
                            "none"  # Make rectangle transparent since we have an image
                        )

                    except Exception as e:
                        logger.warning(f"Failed to load background image: {e}")
                        # Fall back to default background color with error indication
                        face_color = "#FFEEEE"  # Light red to indicate error
            elif isinstance(slide.background, str):
                # Direct string background might be a color or a URL
                if slide.background.startswith(("http://", "https://", "www.")):
                    # It's a URL, likely for an image background
                    try:
                        # Try to load the image
                        response = requests.get(
                            slide.background, stream=True, timeout=5
                        )
                        response.raise_for_status()

                        img = PILImage.open(BytesIO(response.content))
                        img_array = np.array(img)

                        # Calculate aspect ratio and position to fill the slide
                        img_aspect = img.width / img.height
                        slide_aspect = self.slide_width / self.slide_height

                        if img_aspect > slide_aspect:  # Image is wider than slide
                            height = self.slide_height
                            width = height * img_aspect
                            x_offset = (width - self.slide_width) / 2
                            ax.imshow(
                                img_array,
                                extent=[
                                    -x_offset,
                                    width - x_offset,
                                    self.slide_height,
                                    0,
                                ],
                                aspect="auto",
                                zorder=0,
                                alpha=0.3,
                            )  # Semi-transparent
                        else:  # Image is taller than slide
                            width = self.slide_width
                            height = width / img_aspect
                            y_offset = (height - self.slide_height) / 2
                            ax.imshow(
                                img_array,
                                extent=[
                                    0,
                                    self.slide_width,
                                    height - y_offset,
                                    -y_offset,
                                ],
                                aspect="auto",
                                zorder=0,
                                alpha=0.3,
                            )  # Semi-transparent

                        # Still add the boundary rectangle on top for clarity
                        face_color = (
                            "none"  # Make rectangle transparent since we have an image
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load background image URL: {e}")
                        # Fall back to default background color with error indication
                        face_color = "#FFEEEE"  # Light red to indicate error
                else:
                    # Treat it as a color
                    face_color = slide.background

        # Make sure face_color is not a URL before using it for Rectangle
        if isinstance(face_color, str) and face_color.startswith(
            ("http://", "https://", "www.")
        ):
            # If face_color is still a URL string (which shouldn't happen with our previous fix),
            # force it to a safe default color
            logger.warning(
                f"Found URL as face_color, replacing with safe default: {face_color}"
            )
            face_color = "#FFEEEE"  # Light red as an error indicator

        # Add slide boundary rectangle with error handling
        try:
            slide_boundary = patches.Rectangle(
                (0, 0),
                self.slide_width,
                self.slide_height,
                linewidth=1.0,
                edgecolor="black",
                facecolor=face_color,
                zorder=0.5,  # Above background image but below content
            )
        except ValueError as e:
            # If there's still an error with face_color, use a safe fallback
            logger.warning(f"Error creating Rectangle with color {face_color}: {e}")
            slide_boundary = patches.Rectangle(
                (0, 0),
                self.slide_width,
                self.slide_height,
                linewidth=1.0,
                edgecolor="black",
                facecolor="#FFEEEE",  # Safe fallback color
                zorder=0.5,
            )
        ax.add_patch(slide_boundary)

        # Reduce fontsize of labels to save space
        ax.set_xlabel("X Position (points)", fontsize=6)
        ax.set_ylabel("Y Position (points)", fontsize=6)
        ax.tick_params(axis="both", which="major", labelsize=5)

        # Reduce padding around the axis
        ax.set_xmargin(0.01)
        ax.set_ymargin(0.01)

    def save_visualization(
        self, slides_or_deck, filename="slide_visualization.png", **kwargs
    ):
        """
        Save the visualization to a file instead of displaying it.

        Args:
            slides_or_deck: A slide, list of slides, or deck object
            filename: Path to save the visualization
            **kwargs: Additional arguments to pass to visualize()

        Returns:
            Path to the saved file
        """
        # Ensure display is False to prevent showing the plot
        kwargs["display"] = False

        # Create the visualization figure
        fig = self.visualize(slides_or_deck, **kwargs)

        if fig:
            # Save the figure with tight bbox to minimize margins
            fig.savefig(filename, bbox_inches="tight", pad_inches=0.1)
            plt.close(fig)  # Clean up
            logger.info(f"Visualization saved to {filename}")
            return filename
        else:
            logger.error("Failed to create visualization to save")
            return None
