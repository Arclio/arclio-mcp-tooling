import logging

import pytest
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    return Parser()


def log_tree(section, level=0):
    """Helper to recursively log the parsed tree for debugging."""
    indent = "  " * level
    logging.info(
        f"{indent}Section(type={section.type}, id={section.id}, num_children={len(section.children)})"
    )
    for child in section.children:
        if hasattr(child, "children"):  # It's a Section
            log_tree(child, level + 1)
        else:  # It's an Element
            element_type = getattr(child, "element_type", "N/A")
            text = getattr(child, "text", "")[:30]
            logging.info(
                f"{indent}  -> Element(type={element_type.value}, text='{text}...')"
            )


class TestContentPreservation:
    """
    This suite focuses on ensuring no content is lost during parsing, especially
    in complex but valid layouts. It addresses the core concern behind the
    previous content-loss bugs.
    """

    def test_preserves_content_around_nested_row(self, parser: Parser, caplog):
        """
        Validates that content in a column, both before and after a nested row,
        is fully preserved and correctly ordered.
        """
        caplog.set_level(logging.INFO)
        markdown = """
:::row
    :::column
        :::section
Content Before
        :::
        :::row
            :::column
                :::section
Inner Content
                :::
            :::
        :::
        :::section
Content After
        :::
    :::
:::
"""
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        logging.info("--- Parsed Tree Structure ---")
        log_tree(slide.root_section)
        logging.info("-----------------------------")

        # The top-level root section contains one child: the outer row
        outer_row = slide.root_section.children[0]
        assert outer_row.type == "row"

        # The outer row contains one child: the main column
        main_column = outer_row.children[0]
        assert main_column.type == "column"
        assert (
            len(main_column.children) == 3
        ), "Column should have three children: section, row, section"

        # Check the children of the main column
        section_before = main_column.children[0]
        nested_row = main_column.children[1]
        section_after = main_column.children[2]

        assert section_before.type == "section"
        assert nested_row.type == "row"
        assert section_after.type == "section"

        # Verify the content of each section
        assert section_before.children[0].text == "Content Before"
        assert nested_row.children[0].children[0].children[0].text == "Inner Content"
        assert section_after.children[0].text == "Content After"

    def test_preserves_all_elements_in_deeply_nested_structure(
        self, parser: Parser, caplog
    ):
        """
        Validates that all elements in a deeply nested but valid structure
        are parsed correctly.
        """
        caplog.set_level(logging.INFO)
        markdown = """
:::row
    :::column
        :::section
A
        :::
    :::
    :::column
        :::row
            :::column
                :::section
B
                :::
            :::
        :::
        :::section
C
        :::
    :::
:::
"""
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        logging.info("--- Parsed Tree Structure for Deep Nesting ---")
        log_tree(slide.root_section)
        logging.info("----------------------------------------------")

        # Extract all text elements from the parsed structure to verify content
        found_texts = []

        def find_text(section):
            for child in section.children:
                if hasattr(child, "children"):
                    find_text(child)
                else:
                    found_texts.append(child.text)

        find_text(slide.root_section)

        assert "A" in found_texts
        assert "B" in found_texts
        assert "C" in found_texts
        assert len(found_texts) == 3, "Should have found exactly 3 text elements."

    def test_preserves_multiple_sibling_sections_and_rows(self, parser: Parser, caplog):
        """
        Validates that multiple sibling blocks at various levels are all preserved.
        """
        caplog.set_level(logging.INFO)
        markdown = """
:::row
    :::column
        :::section
1
        :::
        :::section
2
        :::
    :::
:::
:::row
    :::column
        :::section
3
        :::
    :::
:::
"""
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        logging.info("--- Parsed Tree Structure for Siblings ---")
        log_tree(slide.root_section)
        logging.info("------------------------------------------")

        # The root section should have two direct children: two rows
        assert len(slide.root_section.children) == 2
        assert slide.root_section.children[0].type == "row"
        assert slide.root_section.children[1].type == "row"

        # The first row's column should have two sections
        first_row_col = slide.root_section.children[0].children[0]
        assert len(first_row_col.children) == 2

        # Verify all content is present
        found_texts = []

        def find_text(section):
            for child in section.children:
                if hasattr(child, "children"):
                    find_text(child)
                else:
                    found_texts.append(child.text)

        find_text(slide.root_section)

        assert sorted(found_texts) == ["1", "2", "3"]
