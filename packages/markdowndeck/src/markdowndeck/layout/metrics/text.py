"""Pure text element metrics for layout calculations - Content-aware height calculation."""

import logging
import re

from markdowndeck.layout.constants import (
    FOOTER_FONT_SIZE,
    H1_FONT_SIZE,
    H1_LINE_HEIGHT_MULTIPLIER,
    H2_FONT_SIZE,
    H2_LINE_HEIGHT_MULTIPLIER,
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
    Calculate the pure intrinsic height needed for a text element based on its content.

    This function now reliably uses actual font metrics via Pillow to accurately
    determine text height, fixing bugs related to text clipping.
    """
    element_type = getattr(
        element,
        "element_type",
        element.get("element_type") if isinstance(element, dict) else ElementType.TEXT,
    )
    text_content = getattr(
        element, "text", element.get("text") if isinstance(element, dict) else ""
    )
    directives = getattr(
        element,
        "directives",
        element.get("directives") if isinstance(element, dict) else {},
    )

    if not text_content.strip():
        return _get_minimum_height_for_type(element_type)

    if element_type == ElementType.FOOTER:
        text_content = re.sub(r"<!--.*?-->", "", text_content, flags=re.DOTALL).strip()
        if not text_content:
            return _get_minimum_height_for_type(element_type)

    font_size, line_height_multiplier, padding, min_height = _get_typography_params(
        element_type, directives
    )

    # Calculate effective width available for the text itself (after padding)
    effective_width = max(10.0, available_width - (padding * 2))

    # Use Pillow-based font metrics for accurate height calculation. This is the fix for the clipping bug.
    try:
        _, text_box_height = calculate_text_bbox(
            text_content,
            font_size,
            max_width=effective_width,
            line_height_multiplier=line_height_multiplier,
        )

        # The total height is the calculated text box height plus top and bottom padding.
        total_height = text_box_height + (padding * 2)

        logger.debug(
            f"Font-based height: type={element_type.value}, "
            f"font_size={font_size:.1f}, text_height={text_box_height:.1f}, "
            f"padding={padding}, total_height={total_height:.1f}"
        )

    except Exception as e:
        logger.error(
            f"Font metrics calculation failed for element, cannot calculate height: {e}",
            exc_info=True,
        )
        total_height = min_height  # Fallback to minimum height on error

    # Apply minimum height constraint
    final_height = max(total_height, min_height)

    logger.debug(
        f"Text height calculation: type={element_type.value}, "
        f"content_len={len(text_content)}, final_height={final_height:.1f}"
    )

    return final_height


def _get_typography_params(
    element_type: ElementType, directives: dict
) -> tuple[float, float, float, float]:
    """
    Get typography parameters for a specific element type, considering directives.
    Returns: (font_size, line_height_multiplier, padding, min_height)
    """
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

    # Override with directives
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
