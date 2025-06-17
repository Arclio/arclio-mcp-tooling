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
        elements = deck.slides[0].root_section.children[0].children
        assert len(elements) == 5, "Expected 5 distinct elements to be parsed."
        element_texts = [getattr(e, "text", getattr(e, "code", "")) for e in elements]
        assert "Heading 1" in element_texts[0]
        assert "A paragraph" in element_texts[1]
        assert "A quote" in element_texts[4]

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
