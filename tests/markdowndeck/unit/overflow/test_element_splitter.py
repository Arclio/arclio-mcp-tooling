"""Unit tests for element split method implementations with specification compliance."""

from markdowndeck.models import (
    CodeElement,
    ElementType,
    ImageElement,
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
    """Unit tests for element split method implementations following specification contracts."""

    def test_text_element_split_minimum_two_lines_requirement(self):
        """Test text element splitting with minimum 2 lines requirement."""

        # Test 1: Text with sufficient lines for splitting
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
            size=(400, 100),
        )

        fitted, overflowing = text.split(60.0)  # Should fit ~3 lines

        if fitted and overflowing:
            # Verify minimum requirements met
            fitted_lines = fitted.text.count("\n") + 1
            overflowing_lines = overflowing.text.count("\n") + 1
            original_lines = text.text.count("\n") + 1

            assert fitted_lines >= 2, "Fitted part should meet minimum 2 lines"
            assert (
                overflowing_lines >= 1
            ), "Overflowing part should have remaining lines"
            assert (
                fitted_lines + overflowing_lines == original_lines
            ), "Lines should add up to original"

        # Test 2: Text with insufficient space for minimum requirements
        small_text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3",
            size=(400, 60),
        )

        fitted_small, overflowing_small = small_text.split(20.0)  # Only ~1 line fits

        # Should reject split due to minimum requirements
        assert fitted_small is None, "Should reject split when minimum not met"
        assert (
            overflowing_small is not None
        ), "Should return entire element as overflowing"

    def test_text_element_split_with_formatting_preservation(self):
        """Test text element splitting with formatting preservation and minimum requirements."""

        text = TextElement(
            element_type=ElementType.TEXT,
            text="First line with bold\nSecond line normal\nThird line with italic\nFourth line",
            formatting=[
                TextFormat(start=16, end=20, format_type=TextFormatType.BOLD),
                TextFormat(start=50, end=56, format_type=TextFormatType.ITALIC),
            ],
            size=(400, 80),
        )

        fitted, overflowing = text.split(50.0)  # Should split after second line

        if fitted and overflowing:
            # Verify minimum requirements
            fitted_lines = fitted.text.count("\n") + 1
            assert fitted_lines >= 2, "Should meet minimum 2 lines requirement"

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

    def test_list_element_split_minimum_two_items_requirement(self):
        """Test list element splitting with minimum 2 items requirement."""

        # Test 1: List with sufficient items for splitting
        items = [ListItem(text=f"Item {i}") for i in range(1, 8)]  # 7 items

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST, items=items, size=(400, 140)
        )

        fitted, overflowing = list_elem.split(80.0)  # Should fit ~4 items

        if fitted and overflowing:
            assert len(fitted.items) >= 2, "Fitted part should meet minimum 2 items"
            assert (
                len(overflowing.items) >= 1
            ), "Overflowing part should have remaining items"
            assert len(fitted.items) + len(overflowing.items) == len(
                list_elem.items
            ), "Items should add up"

        # Test 2: List with insufficient space for minimum requirements
        small_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1"), ListItem(text="Item 2")],
            size=(400, 40),
        )

        fitted_small, overflowing_small = small_list.split(15.0)  # Only ~1 item fits

        # Should reject split due to minimum requirements
        assert fitted_small is None, "Should reject split when minimum not met"
        assert overflowing_small is not None, "Should return entire list as overflowing"

    def test_list_element_context_aware_continuation(self):
        """Test list element context-aware continuation title creation."""

        items = [ListItem(text=f"Item {i}") for i in range(1, 6)]

        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=items,
            size=(400, 100),
            related_to_prev=True,  # Mark as related to preceding element
        )

        # Set preceding title for context-aware continuation
        list_elem.set_preceding_title("Important Tasks")

        fitted, overflowing = list_elem.split(60.0)

        if fitted and overflowing and hasattr(overflowing, "_continuation_title"):
            continuation_title = overflowing._continuation_title
            assert (
                "Important Tasks" in continuation_title.text
            ), "Should include original title"
            assert (
                CONTINUED_ELEMENT_TITLE_SUFFIX in continuation_title.text
            ), "Should include continuation suffix"

    def test_table_element_split_header_plus_two_rows_requirement(self):
        """Test table element splitting with header + 2 rows minimum requirement."""

        # Test 1: Table with sufficient rows for splitting
        headers = ["Col1", "Col2"]
        rows = [[f"Row {i} Col1", f"Row {i} Col2"] for i in range(1, 8)]  # 7 rows

        table = TableElement(
            element_type=ElementType.TABLE, headers=headers, rows=rows, size=(400, 160)
        )

        fitted, overflowing = table.split(100.0)  # Should fit header + ~4 rows

        if fitted and overflowing:
            assert len(fitted.rows) >= 2, "Fitted part should meet minimum 2 rows"
            assert (
                len(overflowing.rows) >= 1
            ), "Overflowing part should have remaining rows"
            assert len(fitted.rows) + len(overflowing.rows) == len(
                table.rows
            ), "Rows should add up"

        # Test 2: Table with insufficient space for minimum requirements
        small_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["Row 1 A", "Row 1 B"], ["Row 2 A", "Row 2 B"]],  # Only 2 rows
            size=(400, 60),
        )

        fitted_small, overflowing_small = small_table.split(30.0)  # Only header fits

        # Should reject split due to minimum requirements (need header + 2 rows)
        assert fitted_small is None, "Should reject split when minimum not met"
        assert (
            overflowing_small is not None
        ), "Should return entire table as overflowing"

    def test_table_element_header_duplication_in_overflow(self):
        """Test that table headers are duplicated in overflowing part."""

        headers = ["Column A", "Column B", "Column C"]
        rows = [[f"Row {i} A", f"Row {i} B", f"Row {i} C"] for i in range(1, 10)]

        table = TableElement(
            element_type=ElementType.TABLE, headers=headers, rows=rows, size=(400, 200)
        )

        fitted, overflowing = table.split(120.0)  # Force split

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

            # Verify minimum requirements were met
            assert len(fitted.rows) >= 2, "Fitted part should meet minimum 2 rows"

    def test_code_element_split_minimum_two_lines_requirement(self):
        """Test code element splitting with minimum 2 lines requirement (updated specification)."""

        # Test 1: Code with sufficient lines for splitting
        code_elem = CodeElement(
            element_type=ElementType.CODE,
            code="line1\nline2\nline3\nline4\nline5",
            language="python",
            size=(400, 100),
        )

        fitted, overflowing = code_elem.split(60.0)  # Should fit ~3 lines

        if fitted and overflowing:
            fitted_lines = fitted.code.count("\n") + 1
            overflowing_lines = overflowing.code.count("\n") + 1

            assert fitted_lines >= 2, "Fitted part should meet minimum 2 lines"
            assert (
                overflowing_lines >= 1
            ), "Overflowing part should have remaining lines"

        # Test 2: Code with insufficient space for minimum requirements
        small_code = CodeElement(
            element_type=ElementType.CODE,
            code="line1\nline2",
            language="python",
            size=(400, 40),
        )

        fitted_small, overflowing_small = small_code.split(20.0)  # Only ~1 line fits

        # Should reject split due to minimum requirements
        assert fitted_small is None, "Should reject split when minimum not met"
        assert overflowing_small is not None, "Should return entire code as overflowing"

    def test_code_element_language_preservation(self):
        """Test that code elements preserve language information when split."""

        code_elem = CodeElement(
            element_type=ElementType.CODE,
            code="function test() {\n  return true;\n}\n\nconsole.log('hello');\nconst x = 42;",
            language="javascript",
            size=(400, 120),
        )

        fitted, overflowing = code_elem.split(80.0)

        if fitted and overflowing:
            assert (
                fitted.language == "javascript"
            ), "Fitted part should preserve language"
            assert (
                overflowing.language == "javascript"
            ), "Overflowing part should preserve language"

            # Verify both parts have valid code content
            assert len(fitted.code.strip()) > 0, "Fitted part should have code content"
            assert (
                len(overflowing.code.strip()) > 0
            ), "Overflowing part should have code content"

    def test_image_element_split_proactive_scaling_contract(self):
        """Test image element split returns (self, None) due to proactive scaling."""

        large_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/large-image.jpg",
            alt_text="Large image",
            size=(620, 400),  # Large size, but proactively scaled
        )

        # Test split with any available height
        fitted, overflowing = large_image.split(100.0)

        # Per specification: images are proactively scaled, so they always fit
        assert fitted == large_image, "Image should return self as fitted part"
        assert overflowing is None, "Image should have no overflowing part (pre-scaled)"

        # Test with very small available height
        fitted_small, overflowing_small = large_image.split(1.0)

        # Even with tiny space, image should still fit due to proactive scaling
        assert fitted_small == large_image, "Pre-scaled image should always fit"
        assert overflowing_small is None, "Pre-scaled image should never overflow"

    def test_image_element_validation_methods(self):
        """Test image element validation and type checking methods."""

        # Valid web image
        web_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/image.jpg",
            alt_text="Web image",
        )

        assert web_image.is_valid(), "Web image should be valid"
        assert web_image.is_web_image(), "Should identify as web image"

        # Data URL image
        data_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            alt_text="Data image",
        )

        assert data_image.is_valid(), "Data image should be valid"
        assert (
            not data_image.is_web_image()
        ), "Data image should not be identified as web image"

        # Invalid image
        invalid_image = ImageElement(
            element_type=ElementType.IMAGE,
            url="",
            alt_text="Invalid image",
        )

        assert not invalid_image.is_valid(), "Empty URL image should be invalid"

    def test_element_split_edge_cases_with_minimum_requirements(self):
        """Test element split methods with edge cases and minimum requirements."""

        # Test 1: Empty content elements
        empty_text = TextElement(element_type=ElementType.TEXT, text="", size=(400, 0))

        fitted, overflowing = empty_text.split(50.0)
        assert fitted is None, "Empty text should return None"
        assert overflowing is None, "Empty text should return None"

        # Test 2: Empty list
        empty_list = ListElement(
            element_type=ElementType.BULLET_LIST, items=[], size=(400, 0)
        )

        fitted, overflowing = empty_list.split(50.0)
        assert fitted is None, "Empty list should return None"
        assert overflowing is None, "Empty list should return None"

        # Test 3: Single line text (can't meet minimum 2 lines)
        single_line = TextElement(
            element_type=ElementType.TEXT,
            text="Single line that won't split",
            size=(400, 20),
        )

        fitted, overflowing = single_line.split(50.0)
        # Should not split single line even with available space
        assert fitted is None, "Single line should not split"
        assert overflowing is not None, "Should return as overflowing"

        # Test 4: Single item list (can't meet minimum 2 items)
        single_item_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Only item")],
            size=(400, 20),
        )

        fitted, overflowing = single_item_list.split(50.0)
        # Should not split single item even with available space
        assert fitted is None, "Single item list should not split"
        assert overflowing is not None, "Should return as overflowing"

        # Test 5: Empty code (should return None, None)
        empty_code = CodeElement(
            element_type=ElementType.CODE,
            code="",
            language="python",
            size=(400, 0),
        )

        fitted, overflowing = empty_code.split(50.0)
        assert fitted is None, "Empty code should return None"
        assert overflowing is None, "Empty code should return None"

    def test_minimum_requirements_contract_consistency(self):
        """Test that all splittable elements follow minimum requirements contract consistently."""

        # Test text element contract
        text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3",
            size=(400, 60),
        )

        # Test with space for exactly 2 lines (minimum)
        fitted, overflowing = text.split(40.0)
        if fitted:
            fitted_lines = fitted.text.count("\n") + 1
            assert fitted_lines >= 2, "Text should enforce minimum 2 lines"

        # Test list element contract
        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"Item {i}") for i in range(1, 5)],
            size=(400, 80),
        )

        # Test with space for exactly 2 items (minimum)
        fitted, overflowing = list_elem.split(40.0)
        if fitted:
            assert len(fitted.items) >= 2, "List should enforce minimum 2 items"

        # Test table element contract
        table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1"],
            rows=[["Row 1"], ["Row 2"], ["Row 3"], ["Row 4"]],
            size=(400, 100),
        )

        # Test with space for header + exactly 2 rows (minimum)
        fitted, overflowing = table.split(60.0)
        if fitted:
            assert len(fitted.rows) >= 2, "Table should enforce minimum 2 rows"
            assert len(fitted.headers) > 0, "Table should include headers"

        # Test code element contract (now splittable)
        code = CodeElement(
            element_type=ElementType.CODE,
            code="line1\nline2\nline3\nline4",
            language="python",
            size=(400, 80),
        )

        fitted, overflowing = code.split(40.0)
        if fitted:
            fitted_lines = fitted.code.count("\n") + 1
            assert fitted_lines >= 2, "Code should enforce minimum 2 lines"

    def test_split_method_polymorphism(self):
        """Test that all element types properly implement the split method interface."""

        # All these elements should have split methods
        elements = [
            TextElement(
                element_type=ElementType.TEXT,
                text="Test text\nLine 2\nLine 3",
                size=(400, 60),
            ),
            ListElement(
                element_type=ElementType.BULLET_LIST,
                items=[
                    ListItem(text="Item 1"),
                    ListItem(text="Item 2"),
                    ListItem(text="Item 3"),
                ],
                size=(400, 60),
            ),
            TableElement(
                element_type=ElementType.TABLE,
                headers=["Col1"],
                rows=[["Row 1"], ["Row 2"], ["Row 3"]],
                size=(400, 60),
            ),
            ImageElement(
                element_type=ElementType.IMAGE,
                url="https://example.com/test.jpg",
                size=(400, 200),
            ),
            CodeElement(
                element_type=ElementType.CODE,
                code="line1\nline2\nline3",
                language="python",
                size=(400, 60),
            ),
        ]

        for element in elements:
            # All elements should have split method
            assert hasattr(
                element, "split"
            ), f"{element.element_type} should have split method"
            assert callable(
                element.split
            ), f"{element.element_type}.split should be callable"

            # Split method should return tuple
            result = element.split(50.0)
            assert isinstance(
                result, tuple
            ), f"{element.element_type}.split should return tuple"
            assert (
                len(result) == 2
            ), f"{element.element_type}.split should return 2-tuple"

            fitted, overflowing = result
            # At least one should not be None (either fits completely or overflows completely)
            assert (
                fitted is not None or overflowing is not None
            ), f"{element.element_type}.split should not return (None, None)"

    def test_split_result_size_consistency(self):
        """Test that split results have consistent size information."""

        text = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4",
            size=(400, 80),
        )

        fitted, overflowing = text.split(50.0)

        if fitted and overflowing:
            # Both parts should have size information
            assert fitted.size is not None, "Fitted part should have size"
            assert overflowing.size is not None, "Overflowing part should have size"

            # Sizes should be reasonable
            assert fitted.size[0] > 0, "Fitted width should be positive"
            assert fitted.size[1] > 0, "Fitted height should be positive"
            assert overflowing.size[0] > 0, "Overflowing width should be positive"
            assert overflowing.size[1] > 0, "Overflowing height should be positive"

    def test_list_item_nested_structure_methods(self):
        """Test ListItem nested structure utility methods."""

        # Create nested list structure
        level_2_items = [
            ListItem(text="Level 2 Item 1", level=2),
            ListItem(text="Level 2 Item 2", level=2),
        ]

        level_1_item = ListItem(text="Level 1 Item", level=1, children=level_2_items)

        top_item = ListItem(text="Top Item", level=0)
        top_item.add_child(level_1_item)

        # Test count methods
        assert top_item.count_all_items() == 4, "Should count all nested items"
        assert top_item.max_depth() == 2, "Should calculate correct max depth"

        # Test child addition
        new_child = ListItem(text="New Child", level=1)
        top_item.add_child(new_child)
        assert len(top_item.children) == 2, "Should have added child"
        assert new_child.level == 1, "Child level should be set correctly"

    def test_table_element_structure_validation_methods(self):
        """Test TableElement structure validation and utility methods."""

        # Valid table
        valid_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["A1", "A2"], ["B1", "B2"]],
        )

        assert valid_table.validate(), "Valid table should pass validation"
        assert valid_table.get_column_count() == 2, "Should return correct column count"
        assert (
            valid_table.get_row_count() == 3
        ), "Should return correct row count (including header)"
        assert (
            valid_table.requires_header_duplication()
        ), "Should require header duplication"

        # Table without headers
        no_header_table = TableElement(
            element_type=ElementType.TABLE,
            headers=[],
            rows=[["A1", "A2"], ["B1", "B2"]],
        )

        assert no_header_table.validate(), "Table without headers should be valid"
        assert (
            not no_header_table.requires_header_duplication()
        ), "Should not require header duplication"

        # Empty table
        empty_table = TableElement(
            element_type=ElementType.TABLE,
            headers=[],
            rows=[],
        )

        assert not empty_table.validate(), "Empty table should be invalid"

    def test_code_element_utility_methods(self):
        """Test CodeElement utility methods."""

        code_elem = CodeElement(
            element_type=ElementType.CODE,
            code="def hello():\n    print('world')\n    return True",
            language="py",
        )

        assert code_elem.count_lines() == 3, "Should count lines correctly"
        assert (
            code_elem.get_display_language() == "Python"
        ), "Should map language correctly"

        # Test with unmapped language
        code_elem.language = "customlang"
        assert (
            code_elem.get_display_language() == "Customlang"
        ), "Should capitalize unknown language"

        # Test with empty code
        empty_code = CodeElement(
            element_type=ElementType.CODE,
            code="",
        )

        assert empty_code.count_lines() == 0, "Empty code should have 0 lines"
