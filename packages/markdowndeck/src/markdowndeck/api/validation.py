import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Google Slides API limit for images is 50 MB.
MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024


def validate_api_request(request: dict[str, Any]) -> bool:
    """
    Validate an API request against known valid Google Slides API structures.

    Args:
        request: The API request dictionary

    Returns:
        True if valid, False if issues were found
    """
    valid = True

    # Check for updateParagraphStyle requests
    if "updateParagraphStyle" in request:
        text_range = request["updateParagraphStyle"].get("textRange", {})
        object_id = request["updateParagraphStyle"].get("objectId", "")

        # Validate text range indices
        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            if end_index <= start_index:
                logger.warning(
                    f"Invalid text range: startIndex ({start_index}) must be less than endIndex ({end_index}) for object {object_id}"
                )
                text_range["endIndex"] = start_index + 1
                valid = False

            if start_index < 0:
                logger.warning(f"Invalid startIndex: {start_index} (must be >= 0)")
                text_range["startIndex"] = 0
                valid = False

    # Check for updateTextStyle requests
    if "updateTextStyle" in request:
        text_range = request["updateTextStyle"].get("textRange", {})
        object_id = request["updateTextStyle"].get("objectId", "")

        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            if end_index <= start_index:
                logger.warning(
                    f"Invalid text range: startIndex ({start_index}) must be less than endIndex ({end_index}) for object {object_id}"
                )
                text_range["endIndex"] = start_index + 1
                valid = False

            if start_index < 0:
                logger.warning(f"Invalid startIndex: {start_index} (must be >= 0)")
                text_range["startIndex"] = 0
                valid = False

    # Check for createParagraphBullets requests
    if "createParagraphBullets" in request:
        text_range = request["createParagraphBullets"].get("textRange", {})
        object_id = request["createParagraphBullets"].get("objectId", "")

        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            if end_index <= start_index:
                logger.warning(
                    f"Invalid text range in createParagraphBullets: startIndex ({start_index}) must be less than endIndex ({end_index}) for object {object_id}"
                )
                text_range["endIndex"] = start_index + 1
                valid = False

            if start_index < 0:
                logger.warning(
                    f"Invalid startIndex in createParagraphBullets: {start_index} (must be >= 0) for object {object_id}"
                )
                text_range["startIndex"] = 0
                valid = False

    return valid


def validate_batch_requests(batch: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and fix a batch of API requests.

    Args:
        batch: Dictionary with presentationId and requests

    Returns:
        Validated (and potentially fixed) batch
    """
    modified_requests = [
        req for req in batch.get("requests", []) if validate_api_request(req)
    ]
    result_batch = batch.copy()
    result_batch["requests"] = modified_requests
    return result_batch


def is_valid_image_url(url: str) -> bool:
    """
    Validate if a URL is a valid, accessible, and appropriately sized image.
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return False

    try:
        # REFACTORED: Use a streaming GET request, which is more reliable than HEAD.
        # We only inspect headers, so this is still efficient.
        with requests.get(
            url, stream=True, timeout=5, allow_redirects=True
        ) as response:
            response.raise_for_status()

            # 1. Check Content-Type
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                logger.warning(
                    f"URL does not appear to be an image (Content-Type: {content_type}): {url}"
                )
                return False

            # 2. Check Content-Length for file size
            content_length_str = response.headers.get("content-length")
            if content_length_str:
                try:
                    content_length = int(content_length_str)
                    if content_length > MAX_IMAGE_SIZE_BYTES:
                        logger.warning(
                            f"Image at {url} is too large ({content_length / 1024 / 1024:.2f} MB). "
                            f"Limit is {MAX_IMAGE_SIZE_BYTES / 1024 / 1024:.2f} MB. Skipping."
                        )
                        return False
                except ValueError:
                    logger.warning(
                        f"Could not parse Content-Length header: {content_length_str}"
                    )
            else:
                logger.debug(
                    f"Content-Length header not found for {url}. Cannot pre-validate size."
                )

            return True

    except requests.exceptions.RequestException as e:
        logger.warning(
            f"Image URL verification failed (request exception): {url}. Error: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during image validation for {url}: {e}",
            exc_info=True,
        )
        return False
