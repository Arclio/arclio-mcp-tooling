"""
MCP server utilities for Google Workspace integration.
This file now contains utility functions, like parsing capabilities.
"""

import logging
import os

logger = logging.getLogger(__name__)


# Parse enabled capabilities from environment
def get_enabled_capabilities() -> set[str]:
    """
    Get the set of enabled capabilities from environment variables.

    Returns:
        set[str]: Enabled capability names
    """
    capabilities_str = os.environ.get("GSUITE_ENABLED_CAPABILITIES", "")
    if not capabilities_str:
        logger.warning(
            "No GSUITE_ENABLED_CAPABILITIES specified. All tools will be disabled."
            " (Note: FastMCP relies on Hub filtering based on declared capabilities.)"
        )
        # FastMCP handles capability filtering based on Hub requests
        # Return empty set, but actual filtering is external
        return set()

    capabilities = {cap.strip().lower() for cap in capabilities_str.split(",") if cap.strip()}
    logger.info(f"Declared G Suite capabilities via env var: {capabilities}")
    return capabilities
