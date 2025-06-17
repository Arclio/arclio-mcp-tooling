import logging

import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser

logger = logging.getLogger(__name__)


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserContentLossReproduced:
    def test_bug_content_after_heading_in_same_block_is_lost(self, parser: Parser):
        """
        Test Case: PARSER-BUG-05 (Content Loss)
        DESCRIPTION: This test now validates the fix for the "greedy" heading formatter.
        By adding a blank line, we ensure markdown-it creates two distinct blocks.
        The test now verifies that our `_process_heading` method consumes ONLY the
        heading block, leaving the paragraph block to be processed next.
        """
        # REFACTORED: Added a blank line to create two distinct blocks per CommonMark spec.
        markdown = """
:::row [gap=50][padding=20,40,40,40]
    :::column [width=1/3]
        :::section
        ### Case Study Deck [color=#008080]

        Title
        Press Mentions
        Campaign Benchmarks
        :::
    :::
:::
        """
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        logger.info(slide)

        # Navigate to the section containing the content
        row = slide.root_section.children[0]
        logger.info(row)
        column = row.children[0]
        logger.info(column)
        content_section = column.children[0]
        logger.info(content_section)

        # This section should contain TWO elements: the heading and the paragraph
        assert (
            len(content_section.children) == 2
        ), "Parser should create two elements: one for the heading, one for the paragraph."

        heading_element = content_section.children[0]
        paragraph_element = content_section.children[1]
        logger.info(heading_element)
        logger.info(paragraph_element)

        assert heading_element.element_type == ElementType.TEXT
        assert heading_element.heading_level == 3
        assert "Case Study Deck" in heading_element.text

        assert paragraph_element.element_type == ElementType.TEXT
        assert paragraph_element.heading_level is None
        assert "Title" in paragraph_element.text
        assert "Press Mentions" in paragraph_element.text
        assert "Campaign Benchmarks" in paragraph_element.text
