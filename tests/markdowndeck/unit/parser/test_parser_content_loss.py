import pytest
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestContentLoss:
    def test_parses_multiple_consecutive_blocks(self, parser: Parser):
        """Validates that sequential blocks of different types are all parsed."""
        markdown = """
:::section
# Heading 1
A paragraph.
- A list item.
```python
a = 1
```
> A quote
:::
"""
        deck = parser.parse(markdown)

        # UPDATED: The refactored parser correctly identifies "# Heading 1" as the slide title
        assert deck.slides[0].get_title_element().text == "Heading 1"

        # The body should now contain 4 elements (title extracted separately)
        elements = deck.slides[0].root_section.children[0].children
        assert (
            len(elements) == 4
        ), "Expected 4 body elements (title extracted separately)."

        # FIXED: Properly validate each element type
        # Element 0: Text element
        assert elements[0].element_type.name == "TEXT"
        assert "A paragraph" in elements[0].text

        # Element 1: List element
        assert elements[1].element_type.name == "BULLET_LIST"
        assert len(elements[1].items) == 1
        assert "A list item" in elements[1].items[0].text

        # Element 2: Code element
        assert elements[2].element_type.name == "CODE"
        assert "a = 1" in elements[2].code

        # Element 3: Quote element
        assert elements[3].element_type.name == "QUOTE"
        assert "A quote" in elements[3].text

    def test_parses_multiple_rows_correctly(self, parser: Parser):
        """Ensures that multiple row blocks are not lost."""
        markdown = """
:::row
  :::column
    :::section
      Row 1
    :::
  :::
:::
:::row
  :::column
    :::section
      Row 2
    :::
  :::
:::
"""
        deck = parser.parse(markdown)
        root_children = deck.slides[0].root_section.children
        assert len(root_children) == 2, "Expected two row elements."
        assert root_children[0].type == "row"
        assert root_children[1].type == "row"
        assert root_children[0].children[0].children[0].children[0].text == "Row 1"
        assert root_children[1].children[0].children[0].children[0].text == "Row 2"
