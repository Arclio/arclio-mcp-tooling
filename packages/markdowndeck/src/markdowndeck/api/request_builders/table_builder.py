import logging

from markdowndeck.api.request_builders.base_builder import BaseRequestBuilder
from markdowndeck.models import TableElement, TextFormat, TextFormatType

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
        size = getattr(element, "size", None) or (400, 200)

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
        header_row_index = 0
        if element.headers:
            for col_index, header in enumerate(element.headers):
                if col_index < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": header_row_index,
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
                        "rowIndex": header_row_index,
                        "columnIndex": col_index,
                    },
                )
                requests.append(style_request)

        # Insert row text
        for r_idx, row in enumerate(element.rows):
            current_row_index = r_idx + (1 if element.headers else 0)
            for col_idx, cell in enumerate(row):
                if col_idx < col_count:
                    insert_text_request = {
                        "insertText": {
                            "objectId": element.object_id,
                            "cellLocation": {
                                "rowIndex": current_row_index,
                                "columnIndex": col_idx,
                            },
                            "text": cell,
                            "insertionIndex": 0,
                        }
                    }
                    requests.append(insert_text_request)

        # Apply table styles if specified in directives
        if hasattr(element, "directives") and element.directives:
            self._apply_table_borders(element, requests, row_count, col_count)
            self._apply_cell_alignment(element, requests, row_count, col_count)
            self._apply_cell_background_colors(element, requests, row_count, col_count)

        if hasattr(element, "row_directives"):
            for row_idx, directives in enumerate(element.row_directives):
                if not directives:
                    continue
                api_row_index = row_idx
                bg_color_val = directives.get("background")
                if bg_color_val:
                    # FIXED: Handle both raw strings and parsed dicts from directives.
                    if isinstance(bg_color_val, dict):
                        actual_bg_color = bg_color_val.get("value", {}).get(
                            "value"
                        ) or bg_color_val.get("value")
                    else:
                        actual_bg_color = bg_color_val

                    color_format = TextFormat(
                        0, 0, TextFormatType.BACKGROUND_COLOR, actual_bg_color
                    )
                    style = self._format_to_style(color_format)
                    if (
                        "backgroundColor" in style
                        and "opaqueColor" in style["backgroundColor"]
                    ):
                        requests.append(
                            {
                                "updateTableCellProperties": {
                                    "objectId": element.object_id,
                                    "tableRange": {
                                        "location": {
                                            "rowIndex": api_row_index,
                                            "columnIndex": 0,
                                        },
                                        "rowSpan": 1,
                                        "columnSpan": col_count,
                                    },
                                    "tableCellProperties": {
                                        "tableCellBackgroundFill": {
                                            "solidFill": {
                                                "color": style["backgroundColor"][
                                                    "opaqueColor"
                                                ]
                                            }
                                        }
                                    },
                                    "fields": "tableCellBackgroundFill.solidFill.color",
                                }
                            }
                        )

                color_val = directives.get("color")
                if color_val:
                    # FIXED: Handle both raw strings and parsed dicts from directives.
                    if isinstance(color_val, dict):
                        actual_color = color_val.get("value", {}).get(
                            "value"
                        ) or color_val.get("value")
                    else:
                        actual_color = color_val

                    if actual_color and isinstance(actual_color, str):
                        color_format = TextFormat(
                            0, 0, TextFormatType.COLOR, actual_color
                        )
                        style = self._format_to_style(color_format)
                        if "foregroundColor" in style:
                            for col_idx in range(col_count):
                                requests.append(
                                    self._apply_text_formatting(
                                        element_id=element.object_id,
                                        style={
                                            "foregroundColor": style["foregroundColor"]
                                        },
                                        fields="foregroundColor",
                                        range_type="ALL",
                                        cell_location={
                                            "rowIndex": api_row_index,
                                            "columnIndex": col_idx,
                                        },
                                    )
                                )

                if directives.get("bold"):
                    for col_idx in range(col_count):
                        requests.append(
                            self._apply_text_formatting(
                                element_id=element.object_id,
                                style={"bold": True},
                                fields="bold",
                                range_type="ALL",
                                cell_location={
                                    "rowIndex": api_row_index,
                                    "columnIndex": col_idx,
                                },
                            )
                        )

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
        """
        if "border" not in element.directives:
            return

        border_value = element.directives["border"]
        weight = {"magnitude": 1, "unit": "PT"}
        dash_style = "SOLID"
        rgb_color = {"red": 0, "green": 0, "blue": 0}

        if isinstance(border_value, str):
            parts = border_value.split()
            for part in parts:
                if part.endswith("pt") or part.endswith("px"):
                    try:
                        width_value = float(part.rstrip("ptx"))
                        weight = {"magnitude": width_value, "unit": "PT"}
                    except ValueError:
                        pass
                elif part.lower() in ["solid", "dashed", "dotted"]:
                    style_map = {"solid": "SOLID", "dashed": "DASH", "dotted": "DOT"}
                    dash_style = style_map.get(part.lower(), "SOLID")
                elif part.startswith("#"):
                    try:
                        rgb = self._hex_to_rgb(part)
                        rgb_color = rgb
                    except ValueError:
                        pass
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

        border_positions = ["ALL"]
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

        for position in border_positions:
            border_style_request = {
                "updateTableBorderProperties": {
                    "objectId": element.object_id,
                    "tableRange": {
                        "location": {"rowIndex": 0, "columnIndex": 0},
                        "rowSpan": row_count,
                        "columnSpan": col_count,
                    },
                    "borderPosition": position,
                    "tableBorderProperties": {
                        "weight": weight,
                        "dashStyle": dash_style,
                        "tableBorderFill": {
                            "solidFill": {"color": {"rgbColor": rgb_color}}
                        },
                    },
                    "fields": "weight,dashStyle,tableBorderFill.solidFill.color",
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
        Apply alignment to table cells.
        """
        if (
            "cell-align" not in element.directives
            and "valign" not in element.directives
        ):
            return

        align_value = element.directives.get("cell-align") or element.directives.get(
            "valign"
        )

        if not isinstance(align_value, str):
            return

        v_alignment_map = {"top": "TOP", "middle": "MIDDLE", "bottom": "BOTTOM"}

        api_alignment = v_alignment_map.get(align_value.lower())
        if not api_alignment:
            logger.warning(
                f"Unsupported vertical alignment value for table cell: {align_value}. "
                f"Supported values are: {', '.join(v_alignment_map.keys())}"
            )
            return

        row_start, row_span, col_start, col_span = 0, row_count, 0, col_count
        if "cell-range" in element.directives:
            pass

        cell_align_request = {
            "updateTableCellProperties": {
                "objectId": element.object_id,
                "tableRange": {
                    "location": {"rowIndex": row_start, "columnIndex": col_start},
                    "rowSpan": row_span,
                    "columnSpan": col_span,
                },
                "tableCellProperties": {"contentAlignment": api_alignment},
                "fields": "contentAlignment",
            }
        }
        requests.append(cell_align_request)
        logger.debug(
            f"Applied vertical alignment '{api_alignment}' to cells in table {element.object_id}"
        )

    def _apply_cell_background_colors(
        self,
        element: TableElement,
        requests: list[dict],
        row_count: int,
        col_count: int,
    ) -> None:
        if "cell-background" not in element.directives:
            return
        bg_value = element.directives["cell-background"]
        color = None

        theme_colors = [
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
        ]
        named_colors_map = {
            "black": {"red": 0, "green": 0, "blue": 0},
            "white": {"red": 1, "green": 1, "blue": 1},
        }

        if isinstance(bg_value, str):
            if bg_value.startswith("#"):
                try:
                    color = {"rgbColor": self._hex_to_rgb(bg_value)}
                except ValueError:
                    return
            elif bg_value.upper() in theme_colors:
                color = {"themeColor": bg_value.upper()}
            elif bg_value.lower() in named_colors_map:
                color = {"rgbColor": named_colors_map[bg_value.lower()]}
            else:
                return
        else:
            return

        fields = "tableCellBackgroundFill.solidFill.color"

        row_start, row_span, col_start, col_span = 0, row_count, 0, col_count
        if "cell-range" in element.directives:
            pass

        bg_request = {
            "updateTableCellProperties": {
                "objectId": element.object_id,
                "tableRange": {
                    "location": {"rowIndex": row_start, "columnIndex": col_start},
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
