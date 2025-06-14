from unittest.mock import patch

from markdowndeck.models import ElementType, TableElement


class TestTableElementSplit:
    """Unit tests for the TableElement's split method."""

    @patch("markdowndeck.layout.metrics.table.calculate_row_height")
    def test_split_preserves_headers_in_overflow(self, mock_calc_height):
        """
        Test Case: DATA-E-SPLIT-TABLE-03 (Custom ID)
        The overflowing part of a table with headers must also contain the headers.
        """
        mock_calc_height.side_effect = lambda data, width, is_header: (30 if is_header else 25)
        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["H1", "H2"],
            rows=[["R1", "R1"], ["R2", "R2"], ["R3", "R3"], ["R4", "R4"]],
            size=(400, 130),
        )
        fitted, overflow = table.split(available_height=85)  # Fits header + 2 rows
        assert fitted is not None
        assert len(fitted.rows) == 2
        assert overflow is not None
        assert len(overflow.rows) == 2
        assert overflow.headers == [
            "H1",
            "H2",
        ], "Headers must be duplicated in the overflow part."
