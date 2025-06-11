from markdowndeck.api.request_builders.text_builder import TextRequestBuilder
from markdowndeck.models import AlignmentType, ElementType, TextElement


class TestTextBuilderLineSpacing:
    def test_line_spacing_converted_to_percentage(self):
        """
        Test Case: TEXT-BUILDER-C-01
        Validates that lineSpacing multipliers are correctly converted to percentages
        for the Google Slides API.
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

        # Assert
        paragraph_style_requests = [
            req
            for req in requests
            if "updateParagraphStyle" in req
            and "lineSpacing" in req["updateParagraphStyle"]["style"]
        ]

        assert (
            len(paragraph_style_requests) > 0
        ), "Should have a paragraph style request with lineSpacing"

        line_spacing_value = paragraph_style_requests[0]["updateParagraphStyle"][
            "style"
        ]["lineSpacing"]
        assert (
            line_spacing_value == 150.0
        ), f"Expected lineSpacing=150.0, got {line_spacing_value}"

    def test_default_line_spacing_is_applied(self):
        """
        Test Case: TEXT-BUILDER-C-02
        Validates that a default lineSpacing is applied and converted.
        """
        # Arrange
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

        # Assert
        paragraph_style_requests = [
            req
            for req in requests
            if "updateParagraphStyle" in req
            and "lineSpacing" in req["updateParagraphStyle"]["style"]
        ]

        assert (
            len(paragraph_style_requests) > 0
        ), "Should have a paragraph style request with lineSpacing"

        line_spacing_value = paragraph_style_requests[0]["updateParagraphStyle"][
            "style"
        ]["lineSpacing"]
        assert (
            abs(line_spacing_value - 115.0) < 0.01
        ), f"Expected default lineSpacing≈115.0, got {line_spacing_value}"
