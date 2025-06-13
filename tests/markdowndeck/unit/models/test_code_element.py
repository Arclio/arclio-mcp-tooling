from markdowndeck.models import CodeElement, ElementType


class TestCodeElementSplit:
    """Unit tests for the CodeElement's split method."""

    def test_split_contract(self):
        """
        Test Case: DATA-E-SPLIT-CODE-01 (Custom ID)
        Validates that CodeElement.split() correctly partitions code content.
        Spec: DATA_MODELS.md, .split() Contract
        """
        original_code = "line 1\nline 2\nline 3\nline 4\nline 5"
        code_element = CodeElement(
            element_type=ElementType.CODE, code=original_code, size=(400, 100)
        )

        available_height = 45.0
        fitted_part, overflowing_part = code_element.split(available_height)

        assert fitted_part is not None, "Fitted part should be created."
        assert overflowing_part is not None, "Overflowing part should be created."
        assert (
            "line 3" in overflowing_part.code
        ), "Overflowing part must contain the remaining code."
