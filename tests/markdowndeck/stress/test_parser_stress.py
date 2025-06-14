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
        """Test Case: STRESS-P-01 - Tests parsing a very large markdown file with many slides."""
        num_slides = 500
        slide_content = "# Test Slide\nContent\n---\nMore Content\n@@@\nFooter"
        massive_markdown = (slide_content + "\n===\n") * num_slides

        start_time = time.time()
        deck = parser.parse(massive_markdown, "Massive Deck")
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Parsing {num_slides} slides took {processing_time:.4f} seconds.")

        assert processing_time < 10.0, "Parsing many slides should be performant."
        assert len(deck.slides) == num_slides
        assert deck.slides[-1].get_footer_element().text == "Footer"

    def test_stress_p_01_single_slide_many_lines(self, parser: Parser):
        """Test Case: STRESS-P-01 (Variant) - Tests parsing a single slide with a huge number of content lines."""
        num_lines = 2000
        line_content = "This is a single line of text in a massive slide.\n"
        massive_content = line_content * num_lines
        markdown = f"# Massive Slide\n{massive_content}"

        start_time = time.time()
        deck = parser.parse(markdown)
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Parsing a slide with {num_lines} lines took {processing_time:.4f} seconds.")

        assert processing_time < 5.0, "Parsing a massive slide should be performant."
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        text_element = next(e for e in slide.elements if e.element_type == "text")
        assert text_element.text.count("\n") >= num_lines - 1
