import pytest
from markdowndeck.api.request_builders.table_builder import TableRequestBuilder
from markdowndeck.models import ElementType, TableElement


@pytest.fixture
def builder() -> TableRequestBuilder:
    return TableRequestBuilder()


class TestTableRequestBuilderStyling:
    def test_generate_table_with_border_directive_simple(
        self, builder: TableRequestBuilder
    ):
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1"],
            rows=[["C1"]],
            object_id="table_border_simple",
            directives={"border": "1pt solid #FF0000"},
        )
        requests = builder.generate_table_element_requests(element, "slide1")

        assert (
            len(requests) >= 6
        ), "Expected requests for table creation, header/cell text, styling, and border"

        border_req = next(
            (r for r in requests if "updateTableBorderProperties" in r), None
        )
        assert border_req is not None
        props = border_req["updateTableBorderProperties"]["tableBorderProperties"]
        assert props["weight"]["magnitude"] == 1.0
        assert props["dashStyle"] == "SOLID"
        assert props["tableBorderFill"]["solidFill"]["color"]["rgbColor"] == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }

        # Check that the fields string is correct for the API
        fields_str = border_req["updateTableBorderProperties"]["fields"]
        assert "weight" in fields_str.split(",")
        assert "dashStyle" in fields_str.split(",")
        assert "tableBorderFill.solidFill.color" in fields_str
        assert border_req["updateTableBorderProperties"]["borderPosition"] == "ALL"

    def test_generate_table_with_border_directive_specific_position(
        self, builder: TableRequestBuilder
    ):
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1"],
            rows=[["C1"]],
            object_id="table_border_outer",
            directives={"border": "2pt dashed blue", "border-position": "OUTER"},
        )
        requests = builder.generate_table_element_requests(element, "slide1")
        border_req = next(
            (r for r in requests if "updateTableBorderProperties" in r), None
        )
        assert border_req is not None
        props = border_req["updateTableBorderProperties"]["tableBorderProperties"]
        assert props["weight"]["magnitude"] == 2.0
        assert props["dashStyle"] == "DASH"
        assert props["tableBorderFill"]["solidFill"]["color"]["rgbColor"] == {
            "red": 0.0,
            "green": 0.0,
            "blue": 1.0,
        }
        assert border_req["updateTableBorderProperties"]["borderPosition"] == "OUTER"

    def test_generate_table_with_cell_vertical_alignment_directive(
        self, builder: TableRequestBuilder
    ):
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H"],
            rows=[["C"]],
            object_id="table_cell_valign",
            directives={"cell-align": "middle"},  # Vertical alignment
        )
        requests = builder.generate_table_element_requests(element, "slide1")

        valign_req = next(
            (
                r
                for r in requests
                if "updateTableCellProperties" in r
                and "contentAlignment"
                in r["updateTableCellProperties"]["tableCellProperties"]
            ),
            None,
        )
        assert valign_req is not None, "updateTableCellProperties request not found"
        props = valign_req["updateTableCellProperties"]["tableCellProperties"]
        assert props["contentAlignment"] == "MIDDLE"
        assert valign_req["updateTableCellProperties"]["fields"] == "contentAlignment"

    def test_generate_table_with_cell_background_directive(
        self, builder: TableRequestBuilder
    ):
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H"],
            rows=[["C"]],
            object_id="table_cell_bg",
            directives={"cell-background": "#ABCDEF"},
        )
        requests = builder.generate_table_element_requests(element, "slide1")

        bg_req = next(
            (
                r
                for r in requests
                if "updateTableCellProperties" in r
                and "tableCellBackgroundFill"
                in r["updateTableCellProperties"]["tableCellProperties"]
            ),
            None,
        )
        assert bg_req is not None
        props = bg_req["updateTableCellProperties"]["tableCellProperties"][
            "tableCellBackgroundFill"
        ]["solidFill"]["color"]
        assert "rgbColor" in props
        rgb = props["rgbColor"]
        assert "red" in rgb
        assert "green" in rgb
        assert "blue" in rgb

        # Correct field path for cell background
        assert (
            bg_req["updateTableCellProperties"]["fields"]
            == "tableCellBackgroundFill.solidFill.color"
        )

    def test_generate_table_with_cell_range_for_directives(
        self, builder: TableRequestBuilder
    ):
        element = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2", "H3"],
            rows=[["R1C1", "R1C2", "R1C3"], ["R2C1", "R2C2", "R2C3"]],
            object_id="table_cell_range",
            directives={
                "cell-background": "#111111",
                "cell-range": "1,1:2,2",  # From row index 1 to 2, col index 1 to 2
            },
        )
        requests = builder.generate_table_element_requests(element, "slide1")

        # Find the background request that applies to the specified cell range
        # (not the header background requests)
        bg_req = next(
            (
                r
                for r in requests
                if "updateTableCellProperties" in r
                and "tableCellBackgroundFill"
                in r["updateTableCellProperties"]["tableCellProperties"]
                and r["updateTableCellProperties"]["tableRange"]["location"]["rowIndex"]
                == 1
                and r["updateTableCellProperties"]["tableRange"]["location"][
                    "columnIndex"
                ]
                == 1
            ),
            None,
        )
        assert (
            bg_req is not None
        ), "Should find background request for cell range 1,1:2,2"
        table_range = bg_req["updateTableCellProperties"]["tableRange"]

        assert table_range["location"]["rowIndex"] == 1
        assert table_range["location"]["columnIndex"] == 1
        assert table_range["rowSpan"] == 2  # (2 - 1 + 1)
        assert table_range["columnSpan"] == 2  # (2 - 1 + 1)
