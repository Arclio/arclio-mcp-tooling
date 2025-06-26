"""
Google Sheets service implementation.
"""

import logging
from typing import Any

from googleapiclient.errors import HttpError

from google_workspace_mcp.services.base import BaseGoogleService

logger = logging.getLogger(__name__)


class SheetsService(BaseGoogleService):
    """
    Service for interacting with the Google Sheets API.
    """

    def __init__(self):
        """Initialize the Google Sheets service."""
        super().__init__(service_name="sheets", version="v4")
        # API calls will be like self.service.spreadsheets().<method>

    def create_spreadsheet(self, title: str) -> dict[str, Any] | None:
        """
        Creates a new Google Spreadsheet with the specified title.

        Args:
            title: The title for the new spreadsheet.

        Returns:
            A dictionary containing the created spreadsheet's ID, title, and URL,
            or an error dictionary.
        """
        try:
            logger.info(f"Creating new Google Spreadsheet with title: '{title}'")
            spreadsheet_body = {"properties": {"title": title}}
            spreadsheet = (
                self.service.spreadsheets().create(body=spreadsheet_body).execute()
            )
            spreadsheet_id = spreadsheet.get("spreadsheetId")
            logger.info(
                f"Successfully created spreadsheet: {spreadsheet.get('properties', {}).get('title')} (ID: {spreadsheet_id})"
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "title": spreadsheet.get("properties", {}).get("title"),
                "spreadsheet_url": spreadsheet.get("spreadsheetUrl"),
            }
        except HttpError as error:
            logger.error(f"Error creating spreadsheet '{title}': {error}")
            return self.handle_api_error("create_spreadsheet", error)
        except Exception as e:
            logger.exception(f"Unexpected error creating spreadsheet '{title}'")
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "create_spreadsheet",
            }

    def read_range(self, spreadsheet_id: str, range_a1: str) -> dict[str, Any] | None:
        """
        Reads values from a specified range in a Google Spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            range_a1: The A1 notation of the range to read (e.g., "Sheet1!A1:C5", or "A1:C5" if only one sheet).

        Returns:
            A dictionary containing the 'range', 'majorDimension', and 'values' (list of lists),
            or an error dictionary.
        """
        try:
            logger.info(
                f"Reading range '{range_a1}' from spreadsheet ID: {spreadsheet_id}"
            )
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_a1)
                .execute()
            )

            # result will contain 'range', 'majorDimension', 'values'
            # 'values' is a list of lists.
            logger.info(
                f"Successfully read range '{result.get('range')}' from spreadsheet ID: {spreadsheet_id}. Got {len(result.get('values', []))} rows."
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "range_requested": range_a1,  # The input range
                "range_returned": result.get(
                    "range"
                ),  # The actual range returned by API
                "major_dimension": result.get("majorDimension"),
                "values": result.get(
                    "values", []
                ),  # Default to empty list if no values
            }
        except HttpError as error:
            logger.error(
                f"Error reading range '{range_a1}' from spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("read_range", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error reading range '{range_a1}' from spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "read_range",
            }

    def write_range(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any] | None:
        """
        Writes data to a specified range in a Google Spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            range_a1: The A1 notation of the range to write (e.g., "Sheet1!A1:C5").
            values: A list of lists representing the data to write.
            value_input_option: How the input data should be interpreted.
                                "USER_ENTERED" will try to parse values as if a user typed them (e.g., formulas).
                                "RAW" will take values literally. Defaults to "USER_ENTERED".
        Returns:
            A dictionary containing details of the update (e.g., updatedRange, updatedCells),
            or an error dictionary.
        """
        try:
            logger.info(
                f"Writing to range '{range_a1}' in spreadsheet ID: {spreadsheet_id} with {len(values)} rows. Value input option: {value_input_option}"
            )
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_a1,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            # result typically includes: spreadsheetId, updatedRange, updatedRows, updatedColumns, updatedCells
            logger.info(
                f"Successfully wrote to range '{result.get('updatedRange')}' in spreadsheet ID: {spreadsheet_id}. Updated {result.get('updatedCells')} cells."
            )
            return {
                "spreadsheet_id": result.get(
                    "spreadsheetId"
                ),  # Or use the input spreadsheet_id
                "updated_range": result.get("updatedRange"),
                "updated_rows": result.get("updatedRows"),
                "updated_columns": result.get("updatedColumns"),
                "updated_cells": result.get("updatedCells"),
            }
        except HttpError as error:
            logger.error(
                f"Error writing to range '{range_a1}' in spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("write_range", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error writing to range '{range_a1}' in spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "write_range",
            }

    def append_rows(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
        insert_data_option: str = "INSERT_ROWS",
    ) -> dict[str, Any] | None:
        """
        Appends rows of data to a sheet or table within a Google Spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            range_a1: The A1 notation of a range indicating the sheet or table to append to
                      (e.g., "Sheet1" to append to the first empty row, or "Sheet1!A1:C1" to append after a table).
            values: A list of lists representing the data rows to append.
            value_input_option: How the input data should be interpreted. Defaults to "USER_ENTERED".
            insert_data_option: How the new data should be inserted. "INSERT_ROWS" inserts new rows,
                                "OVERWRITE" overwrites existing rows if the append range points to them.
                                Defaults to "INSERT_ROWS".
        Returns:
            A dictionary containing details of the append operation (e.g., updates to named ranges, tableRange),
            or an error dictionary.
        """
        try:
            logger.info(
                f"Appending rows to range '{range_a1}' in spreadsheet ID: {spreadsheet_id} with {len(values)} rows. Value input: {value_input_option}, Insert option: {insert_data_option}"
            )
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_a1,
                    valueInputOption=value_input_option,
                    insertDataOption=insert_data_option,
                    body=body,
                )
                .execute()
            )
            # result typically includes: spreadsheetId, tableRange (if appended to a table), updates (if named ranges/etc. were affected)
            logger.info(
                f"Successfully appended rows to spreadsheet ID: {spreadsheet_id}. Updates: {result.get('updates')}"
            )
            return {
                "spreadsheet_id": result.get(
                    "spreadsheetId"
                ),  # Or use the input spreadsheet_id
                "table_range_updated": result.get(
                    "tableRange"
                ),  # The range of the new data
                "updates": result.get(
                    "updates"
                ),  # Info about other updates, e.g. to named ranges
            }
        except HttpError as error:
            logger.error(
                f"Error appending rows to range '{range_a1}' in spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("append_rows", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error appending rows to range '{range_a1}' in spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "append_rows",
            }

    def clear_range(self, spreadsheet_id: str, range_a1: str) -> dict[str, Any] | None:
        """
        Clears values from a specified range in a Google Spreadsheet.
        Note: This typically clears values only, not formatting unless specified in a more complex request body.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            range_a1: The A1 notation of the range to clear (e.g., "Sheet1!A1:C5").

        Returns:
            A dictionary containing the cleared range and spreadsheet ID, or an error dictionary.
        """
        try:
            logger.info(
                f"Clearing range '{range_a1}' in spreadsheet ID: {spreadsheet_id}"
            )
            # The body for clear is an empty JSON object {}.
            result = (
                self.service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_a1, body={})
                .execute()
            )
            # result typically includes: spreadsheetId, clearedRange
            logger.info(
                f"Successfully cleared range '{result.get('clearedRange')}' in spreadsheet ID: {spreadsheet_id}."
            )
            return {
                "spreadsheet_id": result.get(
                    "spreadsheetId"
                ),  # Or use the input spreadsheet_id
                "cleared_range": result.get("clearedRange"),
            }
        except HttpError as error:
            logger.error(
                f"Error clearing range '{range_a1}' from spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("clear_range", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error clearing range '{range_a1}' from spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "clear_range",
            }

    def add_sheet(self, spreadsheet_id: str, title: str) -> dict[str, Any] | None:
        """
        Adds a new sheet to the specified spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            title: The title for the new sheet.

        Returns:
            A dictionary containing properties of the newly added sheet (e.g., sheetId, title, index),
            or an error dictionary.
        """
        try:
            logger.info(
                f"Adding new sheet with title '{title}' to spreadsheet ID: {spreadsheet_id}"
            )
            requests = [{"addSheet": {"properties": {"title": title}}}]
            body = {"requests": requests}
            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )

            # The response contains a list of replies, one for each request.
            # The addSheet reply contains the properties of the new sheet.
            new_sheet_properties = None
            if response and response.get("replies"):
                for reply in response.get("replies"):
                    if "addSheet" in reply:
                        new_sheet_properties = reply["addSheet"].get("properties")
                        break

            if not new_sheet_properties:
                logger.error(
                    f"Failed to add sheet '{title}' or extract properties from response for spreadsheet {spreadsheet_id}."
                )
                return {
                    "error": True,
                    "error_type": "api_response_error",
                    "message": "Failed to add sheet or parse response.",
                    "operation": "add_sheet",
                }

            logger.info(
                f"Successfully added sheet: {new_sheet_properties.get('title')} (ID: {new_sheet_properties.get('sheetId')}) to spreadsheet ID: {spreadsheet_id}"
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "sheet_properties": new_sheet_properties,
            }
        except HttpError as error:
            logger.error(
                f"Error adding sheet '{title}' to spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("add_sheet", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error adding sheet '{title}' to spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "add_sheet",
            }

    def delete_sheet(self, spreadsheet_id: str, sheet_id: int) -> dict[str, Any] | None:
        """
        Deletes a sheet from the specified spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            sheet_id: The numeric ID of the sheet to delete.

        Returns:
            A dictionary indicating success (spreadsheetId and deleted sheetId) or an error dictionary.
        """
        try:
            logger.info(
                f"Deleting sheet ID: {sheet_id} from spreadsheet ID: {spreadsheet_id}"
            )
            requests = [{"deleteSheet": {"sheetId": sheet_id}}]
            body = {"requests": requests}
            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )

            # A successful deleteSheet request usually doesn't return detailed content in the reply.
            # The overall response.spreadsheetId confirms the operation was on the correct spreadsheet.
            logger.info(
                f"Successfully submitted deletion request for sheet ID: {sheet_id} in spreadsheet ID: {spreadsheet_id}. Response: {response}"
            )
            return {
                "spreadsheet_id": spreadsheet_id,
                "deleted_sheet_id": sheet_id,
                "success": True,
            }
        except HttpError as error:
            logger.error(
                f"Error deleting sheet ID {sheet_id} from spreadsheet {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("delete_sheet", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error deleting sheet ID {sheet_id} from spreadsheet {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "delete_sheet",
            }

    def get_spreadsheet_metadata(
        self, spreadsheet_id: str, fields: str | None = None
    ) -> dict[str, Any] | None:
        """
        Retrieves metadata for a specific Google Spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            fields: Optional. A string specifying which fields to include in the response,
                    e.g., "properties,sheets.properties,namedRanges". Defaults to basic properties and sheet info.

        Returns:
            A dictionary containing spreadsheet metadata or an error dictionary.
        """
        try:
            logger.info(
                f"Fetching metadata for spreadsheet ID: {spreadsheet_id}"
                + (f" with fields: {fields}" if fields else "")
            )
            if fields is None:
                fields = "spreadsheetId,properties,sheets(properties(sheetId,title,index,sheetType,gridProperties))"

            spreadsheet_metadata = (
                self.service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id, fields=fields)
                .execute()
            )
            logger.info(
                f"Successfully fetched metadata for spreadsheet: {spreadsheet_metadata.get('properties', {}).get('title')}"
            )
            return spreadsheet_metadata
        except HttpError as error:
            logger.error(
                f"Error fetching metadata for spreadsheet ID {spreadsheet_id}: {error}"
            )
            return self.handle_api_error("get_spreadsheet_metadata", error)
        except Exception as e:
            logger.exception(
                f"Unexpected error fetching metadata for spreadsheet ID {spreadsheet_id}"
            )
            return {
                "error": True,
                "error_type": "unexpected_service_error",
                "message": str(e),
                "operation": "get_spreadsheet_metadata",
            }

    def create_chart_on_sheet(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        chart_type: str,
        num_rows: int,
        num_cols: int,
        title: str,
    ) -> dict[str, Any] | None:
        """
        Adds a new chart to a sheet, handling different chart types correctly.

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet.
            sheet_id: The numeric ID of the sheet to add the chart to.
            chart_type: The API-specific type of chart ('COLUMN', 'LINE', 'PIE_CHART').
            num_rows: The number of rows in the data range.
            num_cols: The number of columns in the data range.
            title: The title of the chart.

        Returns:
            A dictionary containing the properties of the newly created chart or an error dictionary.
        """
        try:
            logger.info(f"Constructing spec for chart '{title}' of type '{chart_type}'")

            chart_spec = {"title": title}

            if chart_type == "PIE_CHART":
                chart_spec["pieChart"] = {
                    "domain": {
                        "sourceRange": {
                            "sources": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": num_rows,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": 1,
                                }
                            ]
                        }
                    },
                    "series": {
                        "sourceRange": {
                            "sources": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": num_rows,
                                    "startColumnIndex": 1,
                                    "endColumnIndex": 2,
                                }
                            ]
                        }
                    },
                    "legendPosition": "LABELED_LEGEND",
                }
            else:  # For BAR, COLUMN, LINE charts
                # --- START OF FIX: Correctly structure the domain object ---
                domain_spec = {
                    "domain": {
                        "sourceRange": {
                            "sources": [
                                {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": num_rows,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": 1,
                                }
                            ]
                        }
                    }
                }
                # --- END OF FIX ---

                series = []
                for i in range(1, num_cols):
                    series.append(
                        {
                            "series": {
                                "sourceRange": {
                                    "sources": [
                                        {
                                            "sheetId": sheet_id,
                                            "startRowIndex": 0,
                                            "endRowIndex": num_rows,
                                            "startColumnIndex": i,
                                            "endColumnIndex": i + 1,
                                        }
                                    ]
                                }
                            },
                            "targetAxis": "LEFT_AXIS",
                        }
                    )

                chart_spec["basicChart"] = {
                    "chartType": chart_type,
                    "legendPosition": "BOTTOM_LEGEND",
                    "axis": [
                        {"position": "BOTTOM_AXIS"},
                        {"position": "LEFT_AXIS"},
                    ],
                    "domains": [domain_spec],  # Use the corrected domain object
                    "series": series,
                }

            requests = [
                {
                    "addChart": {
                        "chart": {
                            "spec": chart_spec,
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": sheet_id,
                                        "rowIndex": num_rows + 2,
                                        "columnIndex": 0,
                                    },
                                }
                            },
                        }
                    }
                }
            ]

            body = {"requests": requests}
            # The google-api-python-client expects snake_case keys in the body,
            # so we'll convert our camelCase spec to snake_case before sending.
            # This is a good practice for robustness.
            import humps

            snake_body = humps.decamelize(body)

            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=snake_body)
                .execute()
            )

            new_chart_properties = (
                response.get("replies", [{}])[0].get("addChart", {}).get("chart")
            )
            if not new_chart_properties:
                raise ValueError("Failed to create chart or parse response.")

            logger.info(
                f"Successfully created chart with ID: {new_chart_properties.get('chartId')}"
            )
            return new_chart_properties

        except HttpError as error:
            logger.error(f"Google API error in create_chart_on_sheet: {error.content}")
            return self.handle_api_error("create_chart_on_sheet", error)
        except Exception as e:
            return self.handle_api_error("create_chart_on_sheet", e)
