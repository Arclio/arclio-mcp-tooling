import pytest
from markdowndeck.models import ElementType
from markdowndeck.models.constants import TextFormatType
from markdowndeck.parser import Parser
from markdowndeck.parser.directive import DirectiveParser


@pytest.fixture
def parser() -> Parser:
    return Parser()


@pytest.fixture
def directive_parser() -> DirectiveParser:
    return DirectiveParser()


class TestParserBugReproduction:
    def test_bug_valueless_align_directive_causes_error(self, parser: Parser):
        """Test Case: PARSER-BUG-02 (Custom ID)"""
        markdown = ":::section [align]\nSome Text\n:::"
        deck = parser.parse(markdown)
        assert deck is not None

    def test_bug_compound_border_directive_misparsed(
        self, directive_parser: DirectiveParser
    ):
        """Test Case: PARSER-BUG-03 (Custom ID)"""
        directive_string = '[border="2pt solid #ccc"]'
        remaining_text, directives = directive_parser.parse_and_strip_from_text(
            directive_string
        )
        assert remaining_text == ""
        assert "border" in directives
        assert directives["border"] == "2pt solid #ccc"

    def test_bug_directives_are_parsed_from_code_blocks(self, parser: Parser):
        """Test Case: PARSER-BUG-04"""
        markdown = """
:::section
```python
# This code should print "[align=center]" literally
print("[align=center]")
```
This is some `inline [code=true]` with a directive inside.
:::
"""
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children
        code_block = next(
            (e for e in elements if e.element_type == ElementType.CODE), None
        )
        text_with_inline_code = next(
            (e for e in elements if e.element_type == ElementType.TEXT), None
        )
        assert code_block is not None
        assert text_with_inline_code is not None
        expected_code_content = '# This code should print "[align=center]" literally\nprint("[align=center]")'
        assert code_block.code.strip() == expected_code_content
        # REFACTORED: The final text should not include backticks, as they are formatting markers.
        expected_text_content = (
            "This is some inline [code=true] with a directive inside."
        )
        assert text_with_inline_code.text.strip() == expected_text_content

    def test_feature_directives_before_text_block(self, parser: Parser):
        """Test Case: PARSER-FEATURE-02"""
        markdown = ":::section\n[color=blue][fontsize=18] This text should be blue and 18pt.\n:::"
        deck = parser.parse(markdown)
        element = deck.slides[0].root_section.children[0].children[0]
        assert element.element_type == ElementType.TEXT
        assert element.text == "This text should be blue and 18pt."
        assert element.directives.get("color") is not None
        assert element.directives.get("fontsize") == 18.0

    def test_bug_indented_text_block_loses_formatting_and_keeps_indent(
        self, parser: Parser
    ):
        """
        Test Case: PARSER-BUG-06 (Custom ID)
        Description: An indented block of text is mis-tokenized as a `code_block`,
                     causing the parser to lose inline formatting and preserve unwanted
                     leading whitespace (indentation).
        Expected to Fail: YES. The text will have leading spaces, and formatting will be empty.
        """
        # Arrange: Note the indented 'This is **bold**' line.
        markdown = """
:::section
    ### A Heading
    This is **bold**.
:::
"""

        # Act
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children

        # There should be two elements: the heading and the text block
        assert len(elements) == 2, f"Expected 2 elements, but found {len(elements)}."
        text_element = elements[1]

        # Assert
        assert text_element.element_type == ElementType.TEXT

        # Assert for Bug #2 (Indentation)
        assert not text_element.text.startswith(
            " "
        ), "BUG CONFIRMED: Text content should not have leading whitespace."

        # Assert for Bug #1b (Formatting Loss)
        assert (
            len(text_element.formatting) > 0
        ), "BUG CONFIRMED: Formatting list is empty; inline bold was lost."
        assert text_element.formatting[0].format_type == TextFormatType.BOLD
