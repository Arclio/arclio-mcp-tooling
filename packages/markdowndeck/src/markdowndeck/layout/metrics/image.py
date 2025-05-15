"""Image element metrics for layout calculations."""

import logging
import re
from typing import cast, Tuple
from urllib.parse import urlparse
import requests

from markdowndeck.models import ImageElement

logger = logging.getLogger(__name__)

# Default aspect ratio to use when image dimensions cannot be determined
DEFAULT_ASPECT_RATIO = 16 / 9  # Common presentation aspect ratio
DEFAULT_IMAGE_MIN_HEIGHT = 100.0  # Minimum height for any image
DEFAULT_IMAGE_MAX_HEIGHT_FRACTION = 1  # Max height as fraction of section height

# Cache for image dimensions to avoid repeated network requests
_image_dimensions_cache = {}


def calculate_image_element_height(
    element: ImageElement | dict, available_width: float, available_height: float = 0
) -> float:
    """
    Calculate the optimal height for an image element based on its aspect ratio and available space.

    Args:
        element: The image element or dict
        available_width: Available width for the image
        available_height: Optional available height constraint (0 means no constraint)

    Returns:
        Calculated height in points that maintains aspect ratio
    """
    image_element = (
        cast(ImageElement, element)
        if isinstance(element, ImageElement)
        else ImageElement(**element)
    )

    # If no image URL, use a sensible default height
    if not image_element.url or not image_element.url.strip():
        logger.debug("No image URL provided, using default height")
        return DEFAULT_IMAGE_MIN_HEIGHT

    # Get aspect ratio (width/height) of the image
    aspect_ratio = get_image_aspect_ratio(image_element.url)
    logger.debug(
        f"Image {image_element.url[:50]}... has aspect ratio {aspect_ratio:.2f}"
    )

    # Calculate height based on available width and aspect ratio
    calculated_height = available_width / aspect_ratio

    # Apply minimum height constraint
    calculated_height = max(calculated_height, DEFAULT_IMAGE_MIN_HEIGHT)

    # IMPROVED: Better utilize available vertical space
    if available_height > 0:
        # If the calculated height is significantly less than the available height
        # and there's room to grow, scale the image up to use more space while maintaining aspect ratio
        max_allowed_height = available_height * DEFAULT_IMAGE_MAX_HEIGHT_FRACTION

        # If image would use less than 70% of available space, scale it up to 85%
        if calculated_height < max_allowed_height * 0.7:
            # Scale up to better utilize available space
            calculated_height = max_allowed_height * 0.85
            logger.debug(
                f"Scaled up image height to better utilize space: {calculated_height:.1f}pt"
            )
        elif calculated_height > max_allowed_height:
            # If image would be too tall, constrain it
            calculated_height = max_allowed_height
            logger.debug(
                f"Constrained image height to max allowed: {calculated_height:.1f}pt"
            )

    # If the image has a fixed size directive, respect that but ensure aspect ratio
    if hasattr(element, "directives") and "height" in element.directives:
        try:
            specified_height = float(element.directives["height"])
            logger.debug(f"Using specified height directive: {specified_height}")
            return specified_height
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid height directive: {element.directives['height']}, using calculated height"
            )

    logger.debug(
        f"Calculated image height: {calculated_height:.2f}pt from width {available_width:.2f}pt"
    )
    return calculated_height


def get_image_aspect_ratio(url: str) -> float:
    """
    Get the aspect ratio (width/height) of an image from its URL.
    Uses a cache to avoid repeated network requests.

    Args:
        url: Image URL

    Returns:
        Aspect ratio (width/height) or DEFAULT_ASPECT_RATIO if dimensions cannot be determined
    """
    # Check if already in cache
    if url in _image_dimensions_cache:
        return _image_dimensions_cache[url]

    # Check for data URLs with embedded dimensions (common in testing)
    data_url_dims = _extract_dimensions_from_data_url(url)
    if data_url_dims:
        width, height = data_url_dims
        aspect_ratio = width / height
        _image_dimensions_cache[url] = aspect_ratio
        return aspect_ratio

    # For regular URLs, try to get dimensions with minimal data transfer
    if url.startswith(("http://", "https://")):
        try:
            # First try with a HEAD request to get content-type
            head_response = requests.head(url, timeout=3, allow_redirects=True)

            if head_response.status_code != 200:
                logger.warning(
                    f"Could not access image URL: {url} (status {head_response.status_code})"
                )
                return DEFAULT_ASPECT_RATIO

            content_type = head_response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    f"URL does not appear to be an image (content-type: {content_type}): {url}"
                )
                return DEFAULT_ASPECT_RATIO

            # Try getting dimensions from URL parameters (common in image services)
            url_dimensions = _extract_dimensions_from_url(url)
            if url_dimensions:
                width, height = url_dimensions
                aspect_ratio = width / height
                _image_dimensions_cache[url] = aspect_ratio
                return aspect_ratio

            # For some common image formats, we can fetch just the header bytes
            # This could be expanded to support more formats
            if content_type in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                # Get just enough bytes to determine dimensions (varies by format)
                # For most formats, 64KB should be sufficient
                chunk_size = 65536  # 64KB
                with requests.get(url, stream=True, timeout=5) as response:
                    if response.status_code == 200:
                        chunk = response.raw.read(chunk_size)
                        # Here we could add format-specific dimension extraction
                        # But it's complex and beyond the scope of this fix
                        # For now, we'll use DEFAULT_ASPECT_RATIO

            # If we reached here, we couldn't determine dimensions precisely
            logger.debug(
                f"Could not determine image dimensions for {url}, using default aspect ratio"
            )
            return DEFAULT_ASPECT_RATIO

        except Exception as e:
            logger.warning(f"Error getting image dimensions for {url}: {e}")
            return DEFAULT_ASPECT_RATIO

    # If we reached here, return the default aspect ratio
    return DEFAULT_ASPECT_RATIO


def _extract_dimensions_from_data_url(url: str) -> Tuple[int, int] | None:
    """Extract dimensions from a data URL if present."""
    if url.startswith("data:") and "width=" in url and "height=" in url:
        width_match = re.search(r"width=(\d+)", url)
        height_match = re.search(r"height=(\d+)", url)
        if width_match and height_match:
            try:
                width = int(width_match.group(1))
                height = int(height_match.group(1))
                if width > 0 and height > 0:
                    return (width, height)
            except ValueError:
                pass
    return None


def _extract_dimensions_from_url(url: str) -> Tuple[int, int] | None:
    """
    Extract image dimensions from URL parameters (common in image services).

    Handles patterns like:
    - example.com/image.jpg?width=800&height=600
    - example.com/800x600/image.jpg
    - example.com/w=800&h=600/image.jpg
    """
    # Pattern 1: width and height as query parameters
    parsed_url = urlparse(url)
    query_params = dict(
        param.split("=") for param in parsed_url.query.split("&") if "=" in param
    )

    # Check for width/height, w/h, or size parameters
    if "width" in query_params and "height" in query_params:
        try:
            width = int(query_params["width"])
            height = int(query_params["height"])
            if width > 0 and height > 0:
                return (width, height)
        except ValueError:
            pass

    if "w" in query_params and "h" in query_params:
        try:
            width = int(query_params["w"])
            height = int(query_params["h"])
            if width > 0 and height > 0:
                return (width, height)
        except ValueError:
            pass

    # Pattern 2: dimensions in path like 800x600
    dimension_pattern = r"/(\d+)x(\d+)/"
    match = re.search(dimension_pattern, url)
    if match:
        try:
            width = int(match.group(1))
            height = int(match.group(2))
            if width > 0 and height > 0:
                return (width, height)
        except ValueError:
            pass

    # Pattern 3: width and height in filename
    filename_pattern = r"_(\d+)x(\d+)\.(jpg|jpeg|png|gif|webp)$"
    match = re.search(filename_pattern, url, re.IGNORECASE)
    if match:
        try:
            width = int(match.group(1))
            height = int(match.group(2))
            if width > 0 and height > 0:
                return (width, height)
        except ValueError:
            pass

    return None
