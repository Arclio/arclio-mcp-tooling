import pytest
from markdowndeck.models import ListElement
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestParserBugReproduction:
    """Tests designed to fail, exposing known bugs in the Parser and its formatters."""

    def test_bug_list_item_directive_not_parsed(self, parser: Parser):
        """
        Test Case: PARSER-BUG-01
        Description: Exposes the bug where directives on list items are not parsed
                     and remain as raw text in the item's content.
        Expected to Fail: Yes. The assertion on `item.text` will fail.
        """
        # Arrange
        markdown = "- List Item [color=red]"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # FIXED: Correctly traverse the parsed structure.
        # The structure is: root_section -> ListElement (direct child)
        # Find the ListElement in the root_section's children
        list_element = next(
            (child for child in slide.root_section.children if isinstance(child, ListElement)),
            None,
        )
        assert list_element is not None, "ListElement not found in parsed section."
        item = list_element.items[0]

        # Assert
        assert item.text == "List Item", "Directive text should be stripped from the list item content."
        assert item.directives.get("color") is not None, "Directive should be parsed and stored in the item's directives."
        assert item.directives["color"]["value"]["value"] == "red"

    def test_feature_indented_fenced_blocks(self, parser: Parser):
        """
        Test Case: PARSER-FEATURE-01
        Description: Validates that indented fenced blocks are parsed correctly, formalizing this as a feature.
        Expected to Fail: No, this is expected to pass but formalizes the behavior.
        """
        # Arrange
        markdown = """
    :::section [padding=10]
        Content in an indented section.
        :::row
            :::column
            Indented column.
            :::
        :::
    :::
"""
        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.root_section is not None, "Root section should be created."
        assert len(slide.root_section.children) == 1, "Root section should contain the parsed content."

        outer_section = slide.root_section.children[0]
        assert outer_section.type == "section"
        assert outer_section.directives.get("padding") == 10.0

        row = outer_section.children[1]  # children[0] is the text "Content..."
        assert row.type == "row"

        column = row.children[0]
        assert column.type == "section"
        assert column.children[0].text == "Indented column."
