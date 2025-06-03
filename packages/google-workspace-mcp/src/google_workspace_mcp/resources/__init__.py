"""Resources for google-workspace-mcp."""

from .sheets_resources import (
    get_specific_sheet_metadata_resource,
    get_spreadsheet_metadata_resource,
)
from .slides import get_markdown_deck_formatting_guide

__all__ = [
    "get_markdown_deck_formatting_guide",
    "get_spreadsheet_metadata_resource",
    "get_specific_sheet_metadata_resource",
]
