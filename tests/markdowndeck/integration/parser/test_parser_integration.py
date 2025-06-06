"""Comprehensive integration tests for the MarkdownDeck parser.

This test suite validates the complete parser pipeline and specifically tests
for all identified bugs and edge cases (P0-P8).
"""

import pytest
from markdowndeck.models import ElementType, TextFormatType
from markdowndeck.parser import Parser


class TestParserIntegration:
    """Integration tests for the complete parser pipeline."""

    @pytest.fixture
    def parser(self) -> Parser:
        """Return a parser instance."""
        return Parser()

    # ========================================================================
    # A. CRITICAL BUG: Missing Content Elements
    # ========================================================================

    def test_content_after_section_directives_a1(self, parser: Parser):
        """Test that content after section directives is properly parsed."""
        markdown = """# Test Slide
[color=blue][align=right]
**Paragraph One.**
[fontsize=12]
Paragraph Two, after a directive line."""

        deck = parser.parse(markdown)
        assert len(deck.slides) == 1

        slide = deck.slides[0]
        assert slide.title == "Test Slide"
        assert len(slide.sections) == 1

        section = slide.sections[0]
        assert section.type == "section"
        assert section.directives == {
            "color": {"type": "named", "value": "blue"},
            "align": "right",
        }

        # Should have 1 text element with combined content and all directives
        assert len(section.elements) == 1

        element = section.elements[0]
        assert element.element_type == ElementType.TEXT
        # Text should have markdown formatting processed, not raw markdown syntax
        assert element.text == "Paragraph One.\nParagraph Two, after a directive line."

        # All directives should be applied to the element
        assert element.directives["color"]["type"] == "named"
        assert element.directives["color"]["value"] == "blue"
        assert element.directives["align"] == "right"
        assert element.directives["fontsize"] == 12.0

        # Should have bold formatting for "Paragraph One."
        bold_formats = [
            f for f in element.formatting if f.format_type == TextFormatType.BOLD
        ]
        assert len(bold_formats) == 1
        assert bold_formats[0].start == 0
        assert bold_formats[0].end == 14  # Length of "Paragraph One."

        # Element should be part of slide elements
        slide_text_elements = [
            e for e in slide.elements if e.element_type == ElementType.TEXT
        ]
        assert len(slide_text_elements) == 1

    def test_content_after_heading_and_directives_a2(self, parser: Parser):
        """Test content after heading with preceding directives."""
        markdown = """# Main Title
## Sub Heading
[align=center][fontsize=10]
Bolded **Text 1**.
*Italic Text 2*."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should have: sub heading + 1 text element with combined content
        assert len(section.elements) == 2

        # Find the sub heading
        sub_heading = next(e for e in section.elements if e.text == "Sub Heading")
        assert (
            sub_heading.element_type == ElementType.TEXT
        )  # Section heading becomes TEXT

        # Default heading directives
        assert sub_heading.directives["fontsize"] == 18
        assert sub_heading.directives["margin_bottom"] == 10

        # Find the text element with combined content
        text_elements = [
            e
            for e in section.elements
            if e.element_type == ElementType.TEXT and "Text" in e.text
        ]
        assert len(text_elements) == 1

        elem = text_elements[0]
        # Text should have markdown formatting processed, not raw markdown syntax
        assert elem.text == "Bolded Text 1.\nItalic Text 2."
        assert elem.directives["align"] == "center"
        assert elem.directives["fontsize"] == 10

        # Should have both bold and italic formatting
        bold_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.BOLD
        ]
        italic_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.ITALIC
        ]

        assert len(bold_formats) == 1
        assert len(italic_formats) == 1

        # Check formatting positions
        assert bold_formats[0].start == 7  # Position of "Text 1"
        assert bold_formats[0].end == 13
        assert italic_formats[0].start == 15  # Position of "Italic Text 2"
        assert italic_formats[0].end == 28

    def test_simple_blockquote_a3(self, parser: Parser):
        """Test blockquote parsing after section separator."""
        markdown = """# Quote Test
Some content
---
> This is a quote."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert len(slide.sections) == 2

        # Second section should have the quote
        quote_section = slide.sections[1]
        assert len(quote_section.elements) == 1

        quote_elem = quote_section.elements[0]
        assert quote_elem.element_type == ElementType.QUOTE
        assert quote_elem.text == "This is a quote."

    def test_text_with_inline_code_and_formatting_a4(self, parser: Parser):
        """Test complex text with inline code and formatting."""
        markdown = """# Code Test
[border=1pt solid red]
Regular text, `inline code here`, and **bold text**.
Another line: `[directive_in_code]` and `[another=val]`."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should have one text element
        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        assert len(text_elements) == 1

        elem = text_elements[0]
        expected_text = "Regular text, inline code here, and bold text.\nAnother line: [directive_in_code] and [another=val]."
        assert elem.text == expected_text

        # Check directives
        assert "border" in elem.directives
        border_info = elem.directives["border"]
        assert border_info["width"] == "1pt"
        assert border_info["style"] == "solid"

        # Check formatting - should have code spans and bold
        code_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.CODE
        ]
        bold_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.BOLD
        ]

        assert len(code_formats) >= 2  # At least 2 code spans
        assert len(bold_formats) == 1  # One bold span

        # Verify directive-like strings in code are NOT parsed as directives
        assert "directive_in_code" not in elem.directives
        assert "another" not in elem.directives

    # ========================================================================
    # B. P0 - Directives in Text / Spurious Elements & P4 - Same-Line Directives
    # ========================================================================

    def test_directives_and_text_same_line_b1(self, parser: Parser):
        """Test directives and text on the same line."""
        markdown = """# Same Line Test
[color=red][fontsize=10]This is red and small."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        assert len(text_elements) == 1

        elem = text_elements[0]
        assert elem.text == "This is red and small."
        assert elem.directives["color"]["type"] == "named"
        assert elem.directives["color"]["value"] == "red"
        assert elem.directives["fontsize"] == 10

    def test_directives_separate_line_text_next_b2(self, parser: Parser):
        """Test directives on one line, text on next."""
        markdown = """# Separate Lines Test
[font-family=Arial][align=justify]
This text is justified Arial."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        assert len(text_elements) == 1

        elem = text_elements[0]
        assert elem.text == "This text is justified Arial."
        assert elem.directives["font-family"] == "Arial"
        assert elem.directives["align"] == "justify"

    def test_no_spurious_element_for_consumed_directives_b3(self, parser: Parser):
        """Test that directive-only lines consumed by block elements don't create spurious text elements."""
        markdown = """# List Test
[align=center]
- List item"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should only have a list element, no text element for the directive line
        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        list_elements = [
            e for e in section.elements if e.element_type == ElementType.BULLET_LIST
        ]

        # No spurious text elements
        directive_text_elements = [
            e for e in text_elements if "[align=center]" in e.text
        ]
        assert len(directive_text_elements) == 0

        # List should have the directive
        assert len(list_elements) == 1
        list_elem = list_elements[0]
        assert list_elem.directives["align"] == "center"

    # ========================================================================
    # C. P1 - Directives for Subsequent Block Elements
    # ========================================================================

    def test_directives_before_table_c1(self, parser: Parser):
        """Test directives before a table are applied to the table."""
        markdown = """# Table Test
[cell-align=right][border=dashed]
| Head1 | Head2 |
|-------|-------|
| Cell1 | Cell2 |"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should have a table element
        table_elements = [
            e for e in section.elements if e.element_type == ElementType.TABLE
        ]
        assert len(table_elements) == 1

        table_elem = table_elements[0]
        assert table_elem.directives["cell-align"] == "right"
        assert "border" in table_elem.directives

        # No separate text element for the directive line
        directive_text_elements = [
            e
            for e in section.elements
            if e.element_type == ElementType.TEXT and "cell-align" in e.text
        ]
        assert len(directive_text_elements) == 0

        # Verify table content
        assert table_elem.headers == ["Head1", "Head2"]
        assert table_elem.rows == [["Cell1", "Cell2"]]

    def test_directives_before_code_block_c2(self, parser: Parser):
        """Test directives before a code block are applied to the code block."""
        markdown = """# Code Test
[background=black][color=lime]
```python
print("Hello")
```"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should have a code element
        code_elements = [
            e for e in section.elements if e.element_type == ElementType.CODE
        ]
        assert len(code_elements) == 1

        code_elem = code_elements[0]
        assert code_elem.directives["background"]["type"] == "named"
        assert code_elem.directives["background"]["value"] == "black"
        assert code_elem.directives["color"]["type"] == "named"
        assert code_elem.directives["color"]["value"] == "lime"

        # No separate text element for the directive line
        directive_text_elements = [
            e
            for e in section.elements
            if e.element_type == ElementType.TEXT and "background" in e.text
        ]
        assert len(directive_text_elements) == 0

        # Verify code content
        assert code_elem.code.strip() == 'print("Hello")'
        assert code_elem.language == "python"

    # ========================================================================
    # D. P2 - Title Directives
    # ========================================================================

    def test_title_with_multiple_directives_d1(self, parser: Parser):
        """Test title with multiple directives."""
        markdown = """# [align=right][fontsize=24][color=blue]My Centered Title
Some content here."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Check slide title
        assert slide.title == "My Centered Title"

        # Find title element
        title_elements = [
            e for e in slide.elements if e.element_type == ElementType.TITLE
        ]
        assert len(title_elements) == 1

        title_elem = title_elements[0]
        assert title_elem.text == "My Centered Title"
        assert title_elem.directives["align"] == "right"
        assert title_elem.directives["fontsize"] == 24
        assert title_elem.directives["color"]["type"] == "named"
        assert title_elem.directives["color"]["value"] == "blue"

    def test_title_with_directives_and_spaces_d2(self, parser: Parser):
        """Test title with directives and extra spaces."""
        markdown = """#   [align=left]  Spaced Title
Content here."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]

        assert slide.title == "Spaced Title"

        title_elements = [
            e for e in slide.elements if e.element_type == ElementType.TITLE
        ]
        assert len(title_elements) == 1

        title_elem = title_elements[0]
        assert title_elem.text == "Spaced Title"
        assert title_elem.directives["align"] == "left"

    # ========================================================================
    # E. P3 - Indented Title Removal
    # ========================================================================

    def test_indented_title_removal_e1(self, parser: Parser):
        """Test that indented titles are properly removed from content."""
        markdown = """   #   Indented Title
Some content."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]

        assert slide.title == "Indented Title"

        # Content should not contain the title line
        text_elements = [
            e for e in slide.elements if e.element_type == ElementType.TEXT
        ]
        content_text = " ".join(e.text for e in text_elements)
        assert "Indented Title" not in content_text
        assert "Some content." in content_text

    # ========================================================================
    # F. P7 - Code Fence Robustness
    # ========================================================================

    def test_slide_splitting_with_various_code_fences_f1(self, parser: Parser):
        """Test slide splitting with various code fence types."""
        markdown = """# Slide 1
````json
{"key": "value"}
````
===
# Slide 2
```text
Hello
```"""

        deck = parser.parse(markdown)
        assert len(deck.slides) == 2

        # First slide
        slide1 = deck.slides[0]
        assert slide1.title == "Slide 1"
        code_elements_1 = [
            e for e in slide1.elements if e.element_type == ElementType.CODE
        ]
        assert len(code_elements_1) == 1
        assert code_elements_1[0].language == "json"

        # Second slide
        slide2 = deck.slides[1]
        assert slide2.title == "Slide 2"
        code_elements_2 = [
            e for e in slide2.elements if e.element_type == ElementType.CODE
        ]
        assert len(code_elements_2) == 1
        assert code_elements_2[0].language == "text"

    # ========================================================================
    # G. P8 - Enhanced CSS Value Parsing
    # ========================================================================

    def test_rgba_color_parsing_g1(self, parser: Parser):
        """Test rgba color parsing."""
        markdown = """# RGBA Test
[background=rgba(255, 0, 128, 0.5)] Text"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        assert len(text_elements) == 1

        elem = text_elements[0]
        bg = elem.directives["background"]
        assert bg["type"] == "rgba"
        assert bg["r"] == 255
        assert bg["g"] == 0
        assert bg["b"] == 128
        assert bg["a"] == 0.5

    def test_hsla_color_parsing_g2(self, parser: Parser):
        """Test hsla color parsing."""
        markdown = """# HSLA Test
[color=hsla(120, 60%, 70%, 0.8)] Text"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        color = elem.directives["color"]
        assert color["type"] == "hsla"
        assert color["h"] == 120
        assert color["s"] == 60
        assert color["l"] == 70
        assert color["a"] == 0.8

    def test_linear_gradient_parsing_g3(self, parser: Parser):
        """Test linear gradient parsing."""
        markdown = """# Gradient Test
[background=linear-gradient(45deg, red, blue)] Text"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        bg = elem.directives["background"]
        assert "gradient" in bg["type"] or bg["type"] == "linear"
        assert "45deg, red, blue" in bg["definition"]

    def test_css_dimensions_g4(self, parser: Parser):
        """Test CSS dimension parsing."""
        markdown = """# Dimension Test
[padding=1.5em][margin=10px] Text"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        assert elem.directives["padding"] == 1.5
        assert elem.directives["margin"] == 10

    def test_complex_border_g5(self, parser: Parser):
        """Test complex border parsing."""
        markdown = """# Border Test
[border=2pt dashed rgba(50,50,50,0.7)] Text"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        border = elem.directives["border"]
        assert border["width"] == "2pt"
        assert border["style"] == "dashed"
        assert border["color"]["type"] == "rgba"
        assert border["color"]["r"] == 50

    # ========================================================================
    # H. Inline Code vs. Directives
    # ========================================================================

    def test_plain_text_resembling_directive_h1(self, parser: Parser):
        """Test plain text that resembles directives."""
        markdown = """# Directive-like Text
This is text [not_a_directive] and more text."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        assert elem.text == "This is text [not_a_directive] and more text."
        assert "not_a_directive" not in elem.directives

    def test_inline_code_with_directive_syntax_h2(self, parser: Parser):
        """Test inline code containing directive-like syntax."""
        markdown = """# Code vs Directive
Code: `[this_is_code=true]` and `[another_code]`"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        assert elem.text == "Code: [this_is_code=true] and [another_code]"

        # Should have code formatting
        code_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.CODE
        ]
        assert len(code_formats) == 2

        # Should NOT parse as directives
        assert "this_is_code" not in elem.directives
        assert "another_code" not in elem.directives

    def test_inline_code_at_boundaries_h3(self, parser: Parser):
        """Test inline code at start/end of text."""
        markdown = """# Boundary Code
`[start_code]` text `[end_code]`"""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        elem = text_elements[0]
        assert "[start_code] text [end_code]" in elem.text

        code_formats = [
            f for f in elem.formatting if f.format_type == TextFormatType.CODE
        ]
        assert len(code_formats) == 2

        assert "start_code" not in elem.directives
        assert "end_code" not in elem.directives

    # ========================================================================
    # I. Section Directive Inheritance and Overriding
    # ========================================================================

    def test_directive_inheritance_and_override_i1(self, parser: Parser):
        """Test section directive inheritance and element-specific overrides."""
        markdown = """# Inheritance Test
[color=blue][fontsize=10]
This is blue, size 10.
[fontsize=12][font-family=Arial]
This is blue, size 12, and Arial."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should have section directives
        assert section.directives["color"]["value"] == "blue"
        assert section.directives["fontsize"] == 10

        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        # Should have one combined text element (markdown parsing combines without blank lines)
        assert len(text_elements) == 1

        elem = text_elements[0]
        # Should inherit section directives and apply element-specific overrides
        assert elem.directives["color"]["value"] == "blue"  # inherited from section
        assert elem.directives["fontsize"] == 12.0  # overridden by element directive
        assert elem.directives["font-family"] == "Arial"  # element-specific

        # Combined text content
        expected_text = "This is blue, size 10.\nThis is blue, size 12, and Arial."
        assert elem.text == expected_text

    # ========================================================================
    # J. Empty and Minimal Content
    # ========================================================================

    def test_empty_slide_j1(self, parser: Parser):
        """Test handling of empty slides."""
        markdown = """# First Slide
Content
===
===
# Last Slide
More content"""

        deck = parser.parse(markdown)
        # Should only have 2 slides (empty slide filtered out)
        assert len(deck.slides) == 2
        assert deck.slides[0].title == "First Slide"
        assert deck.slides[1].title == "Last Slide"

    def test_section_with_only_directives_j2(self, parser: Parser):
        """Test section with only directives."""
        markdown = """# Directive Only Test
[width=100%][height=100%]
---
Some content in next section."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert len(slide.sections) == 2

        # First section should have directives but no elements
        first_section = slide.sections[0]
        assert first_section.directives["width"] == 1.0  # 100% -> 1.0
        assert first_section.directives["height"] == 1.0
        assert len(first_section.elements) == 0

    def test_paragraph_with_only_spaces_j3(self, parser: Parser):
        """Test paragraph with only spaces."""
        markdown = """# Spaces Test

Regular content."""

        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Should only have the regular content, not the spaces
        text_elements = [
            e for e in section.elements if e.element_type == ElementType.TEXT
        ]
        assert len(text_elements) == 1
        assert text_elements[0].text == "Regular content."
