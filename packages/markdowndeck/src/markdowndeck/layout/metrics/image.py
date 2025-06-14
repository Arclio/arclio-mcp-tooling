"""
Enhanced image element metrics with robust dual-constraint proactive scaling.

IMPROVEMENTS:
- Implements Law #2 (Proactive Image Scaling) with both width AND height constraints
- Ensures images never cause overflow by respecting container boundaries
- Maintains aspect ratio while fitting within both dimensional constraints
- Handles invalid URLs gracefully per Law #8 (Rule #8 from LAYOUT_SPEC.md)
"""

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
    _width, height = calculate_image_display_size(element, available_width, available_height)
    return height


def calculate_image_display_size(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> tuple[float, float]:
    """
    Calculate the display size for an image element with comprehensive proactive scaling.

    ENHANCED ALGORITHM:
    1. Check URL validity (Rule #8 compliance)
    2. Determine aspect ratio from element or use default
    3. Apply dual-constraint scaling (width AND height limits)
    4. Ensure minimum viable size
    5. Cache results for performance

    This implements Law #2 by ensuring images fit within BOTH width and height constraints.
    """
    image_element = cast(ImageElement, element) if isinstance(element, ImageElement) else ImageElement(**element)

    # Rule #8: Handle invalid URLs gracefully
    if not is_valid_image_url(image_element.url):
        logger.warning(f"Image URL is invalid or inaccessible: {image_element.url}. Setting size to (0, 0) per Rule #8.")
        image_element.size = (0, 0)
        return 0.0, 0.0

    # Get aspect ratio for scaling calculations
    aspect_ratio = _get_image_aspect_ratio(image_element)
    if aspect_ratio <= 0:
        aspect_ratio = DEFAULT_IMAGE_ASPECT_RATIO

    # Apply element-specific width/height directives if present
    target_width, target_height = _apply_element_size_directives(image_element, available_width, available_height)

    # Calculate optimal size using dual-constraint scaling
    final_width, final_height = _calculate_dual_constraint_size(target_width, target_height, aspect_ratio)

    # Ensure minimum viable dimensions
    if final_height < MIN_IMAGE_HEIGHT and final_width > 0:
        final_height = MIN_IMAGE_HEIGHT
        final_width = final_height * aspect_ratio

    # Store the calculated size on the element
    image_element.size = (final_width, final_height)

    logger.debug(
        f"Image proactively scaled: url={getattr(image_element, 'url', '')[:50]}..., "
        f"aspect_ratio={aspect_ratio:.2f}, "
        f"available=({available_width:.1f}×{available_height:.1f}), "
        f"final=({final_width:.1f}×{final_height:.1f})"
    )

    return final_width, final_height


def _get_image_aspect_ratio(element: ImageElement) -> float:
    """
    Get the aspect ratio (width/height) of an image.
    Uses cached values when available, falls back to default ratio.
    """
    if element.aspect_ratio and element.aspect_ratio > 0:
        return element.aspect_ratio

    url = getattr(element, "url", "")
    if not url:
        return DEFAULT_IMAGE_ASPECT_RATIO

    # Check cache for previously calculated ratios
    if url in _image_dimensions_cache:
        return _image_dimensions_cache[url]

    # For now, use default ratio. In a full implementation, this could
    # fetch actual image dimensions from the URL
    logger.debug(f"Using default aspect ratio {DEFAULT_IMAGE_ASPECT_RATIO:.2f} for image: {url[:50]}...")
    _image_dimensions_cache[url] = DEFAULT_IMAGE_ASPECT_RATIO
    return DEFAULT_IMAGE_ASPECT_RATIO


def _apply_element_size_directives(
    element: ImageElement, available_width: float, available_height: float
) -> tuple[float, float]:
    """
    Apply element-specific width/height directives to determine target dimensions.
    Element directives are treated as preferred sizes (Law #1 - Container-First).
    """
    target_width = available_width
    target_height = available_height if available_height > 0 else float("inf")

    # Check for element width directive
    if hasattr(element, "directives") and element.directives:
        directives = element.directives

        if "width" in directives:
            width_directive = directives["width"]
            try:
                if isinstance(width_directive, str) and "%" in width_directive:
                    percentage = float(width_directive.strip("%")) / 100.0
                    target_width = available_width * percentage
                elif isinstance(width_directive, float) and 0 < width_directive <= 1:
                    target_width = available_width * width_directive
                elif isinstance(width_directive, int | float) and width_directive > 1:
                    # Clamp to available space (Container-First principle)
                    target_width = min(float(width_directive), available_width)
            except (ValueError, TypeError):
                logger.warning(f"Invalid width directive on image: {width_directive}")

        if "height" in directives and available_height > 0:
            height_directive = directives["height"]
            try:
                if isinstance(height_directive, str) and "%" in height_directive:
                    percentage = float(height_directive.strip("%")) / 100.0
                    target_height = available_height * percentage
                elif isinstance(height_directive, float) and 0 < height_directive <= 1:
                    target_height = available_height * height_directive
                elif isinstance(height_directive, int | float) and height_directive > 1:
                    # Clamp to available space (Container-First principle)
                    target_height = min(float(height_directive), available_height)
            except (ValueError, TypeError):
                logger.warning(f"Invalid height directive on image: {height_directive}")

    return target_width, target_height


def _calculate_dual_constraint_size(target_width: float, target_height: float, aspect_ratio: float) -> tuple[float, float]:
    """
    Calculate final image size respecting both width and height constraints.

    This is the core of Law #2 implementation - ensuring images fit within
    BOTH dimensional constraints while maintaining aspect ratio.
    """
    # If no height constraint, scale based on width only
    if target_height == float("inf") or target_height <= 0:
        final_width = target_width
        final_height = target_width / aspect_ratio
        return final_width, final_height

    # Calculate what the dimensions would be if constrained by width
    width_constrained_height = target_width / aspect_ratio

    # Calculate what the dimensions would be if constrained by height
    height_constrained_width = target_height * aspect_ratio

    # Choose the more restrictive constraint (smaller result)
    if width_constrained_height <= target_height:
        # Width is the limiting factor
        final_width = target_width
        final_height = width_constrained_height
    else:
        # Height is the limiting factor
        final_width = height_constrained_width
        final_height = target_height

    logger.debug(
        f"Dual-constraint scaling: target=({target_width:.1f}×{target_height:.1f}), "
        f"aspect_ratio={aspect_ratio:.2f}, final=({final_width:.1f}×{final_height:.1f})"
    )

    return final_width, final_height


def get_image_scaling_info(element: ImageElement, available_width: float, available_height: float = 0) -> dict:
    """
    Get detailed scaling information for debugging and analysis.
    """
    aspect_ratio = _get_image_aspect_ratio(element)
    target_width, target_height = _apply_element_size_directives(element, available_width, available_height)
    final_width, final_height = _calculate_dual_constraint_size(target_width, target_height, aspect_ratio)

    return {
        "url": getattr(element, "url", ""),
        "aspect_ratio": aspect_ratio,
        "available_constraints": {"width": available_width, "height": available_height},
        "target_size": {"width": target_width, "height": target_height},
        "final_size": {"width": final_width, "height": final_height},
        "scaling_applied": {
            "width_scaled": final_width < target_width,
            "height_scaled": final_height < target_height,
            "aspect_ratio_maintained": True,
        },
    }
