"""Validation utilities for Google Slides API requests."""

import logging
from typing import Any, Dict


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

        # Check TextBoxProperties fields path - THIS IS INVALID IN GOOGLE SLIDES API
        if "textBoxProperties" in fields:
            logger.warning(
                "Invalid field 'textBoxProperties': This field is not supported in the Google Slides REST API."
            )
            # Remove textBoxProperties from fields
            fields = ",".join(
                [f for f in fields.split(",") if "textBoxProperties" not in f]
            )
            request["updateShapeProperties"]["fields"] = fields

            # Remove textBoxProperties from shapeProperties
            if "textBoxProperties" in shape_props:
                logger.warning("Removing unsupported textBoxProperties from request")
                shape_props.pop("textBoxProperties")

            valid = False

        # Check autofit fields path
        if "autofit.autofitType" in fields:
            logger.warning(
                "Invalid field path 'autofit.autofitType'. Use 'autofit' instead."
            )
            fields = fields.replace("autofit.autofitType", "autofit")
            request["updateShapeProperties"]["fields"] = fields
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


def validate_batch_requests(batch: Dict[str, Any]) -> Dict[str, Any]:
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

        if has_issues:
            logger.warning(f"Fixed issues in request at index {i}: {request}")

        # Include the (potentially fixed) request
        modified_requests.append(request)

    # Replace requests list with fixed/filtered list
    result_batch = batch.copy()
    result_batch["requests"] = modified_requests
    return result_batch
