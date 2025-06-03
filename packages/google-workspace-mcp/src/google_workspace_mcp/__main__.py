"""
Main entry point for running the MCP server via python -m google_workspace_mcp
"""

import asyncio

from google_workspace_mcp import config  # noqa: F401
from google_workspace_mcp.app import mcp  # Import instance from central location

# Import all modules that register components with the FastMCP instance
from google_workspace_mcp.prompts import calendar as calendar_prompts  # noqa: F401
from google_workspace_mcp.prompts import drive as drive_prompts  # noqa: F401
from google_workspace_mcp.prompts import gmail as gmail_prompts  # noqa: F401
from google_workspace_mcp.prompts import slides as slides_prompts  # noqa: F401

# Register resources
from google_workspace_mcp.resources import calendar as calendar_resources  # noqa: F401
from google_workspace_mcp.resources import drive as drive_resources  # noqa: F401
from google_workspace_mcp.resources import gmail as gmail_resources  # noqa: F401
from google_workspace_mcp.resources import sheets_resources  # noqa: F401
from google_workspace_mcp.resources import slides as slides_resources  # noqa: F401

# Register tools
from google_workspace_mcp.tools import (  # noqa: F401
    calendar_tools,
    docs_tools,
    drive_tools,
    gmail_tools,
    sheets_tools,
    slides_tools,
)


def main():
    """Main entry point for the MCP server."""
    try:
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")


if __name__ == "__main__":
    main()
