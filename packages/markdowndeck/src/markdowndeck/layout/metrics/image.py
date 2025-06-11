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
    image_element = (
        cast(ImageElement, element)
        if isinstance(element, ImageElement)
        else ImageElement(**element)
    )

    # Check for explicit height directive first
    if hasattr(image_element, "directives") and image_element.directives:
        height_directive = image_element.directives.get("height")
        if height_directive is not None:
            try:
                if isinstance(height_directive, int | float) and height_directive > 0:
                    explicit_height = float(height_directive)
                    logger.debug(f"Using explicit height directive: {explicit_height}")
                    return explicit_height
            except (ValueError, TypeError):
                logger.warning(f"Invalid height directive: {height_directive}")

    # Get image URL
    image_url = getattr(image_element, "url", "")
    if not image_url or not image_url.strip():
        logger.debug("No image URL provided, using minimum height")
        return MIN_IMAGE_HEIGHT

    # Get aspect ratio for the image - check element attribute first
    aspect_ratio = getattr(image_element, "aspect_ratio", None)
    if aspect_ratio is None:
        aspect_ratio = _get_image_aspect_ratio(image_url)

    # REFACTORED: Correct scaling algorithm that respects both constraints
    # Calculate height if constrained by width
    height_from_width = available_width / aspect_ratio

    # If there is no height constraint, width is the only constraint
    if available_height <= 0:
        return max(height_from_width, MIN_IMAGE_HEIGHT)

    # We have a height constraint. Compare aspect ratios to find the true constraint.
    # Box aspect ratio is available_width / available_height
    # If image aspect ratio > box aspect ratio, image is "wider" than the box -> width is constraint
    # If image aspect ratio <= box aspect ratio, image is "taller" than the box -> height is constraint
    box_aspect_ratio = available_width / available_height
    if aspect_ratio > box_aspect_ratio:
        # The image is wider than the box, so it is constrained by width.
        scaled_height = height_from_width
    else:
        # The image is taller than (or same as) the box, so it is constrained by height.
        scaled_height = available_height

    final_height = max(scaled_height, MIN_IMAGE_HEIGHT)

    logger.debug(
        f"Image proactively scaled: url={image_url[:50]}..., "
        f"aspect_ratio={aspect_ratio:.2f}, available_width={available_width:.1f}, "
        f"available_height={available_height:.1f}, final_height={final_height:.1f}"
    )

    return final_height


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
                height = int(height_match.group(1))
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

    # Check for explicit width directive
    display_width = available_width
    if hasattr(image_element, "directives") and image_element.directives:
        width_directive = image_element.directives.get("width")
        if width_directive is not None:
            try:
                if isinstance(width_directive, float) and 0 < width_directive <= 1:
                    display_width = available_width * width_directive
                elif isinstance(width_directive, int | float) and width_directive > 1:
                    display_width = min(float(width_directive), available_width)
            except (ValueError, TypeError):
                pass

    # Calculate height based on the display width with proactive scaling
    display_height = calculate_image_element_height(
        image_element, display_width, available_height
    )

    # Recalculate width from the final height to preserve aspect ratio
    aspect_ratio = getattr(image_element, "aspect_ratio", None)
    if aspect_ratio is None:
        aspect_ratio = _get_image_aspect_ratio(getattr(image_element, "url", ""))
    final_width = display_height * aspect_ratio

    # Final sanity check to ensure width does not exceed container width due to rounding.
    if final_width > available_width:
        final_width = available_width
        final_height = final_width / aspect_ratio
    else:
        final_height = display_height

    return (final_width, final_height)


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
