import logging
import re
from typing import cast

from markdowndeck.layout.constants import (
    FOOTER_FONT_SIZE,
    H1_FONT_SIZE,
    H1_LINE_HEIGHT_MULTIPLIER,
    H2_FONT_SIZE,
    H2_LINE_HEIGHT_MULTIPLIER,
    H3_FONT_SIZE,
    H4_FONT_SIZE,
    H5_FONT_SIZE,
    H6_FONT_SIZE,
    MIN_QUOTE_HEIGHT,
    MIN_SUBTITLE_HEIGHT,
    MIN_TEXT_HEIGHT,
    MIN_TITLE_HEIGHT,
    P_FONT_SIZE,
    P_LINE_HEIGHT_MULTIPLIER,
    QUOTE_PADDING,
    SUBTITLE_PADDING,
    TEXT_PADDING,
    TITLE_PADDING,
)
from markdowndeck.layout.metrics.font_metrics import calculate_text_bbox
from markdowndeck.models import ElementType, TextElement

logger = logging.getLogger(__name__)


def calculate_text_element_height(
    element: TextElement | dict, available_width: float
) -> float:
    """
    Calculate intrinsic height for a text element and pre-compute line metrics.
    REFACTORED: Now populates `element._line_metrics` as a side effect.
    """
    text_element = cast(TextElement, element)
    element_type = text_element.element_type
    text_content = text_element.text
    directives = text_element.directives
    # FIXED: Pass heading_level to typography parameter getter.
    heading_level = getattr(text_element, "heading_level", None)

    if not text_content.strip():
        text_element._line_metrics = []
        return _get_minimum_height_for_type(element_type)

    if element_type == ElementType.FOOTER:
        text_content = re.sub(r"<!--.*?-->", "", text_content, flags=re.DOTALL).strip()
        if not text_content:
            text_element._line_metrics = []
            return _get_minimum_height_for_type(element_type)

    font_size, line_height_multiplier, padding, min_height = _get_typography_params(
        element_type, directives, heading_level
    )
    effective_width = max(10.0, available_width - (padding * 2))

    try:
        _, text_box_height, line_metrics = calculate_text_bbox(
            text_content,
            font_size,
            max_width=effective_width,
            line_height_multiplier=line_height_multiplier,
        )
        text_element._line_metrics = line_metrics
        total_height = text_box_height + (padding * 2)

    except Exception as e:
        logger.error(
            f"Font metrics calculation failed, cannot calculate height: {e}",
            exc_info=True,
        )
        text_element._line_metrics = []
        total_height = min_height

    return max(total_height, min_height)


def _get_typography_params(
    element_type: ElementType, directives: dict, heading_level: int | None = None
) -> tuple[float, float, float, float]:
    """Get typography parameters for a specific element type, considering directives and heading level."""
    params = {
        ElementType.TITLE: (
            H1_FONT_SIZE,
            H1_LINE_HEIGHT_MULTIPLIER,
            TITLE_PADDING,
            MIN_TITLE_HEIGHT,
        ),
        ElementType.SUBTITLE: (
            H2_FONT_SIZE,
            H2_LINE_HEIGHT_MULTIPLIER,
            SUBTITLE_PADDING,
            MIN_SUBTITLE_HEIGHT,
        ),
        ElementType.QUOTE: (
            P_FONT_SIZE,
            P_LINE_HEIGHT_MULTIPLIER,
            QUOTE_PADDING,
            MIN_QUOTE_HEIGHT,
        ),
        ElementType.FOOTER: (
            FOOTER_FONT_SIZE,
            P_LINE_HEIGHT_MULTIPLIER,
            TEXT_PADDING,
            20.0,
        ),
        ElementType.TEXT: (
            P_FONT_SIZE,
            P_LINE_HEIGHT_MULTIPLIER,
            TEXT_PADDING,
            MIN_TEXT_HEIGHT,
        ),
    }
    font_size, line_height, padding, min_height = params.get(
        element_type, params[ElementType.TEXT]
    )

    # FIXED: Apply heading_level font size before checking for fontsize directive override.
    if element_type == ElementType.TEXT and heading_level is not None:
        heading_font_sizes = {
            1: H1_FONT_SIZE,
            2: H2_FONT_SIZE,
            3: H3_FONT_SIZE,
            4: H4_FONT_SIZE,
            5: H5_FONT_SIZE,
            6: H6_FONT_SIZE,
        }
        font_size = heading_font_sizes.get(heading_level, P_FONT_SIZE)

    if "fontsize" in directives:
        try:
            custom_font_size = float(directives["fontsize"])
            if custom_font_size > 0:
                font_size = custom_font_size
        except (ValueError, TypeError):
            logger.warning(f"Invalid fontsize directive: {directives['fontsize']}")

    return font_size, line_height, padding, min_height


def _get_minimum_height_for_type(element_type: ElementType) -> float:
    """Get the minimum height for an element type."""
    minimums = {
        ElementType.TITLE: MIN_TITLE_HEIGHT,
        ElementType.SUBTITLE: MIN_SUBTITLE_HEIGHT,
        ElementType.QUOTE: MIN_QUOTE_HEIGHT,
        ElementType.FOOTER: 20.0,
        ElementType.TEXT: MIN_TEXT_HEIGHT,
    }
    return minimums.get(element_type, MIN_TEXT_HEIGHT)
