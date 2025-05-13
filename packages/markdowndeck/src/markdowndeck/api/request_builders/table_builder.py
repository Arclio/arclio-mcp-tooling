"""Table request builder for Google Slides API requests."""

import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import TableElement

logger = logging.getLogger(__name__)


class TableRequestBuilder(BaseRequestBuilder):
    """Builder for table-related Google Slides API requests."""

    def generate_table_element_requests(
        self, element: TableElement, slide_id: str
    ) -> list[dict]:
        """
        Generate requests for a table element.

        Args:
            element: The table element
            slide_id: The slide ID

        Returns:
            List of request dictionaries
        """
        requests = []

        # Calculate position and size
        position = getattr(element, "position", (100, 100))
        size = getattr(element, "size", (400, 200))

        # Ensure element has a valid object_id
        if not element.object_id:
            element.object_id = self._generate_id(f"table_{slide_id}")
            logger.debug(
                f"Generated missing object_id for table element: {element.object_id}"
            )

        # Count rows including headers if present
        row_count = len(element.rows) + (1 if element.headers else 0)
        # Find the max number of columns across all rows and headers
        col_count = max(
            len(element.headers) if element.headers else 0,
            max(len(row) for row in element.rows) if element.rows else 0,
        )

        if col_count == 0:
            return []  # Skip if table has no data

        # Create table
        create_table_request = {
            "createTable": {
                "objectId": element.object_id,
                "rows": row_count,
                "columns": col_count,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": size[0], "unit": "PT"},
                        "height": {"magnitude": size[1], "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": position[0],
                        "translateY": position[1],
                        "unit": "PT",
                    },
                },
            }
        }
        requests.append(create_table_request)

        # Insert header text if present
        row_index = 0
        if element.headers:
            for col_index, header in enumerate(element.headers):
                if col_index < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": row_index,
                                "columnIndex": col_index,
                            },
                            "text": header,
                            "insertionIndex": 0,
                        }
                    }
                    requests.append(insert_text_request)

            # Set header style (bold)
            for col_index in range(min(len(element.headers), col_count)):
                style_request = self._apply_text_formatting(
                    element_id=element.object_id,
                    style={"bold": True},
                    fields="bold",
                    range_type="ALL",
                    cell_location={
                        "rowIndex": row_index,
                        "columnIndex": col_index,
                    },
                )
                requests.append(style_request)

                # Add cell fill for header - FIX THE FIELD NAME HERE
                fill_request = {
                    "updateTableCellProperties": {
                        "objectId": element.object_id,
                        "tableRange": {
                            "location": {
                                "rowIndex": row_index,
                                "columnIndex": col_index,
                            },
                            "rowSpan": 1,
                            "columnSpan": 1,
                        },
                        # CRITICAL FIX: Use camelCase for this property name
                        "tableCellProperties": {
                            "tableCellBackgroundFill": {
                                "solidFill": {
                                    "color": {
                                        "rgbColor": {
                                            "red": 0.95,
                                            "green": 0.95,
                                            "blue": 0.95,
                                        }
                                    }
                                }
                            }
                        },
                        "fields": "tableCellProperties.tableCellBackgroundFill.solidFill.color",
                    }
                }
                requests.append(fill_request)

            row_index += 1

        # Insert row text
        for row_idx, row in enumerate(element.rows):
            for col_idx, cell in enumerate(row):
                if col_idx < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": row_idx + row_index,
                                "columnIndex": col_idx,
                            },
                            "text": cell,
                            "insertionIndex": 0,
                        }
                    }
                    requests.append(insert_text_request)

        # Apply table styles if specified in directives
        if hasattr(element, "directives") and element.directives:
            # ENHANCEMENT: Apply standard border directive
            self._apply_table_borders(element, requests, row_count, col_count)

            # ENHANCEMENT: Apply cell alignment
            self._apply_cell_alignment(element, requests, row_count, col_count)

            # ENHANCEMENT: Apply cell background colors
            self._apply_cell_background_colors(element, requests, row_count, col_count)

        return requests

    def _apply_table_borders(
        self,
        element: TableElement,
        requests: list[dict],
        row_count: int,
        col_count: int,
    ) -> None:
        """
        Apply border styling to the table.

        Args:
            element: The table element
            requests: The request list to append to
            row_count: Number of rows in the table
            col_count: Number of columns in the table
        """
        if "border" not in element.directives:
            return

        border_value = element.directives["border"]

        # Default border properties
        weight = {"magnitude": 1, "unit": "PT"}
        dash_style = "SOLID"

        # FIX: The color should be inside 'tableBorderFill', not directly in 'tableBorderProperties'
        rgb_color = {"red": 0, "green": 0, "blue": 0}

        # Parse border directive
        if isinstance(border_value, str):
            parts = border_value.split()

            for part in parts:
                # Check if it's a width specification
                if part.endswith("pt") or part.endswith("px"):
                    try:
                        width_value = float(part.rstrip("ptx"))
                        weight = {"magnitude": width_value, "unit": "PT"}
                    except ValueError:
                        pass
                # Check if it's a style specification
                elif part.lower() in ["solid", "dashed", "dotted"]:
                    style_map = {
                        "solid": "SOLID",
                        "dashed": "DASH",
                        "dotted": "DOT",
                    }
                    dash_style = style_map.get(part.lower(), "SOLID")
                # Check if it's a color specification
                elif part.startswith("#"):
                    try:
                        rgb = self._hex_to_rgb(part)
                        rgb_color = rgb
                    except ValueError:
                        pass
                # Check if it's a named color
                elif part.lower() in [
                    "black",
                    "white",
                    "red",
                    "green",
                    "blue",
                    "yellow",
                    "cyan",
                    "magenta",
                ]:
                    # Map named colors to RGB
                    color_map = {
                        "black": {"red": 0, "green": 0, "blue": 0},
                        "white": {"red": 1, "green": 1, "blue": 1},
                        "red": {"red": 1, "green": 0, "blue": 0},
                        "green": {"red": 0, "green": 1, "blue": 0},
                        "blue": {"red": 0, "green": 0, "blue": 1},
                        "yellow": {"red": 1, "green": 1, "blue": 0},
                        "cyan": {"red": 0, "green": 1, "blue": 1},
                        "magenta": {"red": 1, "green": 0, "blue": 1},
                    }
                    rgb_color = color_map.get(part.lower())

        # Determine border positions to apply
        border_positions = ["ALL"]  # Default to all borders

        # Check if a specific border position is specified
        if "border-position" in element.directives:
            border_pos = element.directives["border-position"].upper()
            valid_positions = [
                "ALL",
                "OUTER",
                "INNER",
                "LEFT",
                "RIGHT",
                "TOP",
                "BOTTOM",
                "INNER_HORIZONTAL",
                "INNER_VERTICAL",
                "DIAGONAL_DOWN",
                "DIAGONAL_UP",
            ]

            if border_pos in valid_positions:
                border_positions = [border_pos]

        # Apply the border style to each specified position
        for position in border_positions:
            # FIX: Corrected structure for table border properties
            border_style_request = {
                "updateTableBorderProperties": {
                    "objectId": element.object_id,
                    "tableRange": {
                        "location": {
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": row_count,
                        "columnSpan": col_count,
                    },
                    "borderPosition": position,
                    "tableBorderProperties": {
                        "weight": weight,
                        "dashStyle": dash_style,
                        # FIX: Corrected structure with tableBorderFill
                        "tableBorderFill": {
                            "solidFill": {"color": {"rgbColor": rgb_color}}
                        },
                    },
                    "fields": "tableBorderProperties.weight,tableBorderProperties.dashStyle,tableBorderProperties.tableBorderFill.solidFill.color.rgbColor",
                }
            }

            requests.append(border_style_request)
            logger.debug(f"Applied {position} border to table {element.object_id}")

    def _apply_cell_alignment(
        self,
        element: TableElement,
        requests: list[dict],
        row_count: int,
        col_count: int,
    ) -> None:
        """
        Apply cell alignment based on directives.

        Args:
            element: The table element
            requests: The request list to append to
            row_count: Number of rows in the table
            col_count: Number of columns in the table
        """
        # Check for cell alignment directive
        if "cell-align" not in element.directives:
            return

        alignment_value = element.directives["cell-align"]
        if not isinstance(alignment_value, str):
            return

        # FIX: Map alignment value to API enum value, not string
        # Horizontal alignment values
        h_alignment_map = {
            "left": "START",
            "center": "CENTER",
            "right": "END",
            "justify": "JUSTIFIED",
        }

        # Vertical alignment values
        v_alignment_map = {
            "top": "TOP",
            "middle": "MIDDLE",
            "bottom": "BOTTOM",
        }

        # Determine if this is horizontal or vertical alignment
        if alignment_value.lower() in h_alignment_map:
            # Horizontal alignment - contentAlignment field
            api_alignment = h_alignment_map.get(alignment_value.lower())
            field_name = "contentAlignment"
        elif alignment_value.lower() in v_alignment_map:
            # Vertical alignment - contentVerticalAlignment field
            api_alignment = v_alignment_map.get(alignment_value.lower())
            field_name = "contentVerticalAlignment"
        else:
            return

        # Apply to all cells or specific cells based on directives
        row_start = 0
        row_span = row_count
        col_start = 0
        col_span = col_count

        # Check for cell range directives
        if "cell-range" in element.directives:
            cell_range = element.directives["cell-range"]
            if isinstance(cell_range, str):
                # Parse range in format "row1,col1:row2,col2"
                try:
                    parts = cell_range.split(":")
                    if len(parts) == 2:
                        start_parts = parts[0].split(",")
                        end_parts = parts[1].split(",")

                        if len(start_parts) == 2 and len(end_parts) == 2:
                            row_start = int(start_parts[0])
                            col_start = int(start_parts[1])
                            row_span = int(end_parts[0]) - row_start + 1
                            col_span = int(end_parts[1]) - col_start + 1
                except ValueError:
                    # If parsing fails, use default (all cells)
                    logger.warning(
                        f"Failed to parse cell range: {cell_range}, using default"
                    )

        # Create cell properties update request
        # FIX: Ensure all property names use camelCase consistently
        cell_align_request = {
            "updateTableCellProperties": {
                "objectId": element.object_id,
                "tableRange": {
                    "location": {
                        "rowIndex": row_start,
                        "columnIndex": col_start,
                    },
                    "rowSpan": row_span,
                    "columnSpan": col_span,
                },
                "tableCellProperties": {field_name: api_alignment},
                "fields": f"tableCellProperties.{field_name}",
            }
        }

        requests.append(cell_align_request)
        logger.debug(
            f"Applied {alignment_value} alignment to cells in table {element.object_id}"
        )

    def _apply_cell_background_colors(
        self,
        element: TableElement,
        requests: list[dict],
        row_count: int,
        col_count: int,
    ) -> None:
        """
        Apply cell background colors based on directives.

        Args:
            element: The table element
            requests: The request list to append to
            row_count: Number of rows in the table
            col_count: Number of columns in the table
        """
        # Check for cell background directive
        if "cell-background" not in element.directives:
            return

        bg_value = element.directives["cell-background"]

        # Handle different formats of the directive value
        color = None
        fields = ""

        # Check if it's a hex color
        if isinstance(bg_value, str) and bg_value.startswith("#"):
            try:
                rgb = self._hex_to_rgb(bg_value)
                color = {"rgbColor": rgb}
                fields = "tableCellProperties.tableCellBackgroundFill.solidFill.color.rgbColor"
            except ValueError:
                return
        # Check if it's a theme color
        elif isinstance(bg_value, str) and bg_value.upper() in [
            "TEXT1",
            "TEXT2",
            "BACKGROUND1",
            "BACKGROUND2",
            "ACCENT1",
            "ACCENT2",
            "ACCENT3",
            "ACCENT4",
            "ACCENT5",
            "ACCENT6",
        ]:
            color = {"themeColor": bg_value.upper()}
            fields = (
                "tableCellProperties.tableCellBackgroundFill.solidFill.color.themeColor"
            )
        # Check if it's a named color
        elif isinstance(bg_value, str) and bg_value.lower() in [
            "white",
            "black",
            "red",
            "green",
            "blue",
            "yellow",
            "cyan",
            "magenta",
        ]:
            color_map = {
                "black": {"red": 0, "green": 0, "blue": 0},
                "white": {"red": 1, "green": 1, "blue": 1},
                "red": {"red": 1, "green": 0, "blue": 0},
                "green": {"red": 0, "green": 1, "blue": 0},
                "blue": {"red": 0, "green": 0, "blue": 1},
                "yellow": {"red": 1, "green": 1, "blue": 0},
                "cyan": {"red": 0, "green": 1, "blue": 1},
                "magenta": {"red": 1, "green": 0, "blue": 1},
            }
            color = {"rgbColor": color_map.get(bg_value.lower())}
            fields = (
                "tableCellProperties.tableCellBackgroundFill.solidFill.color.rgbColor"
            )
        else:
            return

        # Apply to all cells or specific cells based on directives
        row_start = 0
        row_span = row_count
        col_start = 0
        col_span = col_count

        # Check for cell range directives
        if "cell-range" in element.directives:
            cell_range = element.directives["cell-range"]
            if isinstance(cell_range, str):
                # Parse range in format "row1,col1:row2,col2"
                try:
                    parts = cell_range.split(":")
                    if len(parts) == 2:
                        start_parts = parts[0].split(",")
                        end_parts = parts[1].split(",")

                        if len(start_parts) == 2 and len(end_parts) == 2:
                            row_start = int(start_parts[0])
                            col_start = int(start_parts[1])
                            row_span = int(end_parts[0]) - row_start + 1
                            col_span = int(end_parts[1]) - col_start + 1
                except ValueError:
                    # If parsing fails, use default (all cells)
                    logger.warning(
                        f"Failed to parse cell range: {cell_range}, using default"
                    )

        # Create cell properties update request
        # FIX: Ensure consistent camelCase in all structures
        bg_request = {
            "updateTableCellProperties": {
                "objectId": element.object_id,
                "tableRange": {
                    "location": {
                        "rowIndex": row_start,
                        "columnIndex": col_start,
                    },
                    "rowSpan": row_span,
                    "columnSpan": col_span,
                },
                "tableCellProperties": {
                    "tableCellBackgroundFill": {"solidFill": {"color": color}}
                },
                "fields": fields,
            }
        }

        requests.append(bg_request)
        logger.debug(
            f"Applied background color to cells in table {element.object_id} at range ({row_start},{col_start})-({row_start + row_span - 1},{col_start + col_span - 1})"
        )
