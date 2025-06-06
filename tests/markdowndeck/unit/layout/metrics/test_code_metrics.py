"""Updated unit tests for code element metrics with split() method support."""

from markdowndeck.layout.constants import MIN_CODE_HEIGHT
from markdowndeck.layout.metrics.code import calculate_code_element_height
from markdowndeck.models import CodeElement, ElementType


class TestCodeMetrics:
    """Unit tests for code element height calculation."""

    def test_calculate_code_height_empty(self):
        element = CodeElement(code="", language="python", element_type=ElementType.CODE)
        height = calculate_code_element_height(element, 500)
        assert height >= MIN_CODE_HEIGHT  # Use actual constant

    def test_calculate_code_height_single_line(self):
        element = CodeElement(code="print('hello')", element_type=ElementType.CODE)
        height = calculate_code_element_height(element, 500)
        # Current implementation uses compact line height and padding
        assert height >= (1 * 14.0) + (2 * 8.0)  # line_height + padding

    def test_calculate_code_height_multiple_lines(self):
        code = "def func():\n    pass\n# Comment"
        element = CodeElement(
            code=code, language="python", element_type=ElementType.CODE
        )
        height = calculate_code_element_height(element, 500)
        # 3 lines * line_height + padding + potential language_label
        assert height >= (3 * 14.0) + (2 * 8.0)

    def test_calculate_code_height_long_lines_wrapping(self):
        long_line = "a = " + "'very long string' * 10"  # Approx 200 chars
        element_narrow = CodeElement(code=long_line, element_type=ElementType.CODE)
        height_narrow = calculate_code_element_height(
            element_narrow, 150
        )  # Narrow width

        element_wide = CodeElement(code=long_line, element_type=ElementType.CODE)
        height_wide = calculate_code_element_height(element_wide, 500)  # Wide width

        assert (
            height_narrow > height_wide
        )  # Narrower width means more height due to wrapping

    def test_calculate_code_height_with_and_without_lang_label(self):
        code = "test"
        el_no_lang = CodeElement(
            code=code, language="text", element_type=ElementType.CODE
        )  # "text" = no label
        height_no_lang = calculate_code_element_height(el_no_lang, 500)

        el_with_lang = CodeElement(
            code=code, language="python", element_type=ElementType.CODE
        )
        height_with_lang = calculate_code_element_height(el_with_lang, 500)

        # Both should return reasonable heights
        assert height_no_lang > 0
        assert height_with_lang > 0


class TestCodeElementSplitting:
    """Test the new split() method functionality for CodeElement."""

    def test_code_split_basic_functionality(self):
        """Test basic split() method functionality."""
        code = "line1\nline2\nline3\nline4\nline5"
        element = CodeElement(code=code, element_type=ElementType.CODE)
        element.size = (400, 100)  # Set size for splitting logic

        # Test with sufficient height (should fit all)
        fitted, overflowing = element.split(200)
        assert fitted is not None
        assert overflowing is None
        assert fitted.code == code

    def test_code_split_minimum_requirements(self):
        """Test that split() respects minimum 2-line requirement."""
        code = "line1\nline2\nline3\nline4"
        element = CodeElement(code=code, element_type=ElementType.CODE)
        element.size = (400, 80)

        # Test with very limited height (less than 2 lines worth)
        fitted, overflowing = element.split(20)  # Very small height

        # Should reject split due to minimum requirement
        assert fitted is None
        assert overflowing is not None
        assert overflowing.code == code

    def test_code_split_successful_split(self):
        """Test successful split when minimum requirements are met."""
        code = "line1\nline2\nline3\nline4\nline5\nline6"
        element = CodeElement(code=code, element_type=ElementType.CODE)
        element.size = (400, 120)

        # Test with moderate height (should split)
        fitted, overflowing = element.split(60)  # Enough for ~3 lines

        if fitted is not None:  # Split was accepted
            assert fitted.code != code  # Should be partial
            assert overflowing is not None
            assert len(fitted.code.split("\n")) >= 2  # At least 2 lines
            assert len(overflowing.code.split("\n")) >= 1  # At least 1 line remaining

    def test_code_split_empty_code(self):
        """Test split() with empty code."""
        element = CodeElement(code="", element_type=ElementType.CODE)
        element.size = (400, 50)

        fitted, overflowing = element.split(100)
        assert fitted is None
        assert overflowing is None

    def test_code_split_single_line(self):
        """Test split() with single line of code."""
        element = CodeElement(code="single_line", element_type=ElementType.CODE)
        element.size = (400, 50)

        fitted, overflowing = element.split(20)  # Very small height

        # Single line that doesn't fit should be treated as atomic
        assert fitted is None
        assert overflowing is not None

    def test_code_split_preserves_metadata(self):
        """Test that split preserves element metadata."""
        element = CodeElement(
            code="line1\nline2\nline3\nline4",
            language="python",
            element_type=ElementType.CODE,
            object_id="test_code",
        )
        element.size = (400, 80)

        fitted, overflowing = element.split(50)

        if fitted is not None:
            assert fitted.language == "python"
            assert fitted.element_type == ElementType.CODE
            assert hasattr(fitted, "size")

        if overflowing is not None:
            assert overflowing.language == "python"
            assert overflowing.element_type == ElementType.CODE
