import pytest
from markdowndeck.models import TextFormatType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserInlineFormattingBugs:
    def test_bug_inline_formatting_preserves_spacing(self, parser: Parser):
        """
        Test Case: PARSER-BUG-09 (Custom ID)
        DESCRIPTION: Validates that text following an inline formatted element
                     is not concatenated, preserving the space between them. This
                     also ensures the character indices for formatting remain correct.
        """
        # Arrange - use the notebook example that triggers the bug
        markdown = ":::section\nThis is **bold text** using asterisks.[color=red]\n:::"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        elements = slide.root_section.children[0].children
        text_element = elements[0]

        # Assert
        # 1. The plain text representation must be correct.
        expected_text = "This is bold text using asterisks."
        assert text_element.text == expected_text, (
            f"BUG CONFIRMED: Text is corrupted. "
            f"Expected '{expected_text}', but got '{text_element.text}'."
        )

        # 2. The formatting indices must be correct for the plain text.
        assert len(text_element.formatting) == 1
        bold_format = text_element.formatting[0]
        assert bold_format.format_type == TextFormatType.BOLD

        # The word "bold text" should be selected
        selected_text = text_element.text[bold_format.start : bold_format.end]
        assert selected_text == "bold text"
