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

    def test_bug_indented_text_block_is_parsed_as_text(self, parser: Parser):
        """
        Test Case: PARSER-BUG-06 (UPDATED)
        Description: Validates that indented text is correctly normalized and parsed as
        distinct TEXT elements, not CODE elements.
        """
        # Arrange: Indented content with a heading and a paragraph.
        markdown = """
:::section
    ### A Heading
    This is **bold**.
:::
"""

        # Act
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children

        # Assert: The normalizer should have separated these into two elements.
        assert len(elements) == 2, f"Expected 2 elements, but found {len(elements)}."

        heading_element = elements[0]
        text_element = elements[1]

        # Both elements should be of type TEXT.
        assert (
            heading_element.element_type == ElementType.TEXT
        ), "Heading should be a TEXT element."
        assert (
            text_element.element_type == ElementType.TEXT
        ), "Indented paragraph should be a TEXT element."

        # Verify content and formatting are preserved.
        assert "A Heading" in heading_element.text
        assert "This is bold." in text_element.text
