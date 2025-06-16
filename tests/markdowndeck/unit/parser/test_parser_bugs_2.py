import pytest
from markdowndeck.models import ElementType
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
        """
        Test Case: PARSER-BUG-02 (Custom ID)
        Description: This test replicates the `ValueError: True is not a valid AlignmentType`.
        """
        markdown = ":::section [align]\nSome Text\n:::"
        deck = parser.parse(markdown)
        assert deck is not None  # If it doesn't crash, the fix works.

    def test_bug_compound_border_directive_misparsed(
        self, directive_parser: DirectiveParser
    ):
        """
        Test Case: PARSER-BUG-03 (Custom ID)
        Description: Replicates the log warning `Unsupported directive key 'solid'`.
        """
        directive_string = '[border="2pt solid #ccc"]'
        # FIXED: Corrected the tuple unpacking to match the function's return signature `(str, dict)`.
        remaining_text, directives = directive_parser.parse_and_strip_from_text(
            directive_string
        )
        assert remaining_text == "", "The entire directive string should be consumed."
        assert "border" in directives, "The 'border' key should be present."
        assert (
            "solid" not in directives
        ), "The parser should not treat 'solid' as a separate key."
        assert (
            directives["border"] == "2pt solid #ccc"
        ), "The entire compound value should be preserved as a string."

    def test_bug_directives_are_parsed_from_code_blocks(self, parser: Parser):
        """
        Test Case: PARSER-BUG-04
        Description: Exposes the bug where directive-like syntax is incorrectly
                     parsed from inside both inline and block-level code.
        """
        # Arrange
        markdown = """
```python
# This code should print "[align=center]" literally
print("[align=center]")
```
This is some `inline [code=true]` with a directive inside.
"""
        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        # REFACTORED: The parser now places these into children of the root_section.
        elements = slide.root_section.children

        code_block = next(
            (e for e in elements if e.element_type == ElementType.CODE), None
        )
        text_with_inline_code = next(
            (e for e in elements if e.element_type == ElementType.TEXT), None
        )

        assert code_block is not None, "Code block element was not found."
        assert (
            text_with_inline_code is not None
        ), "Text element with inline code was not found."

        # Assert
        expected_code_content = '# This code should print "[align=center]" literally\nprint("[align=center]")'
        assert (
            code_block.code.strip() == expected_code_content
        ), "Directives should not be stripped from the code block content."

        # FIXED: The backticks are markdown formatting and are not part of the final text content.
        # The test should check that the text *within* the backticks is preserved.
        expected_text_content = (
            "This is some inline [code=true] with a directive inside."
        )
        assert (
            text_with_inline_code.text.strip() == expected_text_content
        ), "Directives should not be stripped from the inline code content."

    def test_feature_directives_before_text_block(self, parser: Parser):
        """
        Test Case: PARSER-FEATURE-02
        Description: Validates that directives placed before a text block are
                     correctly associated with that block.
        """
        # Arrange
        markdown = "[color=blue][fontsize=18] This text should be blue and 18pt."

        # Act
        deck = parser.parse(markdown)
        element = deck.slides[0].root_section.children[0]

        # Assert
        assert element.element_type == ElementType.TEXT
        assert element.text == "This text should be blue and 18pt."
        assert element.directives.get("color") is not None
        assert element.directives.get("fontsize") == 18.0
