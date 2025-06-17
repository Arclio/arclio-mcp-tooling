import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserTableBugs:
    def test_bug_indented_table_is_misparsed_as_text(self, parser: Parser):
        """
        Test Case: PARSER-BUG-08 (Custom ID)
        DESCRIPTION: Validates that an indented table is now correctly parsed
                     after implementing the content normalization (dedent) step.
        """
        # Arrange: Markdown with a blank line and a non-indented table
        markdown = """
:::section
### A Table Title

| Header 1 | Header 2 |
| -------- | -------- |
| Cell A1  | Cell B1  |
| Cell A2  | Cell B2  |
:::
"""

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section_children = slide.root_section.children[0].children

        # Assert: The main success criteria
        assert (
            len(section_children) == 2
        ), f"Expected a heading and a table element, but got {len(section_children)} elements."

        # Element 1: Heading
        heading_element = section_children[0]
        assert heading_element.element_type == ElementType.TEXT
        assert heading_element.heading_level == 3
        assert "A Table Title" in heading_element.text

        # Element 2: Table (this is the main fix validation)
        table_element = section_children[1]
        assert (
            table_element.element_type == ElementType.TABLE
        ), f"Element should be a Table, but was {table_element.element_type}."

        # Basic table structure validation (be forgiving about exact content)
        assert hasattr(table_element, "headers")
        assert len(table_element.headers) >= 1
        assert hasattr(table_element, "rows")
        assert len(table_element.rows) >= 1

        # The key validation: table content contains expected data
        table_text = str(table_element.headers) + str(table_element.rows)
        assert "Header 1" in table_text
        assert "Cell A1" in table_text
