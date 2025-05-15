"""Validation utilities for Google Slides API requests."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def validate_api_request(request: Dict[str, Any]) -> bool:
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

        # Check for known invalid properties
        if "spaceMultiple" in style:
            logger.warning("Invalid field 'spaceMultiple' in paragraph style. Use 'lineSpacing' instead.")
            valid = False

        # Check if fields parameter includes invalid fields
        if "spaceMultiple" in fields:
            logger.warning("Invalid field 'spaceMultiple' in fields parameter. Use 'lineSpacing' instead.")
            valid = False

        # Check lineSpacing is a float value (not an object or integer)
        if "lineSpacing" in style and not isinstance(style["lineSpacing"], float):
            logger.warning(f"lineSpacing must be a float value, got {type(style['lineSpacing'])}.")
            valid = False

    # Check for updateShapeProperties requests with invalid fields
    if "updateShapeProperties" in request:
        shape_props = request["updateShapeProperties"].get("shapeProperties", {})
        fields = request["updateShapeProperties"].get("fields", "")

        # Check for unsupported textBoxProperties field
        if "textBoxProperties" in shape_props:
            logger.warning("Unsupported field 'textBoxProperties' in shapeProperties. This will cause an API error.")
            valid = False

        # Check if fields parameter includes textBoxProperties
        if "textBoxProperties" in fields:
            logger.warning("Unsupported field 'textBoxProperties' in fields parameter. This will cause an API error.")
            valid = False

        # Check for incorrect structure using 'text'
        if "text" in shape_props:
            logger.warning("Invalid field 'text' in shapeProperties. This will cause an API error.")
            valid = False

    # Add checks for other request types as needed

    return valid

def validate_batch_requests(batch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and optionally fix a batch of API requests.

    Args:
        batch: Dictionary with presentationId and requests

    Returns:
        Validated (and potentially fixed) batch
    """
    modified_requests = []

    for i, request in enumerate(batch.get("requests", [])):
        if not validate_api_request(request):
            logger.warning(f"API request at index {i} has validation issues: {request}")

            # Auto-fix for common issues

            # Fix spaceMultiple -> lineSpacing
            if "updateParagraphStyle" in request:
                style = request["updateParagraphStyle"].get("style", {})
                fields = request["updateParagraphStyle"].get("fields", "")

                if "spaceMultiple" in style:
                    # Auto-fix: convert integer percentage to float
                    spacing_value = style.pop("spaceMultiple")
                    style["lineSpacing"] = float(spacing_value) / 100.0
                    logger.info(f"Auto-fixed spaceMultiple -> lineSpacing: {spacing_value}/100 -> {style['lineSpacing']}")

                # Fix fields parameter
                if "spaceMultiple" in fields:
                    fields = fields.replace("spaceMultiple", "lineSpacing")
                    request["updateParagraphStyle"]["fields"] = fields
                    logger.info(f"Auto-fixed fields parameter: {fields}")

                # Include this fixed request
                modified_requests.append(request)

            # Skip problematic updateShapeProperties with textBoxProperties
            elif "updateShapeProperties" in request:
                shape_props = request["updateShapeProperties"].get("shapeProperties", {})

                if "textBoxProperties" in shape_props or "textBoxProperties" in request["updateShapeProperties"].get("fields", ""):
                    logger.info("Skipping unsupported updateShapeProperties request with textBoxProperties")
                    # Skip this request entirely since it's not supported
                    continue

                if "text" in shape_props:
                    logger.info("Skipping unsupported updateShapeProperties request with text field")
                    # Skip this request entirely
                    continue

                # If we get here, the request is valid and should be included
                modified_requests.append(request)
            else:
                # Include all other requests
                modified_requests.append(request)
        else:
            # Include valid requests
            modified_requests.append(request)

    # Replace requests list with fixed/filtered list
    result_batch = batch.copy()
    result_batch["requests"] = modified_requests
    return result_batch
