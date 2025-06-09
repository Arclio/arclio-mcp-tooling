# File: tests/markdowndeck/unit/api/request_builders/test_text_builder_line_spacing.py

from markdowndeck.api.request_builders.text_builder import TextRequestBuilder
from markdowndeck.models import AlignmentType, ElementType, TextElement


class TestTextBuilderLineSpacing:
    def test_line_spacing_converted_to_percentage(self):
        """
        Test Case: TEXT-BUILDER-C-01 (new)
        Validates that lineSpacing multipliers are correctly converted to percentages
        for the Google Slides API.

        Bug Fix: lineSpacing was being sent as multiplier (1.15) instead of percentage (115.0)
        """
        # Arrange
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test text with custom line spacing",
            object_id="test_text_123",
            position=(100, 200),
            size=(400, 100),
            directives={"line-spacing": 1.5},  # 1.5x line spacing
            horizontal_alignment=AlignmentType.LEFT,
        )

        builder = TextRequestBuilder()

        # Act
        requests = builder.generate_text_element_requests(text_element, "slide_123")

        # Assert - Find the updateParagraphStyle request with lineSpacing
        paragraph_style_requests = [
            req
            for req in requests
            if "updateParagraphStyle" in req
            and "lineSpacing" in req["updateParagraphStyle"]["style"]
        ]

        assert (
            len(paragraph_style_requests) > 0
        ), "Should have at least one paragraph style request with lineSpacing"

        # Check that lineSpacing is converted to percentage (1.5 * 100 = 150.0)
        line_spacing_value = paragraph_style_requests[0]["updateParagraphStyle"][
            "style"
        ]["lineSpacing"]
        assert (
            line_spacing_value == 150.0
        ), f"Expected lineSpacing=150.0, got {line_spacing_value}"

    def test_default_line_spacing_converted_to_percentage(self):
        """
        Test Case: TEXT-BUILDER-C-02 (new)
        Validates that default lineSpacing (1.15) is correctly converted to percentage (115.0)
        """
        # Arrange - Text element without explicit line-spacing directive
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test text with default line spacing",
            object_id="test_text_456",
            position=(100, 200),
            size=(400, 100),
            horizontal_alignment=AlignmentType.CENTER,
        )

        builder = TextRequestBuilder()

        # Act
        requests = builder.generate_text_element_requests(text_element, "slide_456")

        # Assert - Find the updateParagraphStyle request with lineSpacing
        paragraph_style_requests = [
            req
            for req in requests
            if "updateParagraphStyle" in req
            and "lineSpacing" in req["updateParagraphStyle"]["style"]
        ]

        assert (
            len(paragraph_style_requests) > 0
        ), "Should have at least one paragraph style request with lineSpacing"

        # Check that default lineSpacing is converted to percentage (1.15 * 100 = 115.0)
        line_spacing_value = paragraph_style_requests[0]["updateParagraphStyle"][
            "style"
        ]["lineSpacing"]
        assert (
            abs(line_spacing_value - 115.0) < 0.01
        ), f"Expected default lineSpacing≈115.0, got {line_spacing_value}"

    def test_apply_paragraph_styling_line_spacing_conversion(self):
        """
        Test Case: TEXT-BUILDER-C-03 (new)
        Validates that _apply_paragraph_styling method converts lineSpacing correctly
        """
        # Arrange
        text_element = TextElement(
            element_type=ElementType.TEXT,
            text="Test text for paragraph styling",
            object_id="test_text_789",
            directives={"line-spacing": 2.0},  # 2.0x line spacing
        )

        builder = TextRequestBuilder()
        requests = []

        # Act
        builder._apply_paragraph_styling(text_element, requests)

        # Assert
        assert len(requests) == 1, "Should have exactly one paragraph style request"

        style_request = requests[0]
        assert "updateParagraphStyle" in style_request

        line_spacing_value = style_request["updateParagraphStyle"]["style"][
            "lineSpacing"
        ]
        assert (
            line_spacing_value == 200.0
        ), f"Expected lineSpacing=200.0 (2.0*100), got {line_spacing_value}"

        # Verify fields include lineSpacing
        fields = style_request["updateParagraphStyle"]["fields"]
        assert (
            "lineSpacing" in fields
        ), f"Fields should include lineSpacing, got: {fields}"
