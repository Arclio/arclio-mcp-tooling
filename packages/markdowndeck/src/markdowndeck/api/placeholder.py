import logging
import urllib.parse

logger = logging.getLogger(__name__)


def create_placeholder_image_url(width: int, height: int, text: str) -> str:
    """
    Creates a URL for a placeholder image using a public service.

    This function generates a short, reliable URL that is compatible with the
    Google Slides API's 2KB URL length limit, replacing the previous
    base64 data URL approach which caused errors.

    Args:
        width: The width of the placeholder image.
        height: The height of the placeholder image.
        text: The text to display on the placeholder image.

    Returns:
        A URL string for the placeholder image.
    """
    # REFACTORED: Switched to placehold.co to generate short, cacheable URLs
    # instead of long base64 data URLs that violate API limits.
    # JUSTIFICATION: Fixes HttpError 400 "URL must be 2K bytes or less".
    # This aligns with the primary goal of the session.
    bg_color = "E2E8F0"  # A light gray (coolGray-200)
    text_color = "94A3B8"  # A medium gray (coolGray-400)
    encoded_text = urllib.parse.quote(text)

    # Ensure width and height are at least 1 to avoid API errors from the placeholder service
    width = max(1, int(width))
    height = max(1, int(height))

    url = f"https://placehold.co/{width}x{height}/{bg_color}/{text_color}/png?text={encoded_text}"
    logger.info(f"Generated placeholder image URL: {url}")
    return url
