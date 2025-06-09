# File: tests/markdowndeck/unit/models/test_code_element.py
from markdowndeck.models import CodeElement, ElementType


class TestCodeElementSplit:
    def test_ova_01_code_element_split_contract(self):
        """
        Test Case: OVA-01 (Overflow Verification A)
        Validates that CodeElement.split() correctly populates the 'overflowing_part'.
        Spec: DATA_MODELS.md, .split() Contract
        """
        # Arrange
        original_code = "line 1\nline 2\nline 3\nline 4\nline 5"
        code_element = CodeElement(
            element_type=ElementType.CODE,
            code=original_code,
            # Mock the size and position as if it came from LayoutManager
            size=(400, 100),
        )

        # Mock a smaller available height that forces a split after line 2
        # Assume 20px per line for this test. Available height allows for ~2 lines.
        available_height = 45.0

        # Act
        fitted_part, overflowing_part = code_element.split(available_height)

        # Assert
        assert fitted_part is not None, "Fitted part should be created."
        assert overflowing_part is not None, "Overflowing part should be created."

        expected_fitted_code = "line 1\nline 2"
        expected_overflowing_code = "line 3\nline 4\nline 5"

        assert (
            fitted_part.code.strip() == expected_fitted_code
        ), "Fitted part has incorrect code."
        assert (
            overflowing_part.code.strip() == expected_overflowing_code
        ), "Overflowing part must contain the remaining code."
