"""
MCP server utilities for Google Workspace integration.
This file now contains utility functions, like parsing capabilities.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


# Parse enabled capabilities from environment
def get_enabled_capabilities() -> set[str]:
    """
    Get the set of enabled capabilities from environment variables.
    Expects GOOGLE_WORKSPACE_ENABLED_CAPABILITIES to be a JSON array of strings.
    E.g., '["drive", "gmail", "docs"]'

    Returns:
        set[str]: Enabled capability names
    """
    capabilities_str = os.environ.get("GOOGLE_WORKSPACE_ENABLED_CAPABILITIES", "[]")  # Default to empty JSON list string

    if not capabilities_str.strip():
        capabilities_str = "[]"  # Treat fully empty or whitespace-only string as empty list

    capabilities: set[str] = set()
    try:
        parsed_list = json.loads(capabilities_str)
        if isinstance(parsed_list, list) and all(isinstance(item, str) for item in parsed_list):
            capabilities = {cap.strip().lower() for cap in parsed_list if cap.strip()}
        else:
            logger.warning(
                f"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES is not a valid JSON list of strings: {capabilities_str}. "
                f"Found type: {type(parsed_list)}. All tools may be affected. "
                'Please use format like \'["drive", "gmail"]\'.'
            )
            # Fallback to empty set, effectively disabling tools unless Hub ignores this
            # Or, decide if we should raise an error or parse common old format as fallback
            # For now, strict parsing and warning.
    except json.JSONDecodeError:
        logger.warning(
            f"GOOGLE_WORKSPACE_ENABLED_CAPABILITIES is not valid JSON: {capabilities_str}. "
            'All tools may be affected. Please use format like \'["drive", "gmail"]\'.'
        )
        # Fallback for non-JSON or badly formatted JSON
        # Consider if a fallback to comma-separated parsing is desired for backward compatibility or remove.
        # For now, strict parsing and warning.

    if not capabilities:  # This condition includes empty JSON array "[]"
        logger.warning(
            "No GOOGLE_WORKSPACE_ENABLED_CAPABILITIES specified or list is empty. "
            "All tools might be disabled depending on Hub filtering. "
            "(Note: FastMCP relies on Hub filtering based on declared capabilities.)"
        )
    else:
        logger.info(f"Declared Google Workspace capabilities via env var: {capabilities}")

    return capabilities
