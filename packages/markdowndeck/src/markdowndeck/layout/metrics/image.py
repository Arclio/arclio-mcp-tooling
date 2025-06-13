"""Pure image element metrics for layout calculations - Proactive scaling implementation."""

import logging
from typing import cast

from markdowndeck.api.validation import is_valid_image_url
from markdowndeck.layout.constants import (
    DEFAULT_IMAGE_ASPECT_RATIO,
    MIN_IMAGE_HEIGHT,
)
from markdowndeck.models import ImageElement

logger = logging.getLogger(__name__)

_image_dimensions_cache = {}


def calculate_image_element_height(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> float:
    """
    Calculate the height needed for an image element with proactive scaling.
    This is a wrapper around calculate_image_display_size for compatibility.
    """
    _width, height = calculate_image_display_size(
        element, available_width, available_height
    )
    return height


def _get_image_aspect_ratio(element: ImageElement) -> float:
    """Get the aspect ratio (width/height) of an image."""
    if element.aspect_ratio:
        return element.aspect_ratio
    url = getattr(element, "url", "")
    if not url:
        return DEFAULT_IMAGE_ASPECT_RATIO
    if url in _image_dimensions_cache:
        return _image_dimensions_cache[url]
    logger.debug(
        f"Using default aspect ratio {DEFAULT_IMAGE_ASPECT_RATIO:.2f} for image: {url[:50]}..."
    )
    _image_dimensions_cache[url] = DEFAULT_IMAGE_ASPECT_RATIO
    return DEFAULT_IMAGE_ASPECT_RATIO


def calculate_image_display_size(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> tuple[float, float]:
    """
    Calculate the display size for an image element with proactive scaling.
    """
    image_element = (
        cast(ImageElement, element)
        if isinstance(element, ImageElement)
        else ImageElement(**element)
    )

    if not is_valid_image_url(image_element.url):
        logger.warning(
            f"Image URL is invalid or inaccessible: {image_element.url}. Assigning size (0, 0)."
        )
        # FIXED: Ensure both width and height are zero for invalid images.
        image_element.size = (0, 0)
        return 0, 0

    aspect_ratio = _get_image_aspect_ratio(image_element)
    if aspect_ratio <= 0:
        aspect_ratio = DEFAULT_IMAGE_ASPECT_RATIO

    target_width = available_width
    target_height = available_height if available_height > 0 else float("inf")
    width_if_height_constrained = target_height * aspect_ratio
    height_if_width_constrained = target_width / aspect_ratio

    if height_if_width_constrained <= target_height:
        final_w = target_width
        final_h = height_if_width_constrained
    else:
        final_h = target_height
        final_w = width_if_height_constrained

    final_h = max(final_h, MIN_IMAGE_HEIGHT)
    image_element.size = (final_w, final_h)

    logger.debug(
        f"Image display size calculated: url={getattr(image_element, 'url', '')[:30]}..., "
        f"aspect_ratio={aspect_ratio:.2f}, available=({available_width:.1f}, {available_height:.1f}), "
        f"final=({final_w:.1f}, {final_h:.1f})"
    )
    return (final_w, final_h)
