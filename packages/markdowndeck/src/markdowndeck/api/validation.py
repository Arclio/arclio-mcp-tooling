"""Validation utilities for Google Slides API requests."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


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
        style = request["updateParagraphStyle"].get("style", {})
        fields = request["updateParagraphStyle"].get("fields", "")
        text_range = request["updateParagraphStyle"].get("textRange", {})
        object_id = request["updateParagraphStyle"].get("objectId", "")

        # Validate text range indices
        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            # Check if end_index > start_index
            if end_index <= start_index:
                logger.warning(
                    f"Invalid text range: startIndex ({start_index}) must be less than endIndex ({end_index}) for object {object_id}"
                )
                # Fix the range
                text_range["endIndex"] = start_index + 1
                valid = False

            # We can't validate against text length here as we don't have that info
            # But we can check other obvious issues
            if start_index < 0:
                logger.warning(f"Invalid startIndex: {start_index} (must be >= 0)")
                text_range["startIndex"] = 0
                valid = False

            # Check for suspiciously large end indices that might cause out-of-bounds errors
            if end_index > 10000:  # Arbitrary large number, unlikely to be valid
                logger.warning(
                    f"Suspiciously large endIndex: {end_index} - likely an error"
                )
                # We cannot fix this without knowing the actual text length
                valid = False

        # Check for known invalid properties
        if "spaceMultiple" in style:
            logger.warning(
                "Invalid field 'spaceMultiple' in paragraph style. Use 'lineSpacing' instead."
            )
            # Convert spaceMultiple to lineSpacing
            spacing_value = style.pop("spaceMultiple")
            style["lineSpacing"] = float(spacing_value) / 100.0
            valid = False

        # Check if fields parameter includes invalid fields
        if "spaceMultiple" in fields:
            logger.warning(
                "Invalid field 'spaceMultiple' in fields parameter. Use 'lineSpacing' instead."
            )
            fields = fields.replace("spaceMultiple", "lineSpacing")
            request["updateParagraphStyle"]["fields"] = fields
            valid = False

        # Check lineSpacing is a float value (not an object or integer)
        if "lineSpacing" in style and not isinstance(style["lineSpacing"], float):
            logger.warning(
                f"lineSpacing must be a float value, got {type(style['lineSpacing'])}."
            )
            style["lineSpacing"] = float(style["lineSpacing"])
            valid = False

    # Check for updateTextStyle requests
    if "updateTextStyle" in request:
        text_range = request["updateTextStyle"].get("textRange", {})
        object_id = request["updateTextStyle"].get("objectId", "")

        # Validate text range indices
        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            # Check if end_index > start_index
            if end_index <= start_index:
                logger.warning(
                    f"Invalid text range: startIndex ({start_index}) must be less than endIndex ({end_index}) for object {object_id}"
                )
                # Fix the range
                text_range["endIndex"] = start_index + 1
                valid = False

            if start_index < 0:
                logger.warning(f"Invalid startIndex: {start_index} (must be >= 0)")
                text_range["startIndex"] = 0
                valid = False

            # Check for suspiciously large end indices that might cause out-of-bounds errors
            if end_index > 10000:  # Arbitrary large number, unlikely to be valid
                logger.warning(
                    f"Suspiciously large endIndex: {end_index} - likely an error"
                )
                # We cannot fix this without knowing the actual text length
                valid = False

    # Check for updateShapeProperties requests
    if "updateShapeProperties" in request:
        fields = request["updateShapeProperties"].get("fields", "")
        shape_props = request["updateShapeProperties"].get("shapeProperties", {})

        # Rule 1: If autofit is in shape_props, validate it has autofitType: NONE
        if "autofit" in shape_props:
            autofit_type = shape_props["autofit"].get("autofitType")
            if autofit_type != "NONE":
                logger.warning(
                    f"Invalid autofitType '{autofit_type}' found in request. Only 'NONE' is supported. Changing to 'NONE'."
                )
                shape_props["autofit"]["autofitType"] = "NONE"

            # Ensure field mask is correct
            if fields != "autofit.autofitType":
                logger.warning(
                    f"Autofit property present in shapeProperties for object {request['updateShapeProperties'].get('objectId')}; "
                    f"forcing fields to 'autofit.autofitType'. Original fields: '{fields}'"
                )
                request["updateShapeProperties"]["fields"] = "autofit.autofitType"
                fields = "autofit.autofitType"  # Update local var for subsequent checks
        else:
            # Rule 2: If autofit is NOT in shape_props, then fields cannot be "*"
            if fields == "*":
                logger.warning(
                    "Invalid field mask '*' in updateShapeProperties (autofit not present): "
                    "Wildcard fields are not allowed. Replacing with safe default 'shapeBackgroundFill,contentAlignment'."
                )
                request["updateShapeProperties"][
                    "fields"
                ] = "shapeBackgroundFill,contentAlignment"
                fields = "shapeBackgroundFill,contentAlignment"  # Update local var
                valid = False

        # Check TextBoxProperties fields path - THIS IS INVALID IN GOOGLE SLIDES API
        # This check runs after autofit rules. If fields is "autofit", "textBoxProperties" in "autofit" is false.
        if "autofit" not in fields and any(
            "textBoxProperties" in f for f in fields.split(",")
        ):
            logger.warning(
                "Invalid field 'textBoxProperties' found in fields string and autofit is not active."
            )
            # Remove textBoxProperties from fields
            current_fields_list = fields.split(",")
            new_fields_list = [
                f for f in current_fields_list if "textBoxProperties" not in f
            ]

            if not new_fields_list:
                logger.warning(
                    "Fields string became empty after removing textBoxProperties. "
                    "Setting to safe default 'shapeBackgroundFill,contentAlignment'."
                )
                request["updateShapeProperties"][
                    "fields"
                ] = "shapeBackgroundFill,contentAlignment"
            else:
                request["updateShapeProperties"]["fields"] = ",".join(new_fields_list)

            fields = request["updateShapeProperties"]["fields"]  # Update local var

            # Remove textBoxProperties from shapeProperties
            if "textBoxProperties" in shape_props:
                logger.warning(
                    "Removing unsupported textBoxProperties from shapeProperties"
                )
                shape_props.pop("textBoxProperties")
            valid = False

        # Check for wildcard fields again in case textBoxProperties removal logic didn't set a default
        # and autofit is not present.
        if (
            "autofit" not in shape_props
            and request["updateShapeProperties"].get("fields", "") == ""
        ):
            logger.warning(
                "Fields string is empty and autofit is not present. Setting to safe default 'shapeBackgroundFill,contentAlignment'."
            )
            request["updateShapeProperties"][
                "fields"
            ] = "shapeBackgroundFill,contentAlignment"
            valid = False

        # Check autofit fields path (This is more of a sanity check now, primary logic is above)
        if (
            "autofit" in fields
            and fields == "autofit"
            and not fields.startswith("autofit.")
        ):
            logger.warning(
                "Invalid field path 'autofit'. Use 'autofit.autofitType' instead."
            )
            fields = fields.replace("autofit", "autofit.autofitType")
            request["updateShapeProperties"]["fields"] = fields
            valid = False

        # Check for contentVerticalAlignment which should be contentAlignment
        if "contentVerticalAlignment" in fields:
            logger.warning(
                "Invalid field path 'contentVerticalAlignment'. Use 'contentAlignment' instead."
            )
            fields = fields.replace("contentVerticalAlignment", "contentAlignment")
            request["updateShapeProperties"]["fields"] = fields

            # Also update the property name in the shapeProperties
            if "contentVerticalAlignment" in shape_props:
                value = shape_props.pop("contentVerticalAlignment")
                shape_props["contentAlignment"] = value

            valid = False

    # Check for createParagraphBullets requests
    if "createParagraphBullets" in request:
        text_range = request["createParagraphBullets"].get("textRange", {})
        object_id = request["createParagraphBullets"].get("objectId", "")

        # Validate text range indices
        if "startIndex" in text_range and "endIndex" in text_range:
            start_index = text_range["startIndex"]
            end_index = text_range["endIndex"]

            # Check if end_index > start_index
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

            # Check for suspiciously large end indices that might cause out-of-bounds errors
            if end_index > 10000:  # Arbitrary large number, unlikely to be valid
                logger.warning(
                    f"Suspiciously large endIndex in createParagraphBullets: {end_index} for object {object_id} - likely an error"
                )
                # We cannot fix this without knowing the actual text length here, just warn
                valid = False

    # Check for tableCellProperties field paths
    if "updateTableCellProperties" in request:
        fields = request["updateTableCellProperties"].get("fields", "")

        # Check if fields starts with "tableCellProperties."
        if fields.startswith("tableCellProperties."):
            logger.warning(
                f"Invalid field path starting with 'tableCellProperties.': {fields}"
            )
            fields = fields.replace("tableCellProperties.", "")
            request["updateTableCellProperties"]["fields"] = fields
            valid = False

    # Check for tableBorderProperties field paths
    if "updateTableBorderProperties" in request:
        fields = request["updateTableBorderProperties"].get("fields", "")

        # Check if fields starts with "tableBorderProperties."
        if fields.startswith("tableBorderProperties."):
            logger.warning(
                f"Invalid field path starting with 'tableBorderProperties.': {fields}"
            )
            fields = fields.replace("tableBorderProperties.", "")
            request["updateTableBorderProperties"]["fields"] = fields
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
    modified_requests = []

    for i, request in enumerate(batch.get("requests", [])):
        has_issues = not validate_api_request(request)

        # Additional batch-specific validations:

        # Check for text range index issues in paragraph style
        if "updateParagraphStyle" in request:
            text_range = request["updateParagraphStyle"].get("textRange", {})
            if (
                "type" not in text_range
                and "startIndex" in text_range
                and "endIndex" in text_range
            ):
                start_index = text_range["startIndex"]
                end_index = text_range["endIndex"]

                # Fix off-by-one errors (common issue with trailing newlines)
                if (
                    end_index - start_index > 1 and end_index % 50 == 1
                ):  # Potential off-by-one error pattern
                    logger.warning(
                        f"Potential off-by-one error in request {i}: endIndex={end_index}"
                    )
                    text_range["endIndex"] = end_index - 1
                    has_issues = True

                # Add safety check for any text range that exceeds typical document sizes
                if end_index > start_index + 10000:  # 10000 chars is a large text block
                    logger.warning(
                        f"Text range suspiciously large in request {i}: {start_index}-{end_index}. Limiting range."
                    )
                    # Limit to a reasonable range
                    text_range["endIndex"] = start_index + 5000
                    has_issues = True

        # Check for text range index issues in text style
        if "updateTextStyle" in request:
            text_range = request["updateTextStyle"].get("textRange", {})
            if (
                "type" not in text_range
                and "startIndex" in text_range
                and "endIndex" in text_range
            ):
                start_index = text_range["startIndex"]
                end_index = text_range["endIndex"]

                # Fix off-by-one errors (common issue with trailing newlines)
                if (
                    end_index - start_index > 1 and end_index % 50 == 1
                ):  # Potential off-by-one error pattern
                    logger.warning(
                        f"Potential off-by-one error in request {i}: endIndex={end_index}"
                    )
                    text_range["endIndex"] = end_index - 1
                    has_issues = True

                # Add safety check for any text range that exceeds typical document sizes
                if end_index > start_index + 10000:  # 10000 chars is a large text block
                    logger.warning(
                        f"Text range suspiciously large in request {i}: {start_index}-{end_index}. Limiting range."
                    )
                    # Limit to a reasonable range
                    text_range["endIndex"] = start_index + 5000
                    has_issues = True

        # Check for text range index issues in createParagraphBullets
        if "createParagraphBullets" in request:
            text_range = request["createParagraphBullets"].get("textRange", {})
            if (
                "type"
                not in text_range  # Ensure it's a range with start/end, not 'ALL' etc.
                and "startIndex" in text_range
                and "endIndex" in text_range
            ):
                start_index = text_range["startIndex"]
                end_index = text_range["endIndex"]

                # Add safety check for any text range that exceeds typical document sizes
                if end_index > start_index + 10000:  # 10000 chars is a large text block
                    logger.warning(
                        f"Text range suspiciously large in createParagraphBullets request {i}: {start_index}-{end_index}. Limiting range."
                    )
                    # Limit to a reasonable range
                    text_range["endIndex"] = start_index + 5000
                    has_issues = True

                # Ensure end_index is still greater than start_index after potential capping
                if text_range["endIndex"] <= text_range["startIndex"]:
                    logger.warning(
                        f"Adjusted endIndex in createParagraphBullets for request {i} is not greater than startIndex. Fixing: {text_range['startIndex']}-{text_range['endIndex']}"
                    )
                    text_range["endIndex"] = text_range["startIndex"] + 1
                    has_issues = True

        if has_issues:
            logger.warning(f"Fixed issues in request at index {i}: {request}")

        # Include the (potentially fixed) request
        modified_requests.append(request)

    # Replace requests list with fixed/filtered list
    result_batch = batch.copy()
    result_batch["requests"] = modified_requests
    return result_batch


def is_valid_image_url(url: str) -> bool:
    """
    Validate if a URL is a valid image URL.

    This performs both format validation and image accessibility checking.
    Google Slides API requires images to be accessible.

    Args:
        url: The URL to validate

    Returns:
        bool: True if the URL is valid and accessible
    """
    if not url:
        return False

    # Only allow http/https URLs
    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    # Check for common image extensions
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]
    has_valid_extension = any(url.lower().endswith(ext) for ext in image_extensions)

    # If no extension, at least make sure it's a properly formed URL with a domain
    if not has_valid_extension and "." not in url.split("//", 1)[-1]:
        return False

    # Check if image actually exists and is accessible
    try:
        # Use HEAD request to check image existence
        head_response = requests.head(url, timeout=3, allow_redirects=True)

        # Check status code
        if head_response.status_code != 200:
            logger.warning(
                f"Image URL returned status code {head_response.status_code}: {url}"
            )
            return False

        # Verify content type is an image
        content_type = head_response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            logger.warning(
                f"URL does not point to an image (content-type: {content_type}): {url}"
            )
            return False

        return True
    except Exception as e:
        # If we can't access the image, log warning and reject it
        logger.warning(f"Image verification failed for {url}: {e}")
        return False
