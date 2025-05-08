"""
Main entry point for running the MCP server via python -m arclio_mcp_gsuite
"""

import logging

# Import tool modules to register them with FastMCP
# (Linter may flag as unused, but import is necessary for registration/config)
from arclio_mcp_gsuite import config  # noqa: F401
from arclio_mcp_gsuite.app import mcp  # Import instance from central location

# Import all prompt modules
from arclio_mcp_gsuite.prompts import calendar as calendar_prompts  # noqa: F401
from arclio_mcp_gsuite.prompts import drive as drive_prompts  # noqa: F401
from arclio_mcp_gsuite.prompts import gmail as gmail_prompts  # noqa: F401
from arclio_mcp_gsuite.prompts import slides as slides_prompts  # noqa: F401

# Import all resource modules
from arclio_mcp_gsuite.resources import calendar as calendar_resources  # noqa: F401
from arclio_mcp_gsuite.resources import drive as drive_resources  # noqa: F401
from arclio_mcp_gsuite.resources import gmail as gmail_resources  # noqa: F401
from arclio_mcp_gsuite.resources import slides as slides_resources  # noqa: F401

# Import all tool modules
from arclio_mcp_gsuite.tools import calendar as calendar_tools  # noqa: F401
from arclio_mcp_gsuite.tools import drive as drive_tools  # noqa: F401
from arclio_mcp_gsuite.tools import gmail as gmail_tools  # noqa: F401
from arclio_mcp_gsuite.tools import slides as slides_tools  # noqa: F401

# Tool, Resource, and Prompt registration happens implicitly when the modules containing
# the respective decorators are imported.

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for running the MCP server for Google Workspace.
    This function is used as a console script entry point.
    """
    logger.info("Starting MCP server for Google Workspace... local")
    # FastMCP handles communication via specified transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    logger.info("Starting MCP server for Google Workspace via __main__ entry point...")
    main()
