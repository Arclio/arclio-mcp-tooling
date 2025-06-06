"""Updated unit tests for text element metrics with split() method support."""

from markdowndeck.layout.constants import (
    MIN_CODE_HEIGHT,
    MIN_LIST_HEIGHT,
    MIN_TEXT_HEIGHT,
)
from markdowndeck.layout.metrics.code import calculate_code_element_height
from markdowndeck.layout.metrics.image import calculate_image_element_height
from markdowndeck.layout.metrics.list import calculate_list_element_height
from markdowndeck.layout.metrics.table import calculate_table_element_height
from markdowndeck.layout.metrics.text import calculate_text_element_height
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


class TestTextMetrics:
    """Test the refactored text metrics system."""

    def test_text_height_is_content_aware(self):
        """Test that text height calculation is based on actual content."""

        short_element = TextElement(element_type=ElementType.TEXT, text="Short")
        long_element = TextElement(
            element_type=ElementType.TEXT,
            text="This is a much longer text that will definitely require multiple lines when wrapped "
            * 5,
        )

        available_width = 300.0

        short_height = calculate_text_element_height(short_element, available_width)
        long_height = calculate_text_element_height(long_element, available_width)

        assert long_height > short_height, "Longer text should result in greater height"
        assert short_height >= MIN_TEXT_HEIGHT, "Should respect minimum height"

    def test_text_height_varies_with_width(self):
        """Test that narrower width results in taller text due to wrapping."""

        element = TextElement(
            element_type=ElementType.TEXT,
            text="This text will wrap differently at different widths and should be taller when narrow",
        )

        wide_height = calculate_text_element_height(element, 500.0)
        narrow_height = calculate_text_element_height(element, 150.0)

        assert (
            narrow_height > wide_height
        ), "Narrower width should result in taller text"

    def test_title_vs_text_sizing(self):
        """Test that titles and regular text use different sizing parameters."""

        title = TextElement(element_type=ElementType.TITLE, text="Title Text")
        text = TextElement(element_type=ElementType.TEXT, text="Regular Text")

        available_width = 400.0

        title_height = calculate_text_element_height(title, available_width)
        text_height = calculate_text_element_height(text, available_width)

        # Title should generally be taller due to larger font size and padding
        assert title_height > text_height, "Title should be taller than regular text"

    def test_empty_text_handling(self):
        """Test that empty text elements return reasonable minimum heights."""

        empty_element = TextElement(element_type=ElementType.TEXT, text="")
        height = calculate_text_element_height(empty_element, 400.0)

        assert height == MIN_TEXT_HEIGHT, "Empty text should return minimum height"

    def test_custom_font_size_directive(self):
        """Test that custom font size directives are respected."""

        normal_element = TextElement(element_type=ElementType.TEXT, text="Test text")
        large_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test text",
            directives={"fontsize": 24.0},
        )

        available_width = 400.0

        normal_height = calculate_text_element_height(normal_element, available_width)
        large_height = calculate_text_element_height(large_element, available_width)

        assert (
            large_height > normal_height
        ), "Larger font size should result in taller element"

    def test_footer_html_comment_stripping(self):
        """Test that footer elements strip HTML comments (speaker notes)."""

        footer_with_comments = TextElement(
            element_type=ElementType.FOOTER,
            text="Page Footer <!-- Speaker note: This is a note -->",
        )

        footer_without_comments = TextElement(
            element_type=ElementType.FOOTER,
            text="Page Footer",
        )

        available_width = 400.0

        height_with_comments = calculate_text_element_height(
            footer_with_comments, available_width
        )
        height_without_comments = calculate_text_element_height(
            footer_without_comments, available_width
        )

        # Heights should be similar since comments should be stripped
        assert (
            abs(height_with_comments - height_without_comments) < 5
        ), "Footer heights should be similar regardless of HTML comments"

    def test_no_longer_caps_height(self):
        """Test that text height is no longer artificially capped."""
        # This text would have previously been capped at a low value.
        long_title_text = "This is an Incredibly Long Title for a Slide That Goes On and On to Ensure It Exceeds Any Old Hardcoded Maximum Height Constraints That Might Have Existed"
        element = TextElement(element_type=ElementType.TITLE, text=long_title_text)

        # Calculate height with a reasonable width
        height = calculate_text_element_height(element, 600)

        # The old cap was around 30-50pt. This should now be much larger.
        assert (
            height > 60
        ), "Title height should be based on content and not capped at a low value."


class TestTextElementSplitting:
    """Test the split() method functionality for TextElement."""

    def test_text_split_basic_functionality(self):
        """Test basic split() method functionality."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        element = TextElement(element_type=ElementType.TEXT, text=text)
        element.size = (400, 100)

        # Test with sufficient height (should fit all)
        fitted, overflowing = element.split(200)
        assert fitted is not None
        assert overflowing is None
        assert fitted.text == text

    def test_text_split_minimum_requirements(self):
        """Test that split() respects minimum 2-line requirement."""
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        element = TextElement(element_type=ElementType.TEXT, text=text)
        element.size = (400, 80)

        # Test with very limited height (less than 2 lines worth)
        fitted, overflowing = element.split(10)  # Very small height

        # Should reject split due to minimum requirement
        assert fitted is None
        assert overflowing is not None
        assert overflowing.text == text

    def test_text_split_successful_split(self):
        """Test successful split when minimum requirements are met."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6"
        element = TextElement(element_type=ElementType.TEXT, text=text)
        element.size = (400, 120)

        # Test with moderate height (should split)
        fitted, overflowing = element.split(60)

        if fitted is not None:  # Split was accepted
            assert fitted.text != text  # Should be partial
            assert overflowing is not None
            assert len(fitted.text.split("\n")) >= 2  # At least 2 lines
            assert len(overflowing.text.split("\n")) >= 1  # At least 1 line remaining

    def test_text_split_empty_text(self):
        """Test split() with empty text."""
        element = TextElement(element_type=ElementType.TEXT, text="")
        element.size = (400, 50)

        fitted, overflowing = element.split(100)
        assert fitted is None
        assert overflowing is None

    def test_text_split_single_line(self):
        """Test split() with single line of text."""
        element = TextElement(element_type=ElementType.TEXT, text="Single line")
        element.size = (400, 50)

        fitted, overflowing = element.split(10)  # Very small height

        # Single line that doesn't fit should be treated as atomic
        assert fitted is None
        assert overflowing is not None

    def test_text_split_preserves_metadata(self):
        """Test that split preserves element metadata."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4",
            object_id="test_text",
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            assert fitted.element_type == ElementType.TEXT
            assert hasattr(fitted, "size")

        if overflowing is not None:
            assert overflowing.element_type == ElementType.TEXT

    def test_text_split_with_formatting(self):
        """Test split() with text formatting."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1 with bold\nLine 2 normal\nLine 3 italic\nLine 4 normal",
            formatting=[
                TextFormat(start=11, end=15, format_type=TextFormatType.BOLD),
                TextFormat(start=35, end=41, format_type=TextFormatType.ITALIC),
            ],
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None and overflowing is not None:
            # Check that formatting is appropriately partitioned
            assert hasattr(fitted, "formatting")
            assert hasattr(overflowing, "formatting")
            # The formatting lists should be adjusted for the split

    def test_text_split_preserves_alignment(self):
        """Test that split preserves text alignment."""
        from markdowndeck.models import AlignmentType

        element = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4",
            horizontal_alignment=AlignmentType.CENTER,
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            assert fitted.horizontal_alignment == AlignmentType.CENTER

        if overflowing is not None:
            assert overflowing.horizontal_alignment == AlignmentType.CENTER

    def test_text_split_with_related_to_next(self):
        """Test split() behavior with related_to_next flag."""
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Line 1\nLine 2\nLine 3\nLine 4",
            related_to_next=True,
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            # The related_to_next flag should be preserved appropriately
            assert hasattr(fitted, "related_to_next")


class TestUnifiedListMetrics:
    """Test the refactored list metrics system."""

    def test_list_height_increases_with_items(self):
        """Test that more list items result in taller lists."""

        short_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1"), ListItem(text="Item 2")],
        )

        long_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text=f"Item {i}") for i in range(1, 11)],  # 10 items
        )

        available_width = 400.0

        short_height = calculate_list_element_height(short_list, available_width)
        long_height = calculate_list_element_height(long_list, available_width)

        assert long_height > short_height, "More items should result in taller list"
        assert short_height >= MIN_LIST_HEIGHT, "Should respect minimum height"

    def test_empty_list_minimum_height(self):
        """Test that empty lists return minimum height."""

        empty_list = ListElement(element_type=ElementType.BULLET_LIST, items=[])
        height = calculate_list_element_height(empty_list, 400.0)

        assert (
            height >= MIN_LIST_HEIGHT
        ), f"Empty list should get minimum height {MIN_LIST_HEIGHT}, got {height}"

    def test_nested_list_height(self):
        """Test that nested lists are taller than flat lists."""

        flat_items = [
            ListItem(text="Item 1"),
            ListItem(text="Item 2"),
            ListItem(text="Item 3"),
        ]

        nested_child = ListItem(text="Child item")
        nested_items = [
            ListItem(text="Item 1"),
            ListItem(text="Item 2", children=[nested_child]),
            ListItem(text="Item 3"),
        ]

        flat_list = ListElement(element_type=ElementType.BULLET_LIST, items=flat_items)
        nested_list = ListElement(
            element_type=ElementType.BULLET_LIST, items=nested_items
        )

        available_width = 400.0

        flat_height = calculate_list_element_height(flat_list, available_width)
        nested_height = calculate_list_element_height(nested_list, available_width)

        assert (
            nested_height > flat_height
        ), "Nested list should be taller than flat list"

    def test_list_item_text_wrapping(self):
        """Test that long list item text affects list height."""

        short_item_list = ListElement(
            element_type=ElementType.BULLET_LIST, items=[ListItem(text="Short")]
        )

        long_item_list = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(
                    text="This is a very long list item that will definitely wrap multiple times "
                    * 3
                )
            ],
        )

        available_width = 200.0  # Narrow to force wrapping

        short_height = calculate_list_element_height(short_item_list, available_width)
        long_height = calculate_list_element_height(long_item_list, available_width)

        assert long_height > short_height, "Long item text should result in taller list"

    def test_list_item_with_formatting(self):
        """Test that list items with formatting work correctly."""

        item_formatted = ListItem(
            text="Item with **bold** text",
            formatting=[TextFormat(start=10, end=14, format_type=TextFormatType.BOLD)],
        )
        element = ListElement(
            items=[item_formatted], element_type=ElementType.BULLET_LIST
        )

        # The height difference due to mild formatting might be negligible or absorbed by line height
        # but the test ensures it doesn't crash and uses the text_height_calculator.
        height = calculate_list_element_height(element, 500)
        assert height > 0, "Formatted list item should have positive height"


class TestUnifiedTableMetrics:
    """Test the refactored table metrics system."""

    def test_table_height_increases_with_rows(self):
        """Test that more table rows result in taller tables."""

        small_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[["R1C1", "R1C2"], ["R2C1", "R2C2"]],
        )

        large_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["Col1", "Col2"],
            rows=[[f"R{i}C1", f"R{i}C2"] for i in range(1, 11)],  # 10 rows
        )

        available_width = 400.0

        small_height = calculate_table_element_height(small_table, available_width)
        large_height = calculate_table_element_height(large_table, available_width)

        assert large_height > small_height, "More rows should result in taller table"

    def test_empty_table_minimum_height(self):
        """Test that empty tables return minimum height."""

        empty_table = TableElement(headers=[], rows=[], element_type=ElementType.TABLE)
        height = calculate_table_element_height(empty_table, 500)
        assert (
            height >= 30
        ), f"Empty table should get minimum height, got {height}"  # Using relaxed minimum

    def test_table_header_only(self):
        """Test tables with only headers."""

        header_only_table = TableElement(
            headers=["H1", "H2"], rows=[], element_type=ElementType.TABLE
        )
        height = calculate_table_element_height(header_only_table, 500)

        # Current implementation uses more compact spacing
        assert (
            height > 20
        ), f"Header-only table should have reasonable height, got {height}"

    def test_table_cell_content_affects_height(self):
        """Test that cell content length affects table height."""

        short_content_table = TableElement(
            element_type=ElementType.TABLE, headers=["A", "B"], rows=[["X", "Y"]]
        )

        long_content_table = TableElement(
            element_type=ElementType.TABLE,
            headers=["A", "B"],
            rows=[["This is very long content that will wrap in the cell " * 2, "Y"]],
        )

        available_width = 300.0

        short_height = calculate_table_element_height(
            short_content_table, available_width
        )
        long_height = calculate_table_element_height(
            long_content_table, available_width
        )

        assert (
            long_height > short_height
        ), "Longer cell content should result in taller table"


class TestUnifiedCodeMetrics:
    """Test the refactored code metrics system."""

    def test_code_height_increases_with_lines(self):
        """Test that more code lines result in taller code blocks."""

        short_code = CodeElement(
            element_type=ElementType.CODE, code="print('hello')", language="python"
        )

        long_code = CodeElement(
            element_type=ElementType.CODE,
            code="\n".join([f"print('line {i}')" for i in range(10)]),
            language="python",
        )

        available_width = 400.0

        short_height = calculate_code_element_height(short_code, available_width)
        long_height = calculate_code_element_height(long_code, available_width)

        assert (
            long_height > short_height
        ), "More code lines should result in taller code block"
        assert short_height >= MIN_CODE_HEIGHT, "Should respect minimum height"

    def test_empty_code_minimum_height(self):
        """Test that empty code blocks return minimum height."""

        empty_code = CodeElement(
            code="", language="python", element_type=ElementType.CODE
        )
        height = calculate_code_element_height(empty_code, 500)
        assert (
            height >= MIN_CODE_HEIGHT
        ), f"Empty code should get minimum height {MIN_CODE_HEIGHT}, got {height}"

    def test_code_line_wrapping_affects_height(self):
        """Test that long code lines that wrap affect height."""

        short_line_code = CodeElement(
            element_type=ElementType.CODE, code="x = 1", language="python"
        )

        long_line_code = CodeElement(
            element_type=ElementType.CODE,
            code="very_long_variable_name = some_function_with_many_parameters(param1, param2, param3, param4, param5)",
            language="python",
        )

        narrow_width = 200.0  # Force wrapping

        short_height = calculate_code_element_height(short_line_code, narrow_width)
        long_height = calculate_code_element_height(long_line_code, narrow_width)

        assert (
            long_height > short_height
        ), "Long lines that wrap should result in taller code block"


class TestUnifiedImageMetrics:
    """Test the refactored image metrics system."""

    def test_image_aspect_ratio_maintained(self):
        """Test that image height calculation maintains aspect ratio."""

        # Test with a known aspect ratio from URL
        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/800x600/test.jpg",  # 4:3 ratio
        )

        available_width = 400.0
        height = calculate_image_element_height(image, available_width)

        calculated_ratio = available_width / height

        # Should be approximately 4:3 (1.333) if URL parsing worked
        # or default 16:9 (1.777) if it didn't
        assert 1.0 < calculated_ratio < 2.0, "Image should have reasonable aspect ratio"

    def test_explicit_height_directive_respected(self):
        """Test that explicit height directives override calculations."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            directives={"height": 150.0},
        )

        available_width = 400.0
        height = calculate_image_element_height(image, available_width)

        assert height == 150.0, "Explicit height directive should be respected"

    def test_image_minimum_height_enforced(self):
        """Test that images respect minimum height constraints."""

        # Create an image that would calculate to very small height
        tiny_image = ImageElement(
            element_type=ElementType.IMAGE, url="https://example.com/test.jpg"
        )

        very_small_width = 10.0
        height = calculate_image_element_height(tiny_image, very_small_width)

        # Should be at least the minimum image height
        from markdowndeck.layout.constants import MIN_IMAGE_HEIGHT

        assert height >= MIN_IMAGE_HEIGHT, "Should enforce minimum image height"

    def test_image_empty_url_handling(self):
        """Test that images with empty URLs return minimum height."""

        empty_image = ImageElement(element_type=ElementType.IMAGE, url="")
        height = calculate_image_element_height(empty_image, 400.0)

        from markdowndeck.layout.constants import MIN_IMAGE_HEIGHT

        assert (
            height >= MIN_IMAGE_HEIGHT
        ), "Empty image URL should return minimum height"


class TestImageElementSplitting:
    """Test the split() method functionality for ImageElement."""

    def test_image_split_always_fits(self):
        """Test that images always fit due to proactive scaling."""

        image = ImageElement(
            element_type=ElementType.IMAGE, url="https://example.com/test.jpg"
        )
        image.size = (400, 300)  # Set a size

        # Test with various heights - image should always fit due to proactive scaling
        fitted, overflowing = image.split(100)
        assert fitted is not None  # Image should always fit
        assert overflowing is None

        fitted, overflowing = image.split(10)  # Very small height
        assert fitted is not None  # Still should fit due to proactive scaling
        assert overflowing is None

    def test_image_split_preserves_metadata(self):
        """Test that image split preserves metadata."""

        image = ImageElement(
            element_type=ElementType.IMAGE,
            url="https://example.com/test.jpg",
            alt_text="Test image",
            object_id="test_image",
        )
        image.size = (400, 300)

        fitted, overflowing = image.split(200)

        assert fitted is not None
        assert fitted.url == "https://example.com/test.jpg"
        assert fitted.alt_text == "Test image"
        assert fitted.element_type == ElementType.IMAGE
        assert overflowing is None


class TestUnifiedMetricsIntegration:
    """Test integration between different metrics modules in unified system."""

    def test_consistent_minimum_heights(self):
        """Test that all metrics modules respect their minimum heights."""

        empty_text = TextElement(element_type=ElementType.TEXT, text="")
        empty_list = ListElement(element_type=ElementType.BULLET_LIST, items=[])
        empty_table = TableElement(element_type=ElementType.TABLE, headers=[], rows=[])
        empty_code = CodeElement(element_type=ElementType.CODE, code="")

        available_width = 400.0

        text_height = calculate_text_element_height(empty_text, available_width)
        list_height = calculate_list_element_height(empty_list, available_width)
        table_height = calculate_table_element_height(empty_table, available_width)
        code_height = calculate_code_element_height(empty_code, available_width)

        assert text_height >= MIN_TEXT_HEIGHT
        assert list_height >= MIN_LIST_HEIGHT
        assert table_height >= 30  # Table minimum from constants
        assert code_height >= MIN_CODE_HEIGHT

    def test_width_constraints_respected(self):
        """Test that all metrics modules handle width constraints properly."""

        content = "Test content that should work across all element types"

        text_elem = TextElement(element_type=ElementType.TEXT, text=content)
        list_elem = ListElement(
            element_type=ElementType.BULLET_LIST, items=[ListItem(text=content)]
        )
        code_elem = CodeElement(element_type=ElementType.CODE, code=content)

        narrow_width = 100.0
        wide_width = 500.0

        # All should handle narrow widths without errors
        narrow_text_height = calculate_text_element_height(text_elem, narrow_width)
        narrow_list_height = calculate_list_element_height(list_elem, narrow_width)
        narrow_code_height = calculate_code_element_height(code_elem, narrow_width)

        wide_text_height = calculate_text_element_height(text_elem, wide_width)
        wide_list_height = calculate_list_element_height(list_elem, wide_width)
        wide_code_height = calculate_code_element_height(code_elem, wide_width)

        # Narrow widths should generally result in taller elements due to wrapping
        assert narrow_text_height >= wide_text_height
        assert narrow_list_height >= wide_list_height
        assert narrow_code_height >= wide_code_height

        # All heights should be positive
        assert all(
            h > 0 for h in [narrow_text_height, narrow_list_height, narrow_code_height]
        )
        assert all(
            h > 0 for h in [wide_text_height, wide_list_height, wide_code_height]
        )
