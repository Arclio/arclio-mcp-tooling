"""
Parser edge case tests for specification compliance validation.
"""

from markdowndeck.models import ElementType, TextFormat
from markdowndeck.parser import Parser


def test_parser_v_01_strips_same_line_directives_from_text():
    """Test Case: PARSER-V-01"""
    parser = Parser()
    markdown = "# The Title of the Presentation [color=blue][fontsize=48]"
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    title_element = slide.get_title_element()

    assert title_element is not None, "Title element not found."
    assert title_element.text == "The Title of the Presentation"
    assert "color" in title_element.directives
    assert "fontsize" in title_element.directives
    assert (
        title_element.directives["color"]["value"] == "blue"
    )  # The converter now creates a dict
    assert title_element.directives["fontsize"] == 48.0


def test_parser_v_01b_strips_same_line_directives_from_subtitle():
    """Test Case: PARSER-V-01b"""
    parser = Parser()
    markdown = "# Main Title\n## A Subtitle for the Presentation [fontsize=24]"
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    subtitle_element = slide.get_subtitle_element()

    assert subtitle_element is not None, "Subtitle element not found."
    assert subtitle_element.text == "A Subtitle for the Presentation"
    assert "fontsize" in subtitle_element.directives
    assert subtitle_element.directives["fontsize"] == 24.0


def test_parser_v_01_strips_directives_from_image_text():
    """Test Case: PARSER-V-01d"""
    parser = Parser()
    markdown = (
        "![Test Image](http://example.com/image.png) [border=1pt solid red][width=300]"
    )
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    image_element = next(
        (e for e in slide.elements if e.element_type == ElementType.IMAGE), None
    )

    assert image_element is not None, "Image element not found."
    assert image_element.alt_text == "Test Image"
    assert "border" in image_element.directives
    assert "width" in image_element.directives


def test_parser_v_02_text_formatting_is_correct_type():
    """Test Case: PARSER-V-02"""
    parser = Parser()
    markdown = "This text is **bold** and *italic*."
    deck = parser.parse(markdown)
    slide = deck.slides[0]
    text_element = slide.root_section.children[0].children[0]

    assert text_element is not None, "Text element not found"
    assert len(text_element.formatting) == 2
    assert all(isinstance(f, TextFormat) for f in text_element.formatting)
