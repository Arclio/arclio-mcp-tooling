"""Stress tests for the MarkdownDeck parser."""

import time

import pytest
from markdowndeck.parser import Parser


class TestParserStress:
    """Stress tests to validate parser performance and robustness."""

    @pytest.fixture(scope="class")
    def parser(self) -> Parser:
        """Provides a class-scoped Parser instance."""
        return Parser()

    def test_stress_p_01_massive_slide_count(self, parser: Parser):
        """
        Test Case: STRESS-P-01
        Tests parsing a very large markdown file with many slides.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        num_slides = 500
        slide_content = """
# Performance Test Slide
This is the content for the slide.
* Item 1
* Item 2
---
[width=1/2]
Left column content.
***
[width=1/2]
Right column content.
@@@
Footer text for the slide.
"""
        massive_markdown = (slide_content + "\n===\n") * num_slides

        start_time = time.time()
        deck = parser.parse(massive_markdown, "Massive Deck")
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Parsing {num_slides} slides took {processing_time:.4f} seconds.")

        assert processing_time < 10.0, "Parsing many slides should be performant."
        assert len(deck.slides) == num_slides, "All slides should be parsed correctly."
        assert deck.slides[-1].footer == "Footer text for the slide."

    def test_stress_p_01_single_slide_many_lines(self, parser: Parser):
        """
        Test Case: STRESS-P-01 (Variant)
        Tests parsing a single slide with a huge number of content lines.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        num_lines = 2000
        line_content = "This is a single line of text in a massive slide.\n"
        massive_content = line_content * num_lines
        markdown = f"# Massive Slide\n{massive_content}"

        start_time = time.time()
        deck = parser.parse(markdown)
        end_time = time.time()

        processing_time = end_time - start_time
        print(
            f"Parsing a slide with {num_lines} lines took {processing_time:.4f} seconds."
        )

        assert processing_time < 5.0, "Parsing a massive slide should be performant."
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        # Check that a single text element was created with all the content
        text_elements = [e for e in slide.elements if e.element_type == "text"]
        assert len(text_elements) == 1
        assert text_elements[0].text.count("\n") >= num_lines - 1

    def test_stress_p_01_pathological_directives(self, parser: Parser):
        """
        Test Case: STRESS-P-01 (Variant)
        Tests parsing content with an excessive number of directives.
        From: docs/markdowndeck/testing/TEST_CASES_STRESS.md
        """
        num_directives = 500
        directives_str = "[key=val]" * num_directives
        markdown = f"""
# Pathological Directives
{directives_str}
This is the actual content.
---
{directives_str}
| A | B |
|---|---|
| 1 | 2 |
"""
        start_time = time.time()
        deck = parser.parse(markdown)
        end_time = time.time()

        processing_time = end_time - start_time
        print(
            f"Parsing content with {num_directives * 2} directives took {processing_time:.4f} seconds."
        )

        assert processing_time < 2.0, "Parsing many directives should be performant."
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        assert len(slide.sections) == 2
