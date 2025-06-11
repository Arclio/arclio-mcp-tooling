from unittest.mock import patch

from markdowndeck.models import ElementType, TableElement


class TestTableElementSplit:
    def test_data_e_04_split_headers_only(self):
        """
        Test Case: DATA-E-04 (Headers Only)
        A table with only headers cannot be split.
        """
        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2"],
            rows=[],
            size=(400, 30),
        )
        fitted, overflow = table.split(available_height=15)
        assert fitted is None
        assert overflow is not None
        assert overflow.headers == ["H1", "H2"]

    def test_data_e_04_split_headers_plus_one_row(self):
        """
        Test Case: DATA-E-04 (Headers + 1 Row)
        Splitting a table with headers and one row should fail the minimum requirement.
        """
        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2"],
            rows=[["R1C1", "R1C2"]],
            size=(400, 60),
        )
        fitted, overflow = table.split(available_height=35)
        assert fitted is None
        assert overflow is not None
        assert len(overflow.rows) == 1

    @patch("markdowndeck.layout.metrics.table.calculate_row_height")
    def test_data_e_04_split_preserves_headers_in_overflow(self, mock_calc_height):
        """
        Test Case: DATA-E-04 (Header Preservation)
        The overflowing part of a table with headers must also contain the headers.
        """
        # Arrange
        mock_calc_height.side_effect = lambda data, width, is_header: (
            30 if is_header else 25
        )

        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2"],
            rows=[["R1", "R1"], ["R2", "R2"], ["R3", "R3"], ["R4", "R4"]],
            size=(400, 130),  # 30 for header + 4*25 for rows
        )

        # Act
        # available_height for header(30) + 2 rows (50) = 80
        fitted, overflow = table.split(available_height=85)

        # Assert
        assert fitted is not None, "Fitted part should exist."
        assert len(fitted.rows) == 2, "Fitted part should have 2 rows."

        assert overflow is not None, "Overflow part should exist."
        assert overflow.headers == [
            "H1",
            "H2",
        ], "Headers must be duplicated in the overflow part."
        assert len(overflow.rows) == 2, "Incorrect number of rows in overflow part."
        assert overflow.rows[0][0] == "R3", "First row of overflow part is incorrect."
