"""
Parser edge case tests for specification compliance validation.

These tests validate that the parser correctly handles edge cases and
properly implements the specifications.
"""

from markdowndeck.models import ElementType, TextFormat, TextFormatType
from markdowndeck.parser import Parser


def test_parser_v_01_strips_same_line_directives_from_text():
    """
    Test Case: PARSER-V-01 (Violation)
    Validates that same-line directives are stripped from the element's text content.

    Spec: PARSER_SPEC.md, Rule 1; DIRECTIVES.md, Rule 1 (The Proximity Rule)
    """
    # Arrange
    parser = Parser()
    markdown = "# The Title of the Presentation [color=blue][fontsize=48]"

    # Act
    deck = parser.parse(markdown)
    slide = deck.slides[0]

    # Find the title element - it should be in renderable_elements after parsing
    title_element = None
    for element in slide.elements:
        if element.element_type == ElementType.TITLE:
            title_element = element
            break

    assert title_element is not None, "Title element not found in slide.elements"

    # Assert
    assert title_element.element_type == ElementType.TITLE
    assert (
        title_element.text == "The Title of the Presentation"
    ), "Directive string must be stripped from text"
    assert "color" in title_element.directives, "Directive 'color' was not parsed"
    assert "fontsize" in title_element.directives, "Directive 'fontsize' was not parsed"
    assert title_element.directives["color"] == "blue", "Directive value incorrect"
    assert title_element.directives["fontsize"] == "48", "Directive value incorrect"


def test_parser_v_01_strips_directives_from_image_text():
    """
    Test Case: PARSER-V-01b (Additional case)
    Validates that same-line directives are stripped from image alt text.

    Spec: PARSER_SPEC.md, Rule 1; DIRECTIVES.md, Rule 1 (The Proximity Rule)
    """
    # Arrange
    parser = Parser()
    markdown = (
        "![Test Image](http://example.com/image.png) [border=1pt solid red][width=300]"
    )

    # Act
    deck = parser.parse(markdown)
    slide = deck.slides[0]

    # Find the image element
    image_element = None
    for element in slide.elements:
        if element.element_type == ElementType.IMAGE:
            image_element = element
            break

    assert image_element is not None, "Image element not found in slide.elements"

    # Assert
    assert image_element.element_type == ElementType.IMAGE
    assert (
        image_element.alt_text == "Test Image"
    ), "Directive string must be stripped from alt text"
    assert "border" in image_element.directives, "Directive 'border' was not parsed"
    assert "width" in image_element.directives, "Directive 'width' was not parsed"


def test_parser_v_02_text_formatting_is_correct_type():
    """
    Test Case: PARSER-V-02 (Violation)
    Validates that TextElement.formatting contains a list of TextFormat objects, not booleans.

    Spec: DATA_MODELS.md - TextFormat specification
    """
    # Arrange
    parser = Parser()
    markdown = "This text is **bold** and *italic*."

    # Act
    deck = parser.parse(markdown)
    slide = deck.slides[0]

    # Find the text element
    text_element = None
    for element in slide.elements:
        if element.element_type == ElementType.TEXT:
            text_element = element
            break

    assert text_element is not None, "Text element not found in slide.elements"

    # Assert
    assert len(text_element.formatting) == 2, "Should have found two formatting spans."
    assert all(
        isinstance(f, TextFormat) for f in text_element.formatting
    ), "All items in formatting list must be TextFormat objects."

    # Verify the first format (bold)
    bold_format = text_element.formatting[0]
    assert bold_format.format_type == TextFormatType.BOLD
    assert (
        bold_format.start == 13
    )  # Position of "bold" in "This text is bold and italic."
    assert bold_format.end == 17

    # Verify the second format (italic)
    italic_format = text_element.formatting[1]
    assert italic_format.format_type == TextFormatType.ITALIC
    assert (
        italic_format.start == 22
    )  # Position of "italic" in "This text is bold and italic."
    assert italic_format.end == 28
