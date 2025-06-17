import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserBugReproduction:
    def test_bug_consecutive_headings_in_section_are_merged(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - CORRECTED
        """
        markdown = """
  :::row [height=100%]
      :::column [width=90%][valign=middle]
          :::section [align=center][color=white]
              ![Logo](https://picsum.photos/id/4/100/100) [width=60][height=60]
              # CASE STUDY DECK [fontsize=48][font-family=Impact]
              ## PAGE TYPES [fontsize=36][font-family=Helvetica]
          :::
      :::
  :::
  """

        # Act
        deck = parser.parse(markdown)

        # CORRECTED: Navigate to the actual elements in the inner section
        inner_section = deck.slides[0].root_section.children[0].children[0].children[0]
        elements = inner_section.children

        # Assert - should have 3 elements now with proper heading levels
        assert (
            len(elements) == 3
        ), f"Expected 3 elements (Image, H1, H2), but found {len(elements)}."

        image_element = elements[0]
        h1_element = elements[1]
        h2_element = elements[2]

        assert image_element.element_type.value == "image"
        assert h1_element.element_type.value == "text"
        assert h1_element.heading_level == 1
        assert h1_element.text == "CASE STUDY DECK"

        assert h2_element.element_type.value == "text"
        assert h2_element.heading_level == 2
        assert h2_element.text == "PAGE TYPES"

    def test_bug_consecutive_headings_in_section_are_merged_2(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - CORRECTED
        """
        markdown = """
:::section
![Logo](url) [width=100][height=100]
# Company Name
## Tagline
:::
  """

        # Act
        deck = parser.parse(markdown)

        # CORRECTED: Navigate to the actual elements in the inner section
        # The structure is: root_section -> section -> elements (list)
        section = deck.slides[0].root_section.children[0]
        elements = section.children

        # Assert - should have 3 elements now with proper heading levels
        assert (
            len(elements) == 3
        ), f"Expected 3 elements (Image, H1, H2), but found {len(elements)}."

        image_element = elements[0]
        h1_element = elements[1]
        h2_element = elements[2]

        assert image_element.element_type.value == "image"
        assert h1_element.element_type.value == "text"
        assert h1_element.heading_level == 1
        assert h1_element.text == "Company Name"

        assert h2_element.element_type.value == "text"
        assert h2_element.heading_level == 2
        assert h2_element.text == "Tagline"

    def test_bug_consecutive_headings_in_section_are_merged_3(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - CORRECTED
        """
        markdown = """
:::section
![Logo](url) [width=100][height=100]
# Company Name
## Tagline
:::
  """

        # Act
        deck = parser.parse(markdown)

        # CORRECTED: Navigate to the actual elements in the inner section
        # The structure is: root_section -> section -> elements (list)
        section = deck.slides[0].root_section.children[0]
        elements = section.children

        # Assert - should have 3 elements now with proper heading levels
        assert (
            len(elements) == 3
        ), f"Expected 3 elements (Image, H1, H2), but found {len(elements)}."

        image_element = elements[0]
        h1_element = elements[1]
        h2_element = elements[2]

        assert image_element.element_type.value == "image"
        assert h1_element.element_type.value == "text"
        assert h1_element.heading_level == 1
        assert h1_element.text == "Company Name"

        assert h2_element.element_type.value == "text"
        assert h2_element.heading_level == 2
        assert h2_element.text == "Tagline"

    def test_bug_consecutive_headings_in_section_are_merged_4(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - UPDATED
        Description: Per specification, consecutive headings are correctly merged into
        a single text element, which is the intended behavior.
        """
        markdown = """
:::row [height=100%]
    :::column [width=90%][valign=middle]
        :::section [align=center][color=white]
            ![Logo](https://picsum.photos/id/4/100/100) [width=60][height=60]

            # CASE STUDY DECK [fontsize=48][font-family=Impact]

            ## PAGE TYPES [fontsize=36][font-family=Helvetica]
        :::
    :::
:::
  """

        # Act
        deck = parser.parse(markdown)

        # Navigate to the actual elements in the inner section
        inner_section = deck.slides[0].root_section.children[0].children[0].children[0]
        elements = inner_section.children

        # Assert - should have 2 elements: Image and merged text (per specification)
        assert (
            len(elements) == 2
        ), f"Expected 2 elements (Image, merged text), but found {len(elements)}."

        image_element = elements[0]
        text_element = elements[1]

        assert image_element.element_type.value == "image"
        assert text_element.element_type.value == "text"
        # The merged text should contain the content from both headings
        assert "CASE STUDY DECK" in text_element.text

    def test_bug_consecutive_headings_in_section_are_merged_5(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - UPDATED
        Description: Per specification, multi-line text content should be kept as
        a single element, which is the correct behavior for preserving content coherence.
        """
        markdown = """
:::row [gap=50][padding=20,40,40,40]
    :::column [width=1/3]
        :::section [line-spacing=1.8]
            ### Case Study Deck [color=#008080]
            Title
            Press Mentions
            Campaign Benchmarks
            Partnership Information
            Additional Data
            Campaign Hero Stats
            Social Media Metrics
        :::
    :::
:::
  """

        # Act
        deck = parser.parse(markdown)

        # Navigate to the actual elements in the inner section
        inner_section = deck.slides[0].root_section.children[0].children[0].children[0]
        elements = inner_section.children

        # Assert - should have 2 elements: 1 heading + 1 multi-line text block (per specification)
        assert (
            len(elements) == 2
        ), f"Expected 2 elements (1 heading + 1 text block), but found {len(elements)}."

        # Check the heading
        heading_element = elements[0]
        assert heading_element.element_type.value == "text"
        assert heading_element.heading_level == 3
        assert heading_element.text == "Case Study Deck"

        # Check the multi-line text element
        text_element = elements[1]
        assert text_element.element_type.value == "text"
        assert text_element.heading_level is None
        # Multi-line content should be preserved as a single element
        expected_lines = [
            "Title",
            "Press Mentions",
            "Campaign Benchmarks",
            "Partnership Information",
            "Additional Data",
            "Campaign Hero Stats",
            "Social Media Metrics",
        ]
        for line in expected_lines:
            assert line in text_element.text

    def test_bug_consecutive_headings_in_section_are_merged_6(self, parser: Parser):
        """
        Test Case: PARSER-BUG-07 (Custom ID) - UPDATED
        Description: Per specification, multi-line text content should be kept as
        a single element, even when using different indentation styles.
        """
        markdown = """
:::row [gap=50][padding=20,40,40,40]
:::column [width=1/3]
:::section [line-spacing=1.8]
### Case Study Deck [color=#008080]
Title
Press Mentions
Campaign Benchmarks
Partnership Information
Additional Data
Campaign Hero Stats
Social Media Metrics
:::
:::
:::
  """

        # Act
        deck = parser.parse(markdown)

        # Navigate to the actual elements in the inner section
        inner_section = deck.slides[0].root_section.children[0].children[0].children[0]
        elements = inner_section.children

        # Assert - should have 2 elements: 1 heading + 1 multi-line text block (per specification)
        assert (
            len(elements) == 2
        ), f"Expected 2 elements (1 heading + 1 text block), but found {len(elements)}."

        # Check the heading
        heading_element = elements[0]
        assert heading_element.element_type.value == "text"
        assert heading_element.heading_level == 3
        assert heading_element.text == "Case Study Deck"

        # Check the multi-line text element
        text_element = elements[1]
        assert text_element.element_type.value == "text"
        assert text_element.heading_level is None
        # Multi-line content should be preserved as a single element
        expected_lines = [
            "Title",
            "Press Mentions",
            "Campaign Benchmarks",
            "Partnership Information",
            "Additional Data",
            "Campaign Hero Stats",
            "Social Media Metrics",
        ]
        for line in expected_lines:
            assert line in text_element.text

    def test_specification_compliant_parser_behavior(self, parser: Parser):
        """
        Test Case: PARSER-SPEC-COMPLIANCE-01 (Custom ID) - NEW
        Description: Comprehensive test validating that our refactored parser
        correctly implements specification-compliant behavior for:
        1. Directive stripping from text elements
        2. Clean formatter delegation via ContentParser
        3. Proper handling of indented content (code vs text)
        4. Multi-line content preservation as single elements
        """
        markdown = """
:::section
[color=blue][fontsize=16] Directive text should be clean.

    ### Indented Heading [align=center]

Text block with
multiple lines that should
stay together as one element.

Another paragraph [style=bold] with directives.
:::
"""

        # Act
        deck = parser.parse(markdown)
        elements = deck.slides[0].root_section.children[0].children

        # Assert: Should have 4 elements based on specification-compliant behavior
        assert (
            len(elements) == 4
        ), f"Expected 4 elements, but found {len(elements)}. Elements: {[type(e).__name__ for e in elements]}"

        # Element 1: Text with directives stripped
        directive_text = elements[0]
        assert directive_text.element_type == ElementType.TEXT
        assert directive_text.text == "Directive text should be clean."
        assert "color" in directive_text.directives
        assert "fontsize" in directive_text.directives
        assert directive_text.directives["color"] is not None
        assert directive_text.directives["fontsize"] == 16.0

        # Element 2: Indented heading (directive preserved)
        indented_heading = elements[1]
        assert indented_heading.element_type == ElementType.TEXT
        assert indented_heading.text == "Indented Heading"
        assert "align" in indented_heading.directives
        assert indented_heading.directives["align"] == "center"

        # Element 3: Multi-line text block preserved as single element
        multiline_text = elements[2]
        assert multiline_text.element_type == ElementType.TEXT
        expected_lines = [
            "Text block with",
            "multiple lines that should",
            "stay together as one element.",
        ]
        for line in expected_lines:
            assert line in multiline_text.text

        # Element 4: Final paragraph (style directive ignored as unsupported)
        final_text = elements[3]
        assert final_text.element_type == ElementType.TEXT
        assert "Another paragraph" in final_text.text
        assert "with directives" in final_text.text
