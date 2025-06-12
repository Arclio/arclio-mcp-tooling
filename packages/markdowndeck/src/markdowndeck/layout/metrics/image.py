"""Pure image element metrics for layout calculations - Proactive scaling implementation."""

import logging
from typing import cast

from markdowndeck.layout.constants import (
    # Image specific constants
    DEFAULT_IMAGE_ASPECT_RATIO,
    MIN_IMAGE_HEIGHT,
)
from markdowndeck.models import ImageElement

logger = logging.getLogger(__name__)

# Cache for image dimensions to avoid repeated lookups
_image_dimensions_cache = {}


def calculate_image_element_height(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> float:
    """
    Calculate the height needed for an image element with proactive scaling.

    Per Rule #5 of the specification: Images are proactively scaled to fit within their
    parent section's available width while maintaining aspect ratio. This prevents
    layout shifts and ensures images never cause overflow by themselves.

    Args:
        element: The image element to measure
        available_width: Available width for the image (container width)
        available_height: Available height constraint (0 means no constraint)

    Returns:
        The calculated height that ensures the image fits within constraints
    """
    # This function is now a simple wrapper around calculate_image_display_size
    # for backward compatibility within the metrics module.
    _width, height = calculate_image_display_size(
        element, available_width, available_height
    )
    return height


def _get_image_aspect_ratio(url: str) -> float:
    """
    Get the aspect ratio (width/height) of an image from its URL.

    This implementation uses cached values and basic URL analysis.
    For production use, this could be enhanced with actual image inspection.

    Args:
        url: Image URL

    Returns:
        Aspect ratio (width/height) or default if cannot be determined
    """
    # Check cache first
    if url in _image_dimensions_cache:
        return _image_dimensions_cache[url]

    # Try to extract dimensions from URL patterns
    aspect_ratio = _extract_aspect_ratio_from_url(url)

    if aspect_ratio is None:
        # Use default aspect ratio
        aspect_ratio = DEFAULT_IMAGE_ASPECT_RATIO
        logger.debug(
            f"Using default aspect ratio {aspect_ratio:.2f} for image: {url[:50]}..."
        )

    # Cache the result
    _image_dimensions_cache[url] = aspect_ratio

    return aspect_ratio


def _extract_aspect_ratio_from_url(url: str) -> float | None:
    """
    Try to extract aspect ratio from URL patterns.

    Looks for patterns like:
    - example.com/800x600/image.jpg
    - example.com/image.jpg?width=800&height=600
    - data:image/jpeg;width=800;height=600;base64,...

    Args:
        url: Image URL to analyze

    Returns:
        Aspect ratio if found, None otherwise
    """
    import re
    from urllib.parse import parse_qs, urlparse

    # Pattern 1: Dimensions in path like 800x600
    dimension_pattern = r"/(\d+)x(\d+)/"
    match = re.search(dimension_pattern, url)
    if match:
        try:
            width = int(match.group(1))
            height = int(match.group(2))
            if width > 0 and height > 0:
                return width / height
        except ValueError:
            pass

    # Pattern 2: Query parameters
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        width = None
        height = None

        # Check various parameter names
        if "width" in query_params and "height" in query_params:
            width = int(query_params["width"][0])
            height = int(query_params["height"][0])
        elif "w" in query_params and "h" in query_params:
            width = int(query_params["w"][0])
            height = int(query_params["h"][0])

        if width and height and width > 0 and height > 0:
            return width / height

    except (ValueError, IndexError):
        pass

    # Pattern 3: Data URL with dimensions
    if url.startswith("data:"):
        width_match = re.search(r"width=(\d+)", url)
        height_match = re.search(r"height=(\d+)", url)
        if width_match and height_match:
            try:
                width = int(width_match.group(1))
                height = int(height_match.group(2))
                if width > 0 and height > 0:
                    return width / height
            except ValueError:
                pass

    # Pattern 4: Filename with dimensions
    filename_pattern = r"_(\d+)x(\d+)\.(jpg|jpeg|png|gif|webp)$"
    match = re.search(filename_pattern, url, re.IGNORECASE)
    if match:
        try:
            width = int(match.group(1))
            height = int(match.group(2))
            if width > 0 and height > 0:
                return width / height
        except ValueError:
            pass

    return None


def calculate_image_display_size(
    element: ImageElement | dict,
    available_width: float,
    available_height: float = 0,
) -> tuple[float, float]:
    """
    Calculate the display size (width, height) for an image element with proactive scaling.

    This function implements the proactive scaling contract: images are always sized
    to fit within their container while maintaining aspect ratio.

    Args:
        element: The image element
        available_width: Available width (container width)
        available_height: Available height constraint

    Returns:
        (display_width, display_height) tuple that fits within constraints
    """
    image_element = (
        cast(ImageElement, element)
        if isinstance(element, ImageElement)
        else ImageElement(**element)
    )

    aspect_ratio = _get_image_aspect_ratio(getattr(image_element, "url", ""))

    # Determine the initial target width from directives, capped by container width.
    target_width = available_width
    if hasattr(image_element, "directives") and image_element.directives:
        width_directive = image_element.directives.get("width")
        if width_directive is not None:
            try:
                if isinstance(width_directive, float) and 0 < width_directive <= 1:
                    target_width = available_width * width_directive
                elif isinstance(width_directive, int | float) and width_directive > 1:
                    target_width = min(float(width_directive), available_width)
            except (ValueError, TypeError):
                logger.warning(f"Invalid width directive: {width_directive}")

    # Determine the initial target height from directives, capped by container height.
    target_height = available_height if available_height > 0 else float("inf")
    if hasattr(image_element, "directives") and image_element.directives:
        height_directive = image_element.directives.get("height")
        if height_directive is not None:
            try:
                if isinstance(height_directive, float) and 0 < height_directive <= 1:
                    target_height = min(
                        target_height, available_height * height_directive
                    )
                elif isinstance(height_directive, int | float) and height_directive > 1:
                    target_height = min(target_height, float(height_directive))
            except (ValueError, TypeError):
                logger.warning(f"Invalid height directive: {height_directive}")

    # Calculate final dimensions while preserving aspect ratio.
    # We have three constraints: target_width, target_height, and available_width/available_height.
    # The final size must respect all of them.

    # Calculate dimensions if constrained by width
    target_width / aspect_ratio

    # Calculate dimensions if constrained by height
    target_height * aspect_ratio

    # The image must fit inside the available area.
    # It also must respect the user's target width/height directives if they make it smaller.
    final_w = available_width
    final_h = available_height

    if available_height <= 0:  # No height constraint
        final_w = target_width
        final_h = final_w / aspect_ratio
    else:  # Both width and height are constrained
        # Compare aspect ratios to see which dimension is the primary constraint
        if (available_width / available_height) > aspect_ratio:
            # Container is wider than the image; height is the limiting dimension
            final_h = available_height
            final_w = final_h * aspect_ratio
        else:
            # Container is taller/narrower than the image; width is the limiting dimension
            final_w = available_width
            final_h = final_w / aspect_ratio

    # Now, check if the user directives for width/height are even more constraining.
    if target_width < final_w:
        final_w = target_width
        final_h = final_w / aspect_ratio

    if target_height < final_h:
        final_h = target_height
        final_w = final_h * aspect_ratio

    final_h = max(final_h, MIN_IMAGE_HEIGHT)

    logger.debug(
        f"Image display size calculated: "
        f"url={getattr(image_element, 'url', '')[:30]}..., "
        f"aspect_ratio={aspect_ratio:.2f}, available=({available_width:.1f}, {available_height:.1f}), "
        f"final=({final_w:.1f}, {final_h:.1f})"
    )

    return (final_w, final_h)


def estimate_image_loading_impact(image_url: str) -> str:
    """
    Estimate the loading impact of an image based on its URL.

    Args:
        image_url: URL of the image

    Returns:
        Impact classification: "low", "medium", "high"
    """
    if not image_url:
        return "low"

    url_lower = image_url.lower()

    # Data URLs are embedded, so no loading impact
    if url_lower.startswith("data:"):
        return "low"

    # Large image file extensions might have higher impact
    if any(ext in url_lower for ext in [".png", ".tiff", ".bmp"]):
        return "high"
    if any(ext in url_lower for ext in [".jpg", ".jpeg", ".webp"]):
        return "medium"

    return "medium"  # Default assumption
