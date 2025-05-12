"""Element positioning functions for the PositionCalculator."""

import logging

from markdowndeck.models import AlignmentType, ElementType

logger = logging.getLogger(__name__)


def position_header_elements(calculator, slide):
    """
    Position title and subtitle elements within the header zone.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to position header elements for
    """
    # Get title and subtitle elements if present
    title_elements = [e for e in slide.elements if e.element_type == ElementType.TITLE]
    subtitle_elements = [e for e in slide.elements if e.element_type == ElementType.SUBTITLE]

    # Position title
    if title_elements:
        title = title_elements[0]
        title_width = calculator.default_sizes[ElementType.TITLE][0]
        title_height = calculator.default_sizes[ElementType.TITLE][1]
        title.size = (title_width, title_height)

        # Center the title horizontally
        title_x = calculator.margins["left"] + (calculator.max_content_width - title_width) / 2
        title_y = calculator.margins["top"] + 20  # Position from top margin
        title.position = (title_x, title_y)

    # Position subtitle
    if subtitle_elements:
        subtitle = subtitle_elements[0]
        subtitle_width = calculator.default_sizes[ElementType.SUBTITLE][0]
        subtitle_height = calculator.default_sizes[ElementType.SUBTITLE][1]
        subtitle.size = (subtitle_width, subtitle_height)

        # Center the subtitle horizontally
        subtitle_x = (
            calculator.margins["left"] + (calculator.max_content_width - subtitle_width) / 2
        )

        # Position below title if title exists, otherwise from top margin
        if title_elements:
            subtitle_y = title.position[1] + title.size[1] + 10
        else:
            subtitle_y = calculator.margins["top"] + 30

        subtitle.position = (subtitle_x, subtitle_y)


def position_footer_element(calculator, slide):
    """
    Position footer element at the bottom of the slide.

    Args:
        calculator: The PositionCalculator instance
        slide: The slide to position footer element for
    """
    # Get footer element if present
    footer_elements = [e for e in slide.elements if e.element_type == ElementType.FOOTER]

    if footer_elements:
        footer = footer_elements[0]
        footer_width = calculator.max_content_width
        footer_height = calculator.FOOTER_HEIGHT
        footer.size = (footer_width, footer_height)

        # Default alignment is centered
        alignment = getattr(footer, "horizontal_alignment", AlignmentType.CENTER)

        # Calculate x position based on alignment
        if alignment == AlignmentType.LEFT:
            footer_x = calculator.margins["left"]
        elif alignment == AlignmentType.RIGHT:
            footer_x = calculator.slide_width - calculator.margins["right"] - footer_width
        else:  # CENTER
            footer_x = calculator.margins["left"]  # Start position

        # Position at the bottom of the slide
        footer_y = calculator.slide_height - calculator.margins["bottom"] - footer_height
        footer.position = (footer_x, footer_y)
