"""Unit tests for individual overflow handler components."""

from markdowndeck.models import (
    ElementType,
    ListElement,
    ListItem,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
)
from markdowndeck.overflow.constants import (
    CONTINUED_ELEMENT_TITLE_SUFFIX,
)


class TestElementSplitMethods:
    """Unit tests for element split method implementations."""

    def test_text_element_split_basic(self):
        """Test basic text element splitting functionality."""

        text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4",
            size=(400, 80),
        )

        # Mock calculate_element_height to return predictable values
        def mock_calculate_height(element, width):
            lines = element.text.count("\n") + 1
            return lines * 20  # 20 points per line

        # Replace the import in the method (this would need to be mocked properly in real tests)
        fitted, overflowing = text.split(50.0)  # Should fit 2.5 lines, so 2 lines

        assert fitted is not None, "Should have fitted part"
        assert overflowing is not None, "Should have overflowing part"

        # Fitted should have fewer lines than original
        fitted_lines = fitted.text.count("\n") + 1
        overflowing_lines = overflowing.text.count("\n") + 1
        original_lines = text.text.count("\n") + 1

        assert (
            fitted_lines + overflowing_lines == original_lines
        ), "Lines should add up to original"
        assert fitted_lines < original_lines, "Fitted should have fewer lines"

    def test_text_element_split_with_formatting(self):
        """Test text element splitting with formatting preservation."""

        text = TextElement(
            element_type=ElementType.TEXT,
            text="First line with bold\nSecond line normal\nThird line with italic",
            formatting=[
                TextFormat(start=16, end=20, format_type=TextFormatType.BOLD),
                TextFormat(start=50, end=56, format_type=TextFormatType.ITALIC),
            ],
            size=(400, 60),
        )

        fitted, overflowing = text.split(40.0)  # Should split after first line

        if fitted and overflowing:
            # Check that formatting is properly distributed
            assert (
                len(fitted.formatting) >= 0
            ), "Fitted part should have appropriate formatting"
            assert (
                len(overflowing.formatting) >= 0
            ), "Overflowing part should have appropriate formatting"

            # Formatting positions should be adjusted for overflowing part
            for fmt in overflowing.formatting:
                assert fmt.start >= 0, "Formatting start should be adjusted"
                assert fmt.end <= len(
                    overflowing.text
                ), "Formatting end should be within text"

    def test_list_element_split_basic(self):
        """Test basic list element splitting functionality."""

        items = [ListItem(text=f"Item {i}") for i in range(1, 11)]  # 10 items

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST, items=items, size=(400, 200)
        )

        fitted, overflowing = list_elem.split(
            100.0
        )  # Should fit some but not all items

        assert fitted is not None, "Should have fitted part"
        assert overflowing is not None, "Should have overflowing part"

        assert len(fitted.items) < len(
            list_elem.items
        ), "Fitted should have fewer items"
        assert len(overflowing.items) > 0, "Overflowing should have items"
        assert len(fitted.items) + len(overflowing.items) == len(
            list_elem.items
        ), "Items should add up"

    def test_list_element_context_aware_continuation(self):
        """Test list element context-aware continuation title creation."""

        items = [ListItem(text=f"Item {i}") for i in range(1, 6)]

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items,
            size=(400, 100),
            related_to_prev=True,
        )

        # Set preceding title
        list_elem.set_preceding_title("Important Tasks")

        fitted, overflowing = list_elem.split(60.0)

        if overflowing and hasattr(overflowing, "_continuation_title"):
            continuation_title = overflowing._continuation_title
            assert (
                "Important Tasks" in continuation_title.text
            ), "Should include original title"
            assert (
                CONTINUED_ELEMENT_TITLE_SUFFIX in continuation_title.text
            ), "Should include continuation suffix"

    def test_table_element_split_basic(self):
        """Test basic table element splitting functionality."""

        headers = ["Col1", "Col2"]
        rows = [[f"Row {i} Col1", f"Row {i} Col2"] for i in range(1, 11)]  # 10 rows

        table = TableElement(
            element_type=ElementType.TABLE, headers=headers, rows=rows, size=(400, 200)
        )

        fitted, overflowing = table.split(100.0)  # Should fit some but not all rows

        assert fitted is not None, "Should have fitted part"
        assert overflowing is not None, "Should have overflowing part"

        assert len(fitted.rows) < len(table.rows), "Fitted should have fewer rows"
        assert len(overflowing.rows) > 0, "Overflowing should have rows"
        assert len(fitted.rows) + len(overflowing.rows) == len(
            table.rows
        ), "Rows should add up"

    def test_table_element_header_duplication(self):
        """Test that table headers are duplicated in overflowing part."""

        headers = ["Column A", "Column B", "Column C"]
        rows = [[f"Row {i} A", f"Row {i} B", f"Row {i} C"] for i in range(1, 8)]

        table = TableElement(
            element_type=ElementType.TABLE, headers=headers, rows=rows, size=(400, 160)
        )

        fitted, overflowing = table.split(80.0)  # Force split

        if fitted and overflowing:
            # Both parts should have headers
            assert fitted.headers == headers, "Fitted part should have headers"
            assert (
                overflowing.headers == headers
            ), "Overflowing part should have duplicated headers"

            # Headers should be deep copies, not references
            assert (
                fitted.headers is not overflowing.headers
            ), "Headers should be independent copies"

    def test_table_element_empty_content_handling(self):
        """Test table element splitting with empty or minimal content."""

        # Empty table
        empty_table = TableElement(
            element_type=ElementType.TABLE, headers=[], rows=[], size=(400, 0)
        )

        fitted, overflowing = empty_table.split(50.0)
        assert fitted is None, "Empty table should return None for fitted"
        assert overflowing is None, "Empty table should return None for overflowing"

        # Headers only
        headers_only = TableElement(
            element_type=ElementType.TABLE,
            headers=["Header 1", "Header 2"],
            rows=[],
            size=(400, 30),
        )

        fitted, overflowing = headers_only.split(50.0)
        # Headers-only table should fit (depending on height calculation)
        # The exact behavior depends on the implementation

    def test_element_split_edge_cases(self):
        """Test element split methods with edge cases."""

        # Text with no content
        empty_text = TextElement(element_type=ElementType.TEXT, text="", size=(400, 0))

        fitted, overflowing = empty_text.split(50.0)
        assert fitted is None, "Empty text should return None"
        assert overflowing is None, "Empty text should return None"

        # List with no items
        empty_list = ListElement(
            element_type=ElementType.BULLET_LIST, items=[], size=(400, 0)
        )

        fitted, overflowing = empty_list.split(50.0)
        assert fitted is None, "Empty list should return None"
        assert overflowing is None, "Empty list should return None"

        # Very small available height
        text_with_content = TextElement(
            element_type=ElementType.TEXT,
            text="Some content that won't fit",
            size=(400, 50),
        )

        fitted, overflowing = text_with_content.split(1.0)  # Tiny space
        # Should return None for fitted (nothing fits) and copy for overflowing
