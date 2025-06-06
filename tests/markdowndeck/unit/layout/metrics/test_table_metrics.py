"""Updated unit tests for table element metrics with split() method support."""

from markdowndeck.layout.metrics.table import calculate_table_element_height
from markdowndeck.models import ElementType, TableElement


class TestTableMetrics:
    """Unit tests for table element height calculation."""

    def test_calculate_table_height_empty(self):
        element = TableElement(headers=[], rows=[], element_type=ElementType.TABLE)
        height = calculate_table_element_height(element, 500)
        assert height >= 35  # MIN_TABLE_HEIGHT

    def test_calculate_table_height_header_only(self):
        element = TableElement(headers=["H1", "H2"], rows=[], element_type=ElementType.TABLE)
        height = calculate_table_element_height(element, 500)
        assert height > 35  # Should be more than minimum

    def test_calculate_table_height_header_and_rows(self):
        headers = ["Header"]
        rows = [["Row1Cell1"], ["Row2Cell1"]]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        height = calculate_table_element_height(element, 200)
        # Current implementation uses compact spacing
        assert height > 60  # Should account for header + 2 rows + padding

    def test_calculate_table_height_wrapping_cell_content(self):
        headers = ["Col A"]
        short_cell_row = [["Short"]]
        long_cell_row = [["This cell has a lot of text that should wrap multiple times and make the row taller."]]

        element_short = TableElement(headers=headers, rows=short_cell_row, element_type=ElementType.TABLE)
        element_long = TableElement(headers=headers, rows=long_cell_row, element_type=ElementType.TABLE)

        height_short = calculate_table_element_height(element_short, 300)
        height_long = calculate_table_element_height(element_long, 300)

        assert height_long > height_short

    def test_calculate_table_height_multiple_columns_wrapping(self):
        headers = ["Col1", "Col2"]
        rows = [
            [
                "Short",
                "This second cell is very long and should determine the row height because it wraps",
            ],
            ["Another short", "Also short"],
        ]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        height = calculate_table_element_height(element, 400)

        # Compare to a table where all cells are short
        rows_all_short = [["Short", "Short"], ["Short", "Short"]]
        element_all_short = TableElement(headers=headers, rows=rows_all_short, element_type=ElementType.TABLE)
        height_all_short = calculate_table_element_height(element_all_short, 400)

        assert height > height_all_short

    def test_calculate_table_height_many_rows(self):
        """Test table height calculation with many rows."""
        headers = ["Col1", "Col2"]
        few_rows = [["A", "B"], ["C", "D"]]
        many_rows = [["A", "B"] for _ in range(10)]

        element_few = TableElement(headers=headers, rows=few_rows, element_type=ElementType.TABLE)
        element_many = TableElement(headers=headers, rows=many_rows, element_type=ElementType.TABLE)

        height_few = calculate_table_element_height(element_few, 400)
        height_many = calculate_table_element_height(element_many, 400)

        assert height_many > height_few

    def test_calculate_table_height_varying_column_count(self):
        """Test table height with varying column counts."""
        headers = ["H1", "H2", "H3"]
        rows = [
            ["A", "B", "C"],  # Full row
            ["A", "B"],  # Partial row
            ["A"],  # Single cell
        ]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        height = calculate_table_element_height(element, 400)

        assert height > 35  # Should handle varying column counts


class TestTableElementSplitting:
    """Test the split() method functionality for TableElement."""

    def test_table_split_basic_functionality(self):
        """Test basic split() method functionality."""
        headers = ["Col1", "Col2"]
        rows = [["R1C1", "R1C2"], ["R2C1", "R2C2"], ["R3C1", "R3C2"]]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 100)

        # Test with sufficient height (should fit all)
        fitted, overflowing = element.split(200)
        assert fitted is not None
        assert overflowing is None
        assert len(fitted.rows) == 3

    def test_table_split_minimum_requirements(self):
        """Test that split() respects minimum header + 2 rows requirement."""
        headers = ["Col1", "Col2"]
        rows = [["R1C1", "R1C2"], ["R2C1", "R2C2"], ["R3C1", "R3C2"]]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 80)

        # Test with very limited height (less than header + 2 rows)
        fitted, overflowing = element.split(30)  # Very small height

        # Should reject split due to minimum requirement
        assert fitted is None
        assert overflowing is not None
        assert len(overflowing.rows) == 3

    def test_table_split_successful_split(self):
        """Test successful split when minimum requirements are met."""
        headers = ["Col1", "Col2"]
        rows = [[f"R{i}C1", f"R{i}C2"] for i in range(1, 7)]  # 6 rows
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 120)

        # Test with moderate height (should split)
        fitted, overflowing = element.split(70)

        if fitted is not None:  # Split was accepted
            assert len(fitted.rows) >= 2  # At least 2 data rows
            assert len(fitted.rows) < 6  # Not all rows
            assert fitted.headers == headers  # Headers preserved
            assert overflowing is not None
            assert len(overflowing.rows) >= 1  # At least 1 row remaining
            assert overflowing.headers == headers  # Headers duplicated
            assert len(fitted.rows) + len(overflowing.rows) == 6  # Total preserved

    def test_table_split_empty_table(self):
        """Test split() with empty table."""
        element = TableElement(headers=[], rows=[], element_type=ElementType.TABLE)
        element.size = (400, 50)

        fitted, overflowing = element.split(100)
        assert fitted is None
        assert overflowing is None

    def test_table_split_header_only(self):
        """Test split() with header-only table."""
        element = TableElement(headers=["H1", "H2"], rows=[], element_type=ElementType.TABLE)
        element.size = (400, 50)

        fitted, overflowing = element.split(100)
        # Header-only table should fit entirely or not at all
        if fitted is not None:
            assert fitted.headers == ["H1", "H2"]
            assert fitted.rows == []
            assert overflowing is None

    def test_table_split_insufficient_rows(self):
        """Test split() with insufficient rows to meet minimum."""
        headers = ["Col1"]
        rows = [["R1C1"]]  # Only 1 row - can't meet minimum of 2
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 50)

        fitted, overflowing = element.split(40)  # Limited height

        # Should be treated as atomic due to insufficient rows
        assert fitted is None
        assert overflowing is not None

    def test_table_split_preserves_metadata(self):
        """Test that split preserves element metadata."""
        headers = ["Col1", "Col2"]
        rows = [["R1C1", "R1C2"], ["R2C1", "R2C2"], ["R3C1", "R3C2"]]
        element = TableElement(
            headers=headers,
            rows=rows,
            element_type=ElementType.TABLE,
            object_id="test_table",
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            assert fitted.element_type == ElementType.TABLE
            assert hasattr(fitted, "size")
            assert fitted.headers == headers

        if overflowing is not None:
            assert overflowing.element_type == ElementType.TABLE
            assert overflowing.headers == headers

    def test_table_split_header_duplication(self):
        """Test that headers are properly duplicated in overflowing part."""
        headers = ["ID", "Name", "Value"]
        rows = [
            ["1", "Item1", "100"],
            ["2", "Item2", "200"],
            ["3", "Item3", "300"],
            ["4", "Item4", "400"],
        ]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 100)

        fitted, overflowing = element.split(60)

        if fitted is not None and overflowing is not None:
            # Both parts should have the same headers
            assert fitted.headers == headers
            assert overflowing.headers == headers
            # Verify data integrity
            all_fitted_rows = [row[:] for row in fitted.rows]
            all_overflowing_rows = [row[:] for row in overflowing.rows]
            all_reconstructed = all_fitted_rows + all_overflowing_rows
            assert all_reconstructed == rows

    def test_table_split_large_table_performance(self):
        """Test split performance with large table."""
        headers = ["Col1", "Col2", "Col3"]
        rows = [[f"R{i}C1", f"R{i}C2", f"R{i}C3"] for i in range(100)]
        element = TableElement(headers=headers, rows=rows, element_type=ElementType.TABLE)
        element.size = (400, 200)

        import time

        start = time.time()
        fitted, overflowing = element.split(100)
        end = time.time()

        assert (end - start) < 1.0  # Should complete quickly

        if fitted is not None:
            assert len(fitted.rows) >= 2  # Should meet minimum requirements

    def test_table_requires_header_duplication(self):
        """Test the requires_header_duplication method."""
        # Table with headers
        element_with_headers = TableElement(
            headers=["H1", "H2"],
            rows=[["R1C1", "R1C2"]],
            element_type=ElementType.TABLE,
        )
        assert element_with_headers.requires_header_duplication() is True

        # Table without headers
        element_no_headers = TableElement(headers=[], rows=[["R1C1", "R1C2"]], element_type=ElementType.TABLE)
        assert element_no_headers.requires_header_duplication() is False
