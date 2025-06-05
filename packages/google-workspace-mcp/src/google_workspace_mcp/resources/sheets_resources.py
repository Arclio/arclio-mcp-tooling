import logging
from typing import Any

from google_workspace_mcp.app import mcp
from google_workspace_mcp.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)


@mcp.resource("sheets://spreadsheets/{spreadsheet_id}/metadata")
async def get_spreadsheet_metadata_resource(spreadsheet_id: str) -> dict[str, Any]:
    """
    Retrieves metadata for a specific Google Spreadsheet.
    Maps to URI: sheets://spreadsheets/{spreadsheet_id}/metadata
    """
    logger.info(f"Executing get_spreadsheet_metadata_resource for spreadsheet_id: {spreadsheet_id}")
    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required in the URI path.")

    sheets_service = SheetsService()
    metadata = sheets_service.get_spreadsheet_metadata(spreadsheet_id=spreadsheet_id)

    if isinstance(metadata, dict) and metadata.get("error"):
        raise ValueError(metadata.get("message", "Error retrieving spreadsheet metadata"))

    if not metadata:
        raise ValueError(f"Could not retrieve metadata for spreadsheet ID: {spreadsheet_id}")

    return metadata


@mcp.resource("sheets://spreadsheets/{spreadsheet_id}/sheets/{sheet_identifier}/metadata")
async def get_specific_sheet_metadata_resource(spreadsheet_id: str, sheet_identifier: str) -> dict[str, Any]:
    """
    Retrieves metadata for a specific sheet within a Google Spreadsheet,
    identified by its title (name) or numeric sheetId.
    Maps to URI: sheets://spreadsheets/{spreadsheet_id}/sheets/{sheet_identifier}/metadata
    """
    logger.info(
        f"Executing get_specific_sheet_metadata_resource for spreadsheet: {spreadsheet_id}, sheet_identifier: {sheet_identifier}"
    )
    if not spreadsheet_id or not sheet_identifier:
        raise ValueError("Spreadsheet ID and sheet identifier (name or ID) are required.")

    sheets_service = SheetsService()
    # Fetch metadata for all sheets first
    full_metadata = sheets_service.get_spreadsheet_metadata(
        spreadsheet_id=spreadsheet_id,
        fields="sheets(properties(sheetId,title,index,sheetType,gridProperties))",
    )

    if isinstance(full_metadata, dict) and full_metadata.get("error"):
        raise ValueError(full_metadata.get("message", "Error retrieving spreadsheet to find sheet metadata"))

    if not full_metadata or not full_metadata.get("sheets"):
        raise ValueError(f"No sheets found in spreadsheet {spreadsheet_id} or metadata incomplete.")

    found_sheet = None
    for sheet in full_metadata.get("sheets", []):
        props = sheet.get("properties", {})
        # Try matching by numeric ID first, then by title
        if str(props.get("sheetId")) == sheet_identifier:
            found_sheet = props
            break
        if props.get("title", "").lower() == sheet_identifier.lower():
            found_sheet = props
            break

    if not found_sheet:
        raise ValueError(f"Sheet '{sheet_identifier}' not found in spreadsheet '{spreadsheet_id}'.")

    return found_sheet
