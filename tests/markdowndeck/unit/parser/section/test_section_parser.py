"""Updated unit tests for the SectionParser with enhanced content handling."""

import pytest
from markdowndeck.models.slide import Section
from markdowndeck.parser.section.section_parser import SectionParser


class TestSectionParser:
    """Updated unit tests for the SectionParser component."""

    @pytest.fixture
    def parser(self) -> SectionParser:
        return SectionParser()

    # ========================================================================
    # Basic Section Parsing Tests (Updated)
    # ========================================================================

    def test_parse_single_section_no_separators(self, parser: SectionParser):
        """Test parsing simple content without separators."""
        content = "This is simple content with **formatting**."
        sections = parser.parse_sections(content)

        assert len(sections) == 1
        assert isinstance(sections[0], Section)
        assert sections[0].type == "section"
        assert sections[0].content == content
        assert sections[0].id is not None
        assert sections[0].directives == {}
        assert sections[0].elements == []

    def test_parse_vertical_sections_only(self, parser: SectionParser):
        """Test parsing with only vertical separators (---)."""
        content = """[width=100%]
Content A with directives
---
[align=center]
Content B centered
---
[color=red]
Content C in red"""

        sections = parser.parse_sections(content)
        assert len(sections) == 3

        # All should be section type
        for section in sections:
            assert section.type == "section"
            assert section.id is not None
            assert section.elements == []

        # Check content preservation
        assert "Content A with directives" in sections[0].content
        assert "Content B centered" in sections[1].content
        assert "Content C in red" in sections[2].content

        # Directives should be preserved in content for later parsing
        assert "[width=100%]" in sections[0].content
        assert "[align=center]" in sections[1].content
        assert "[color=red]" in sections[2].content

    def test_parse_horizontal_sections_only(self, parser: SectionParser):
        """Test parsing with only horizontal separators (***)."""
        content = """[width=1/2]
Left column content
***
[width=1/2][align=right]
Right column content"""

        sections = parser.parse_sections(content)
        assert len(sections) == 1
        assert sections[0].type == "row"
        assert len(sections[0].subsections) == 2

        # Check subsections
        left_section = sections[0].subsections[0]
        right_section = sections[0].subsections[1]

        assert left_section.type == "section"
        assert "Left column content" in left_section.content
        assert "[width=1/2]" in left_section.content

        assert right_section.type == "section"
        assert "Right column content" in right_section.content
        assert "[width=1/2][align=right]" in right_section.content

        # Row's content should be the original unsplit content
        assert "Left column content" in sections[0].content
        assert "Right column content" in sections[0].content

    def test_parse_mixed_vertical_and_horizontal(self, parser: SectionParser):
        """Test parsing with both vertical and horizontal separators."""
        content = """[background=blue]
Top Section
---
[width=1/2]
Left Column
***
[width=1/2][align=center]
Right Column
---
[margin=20]
Bottom Section"""

        sections = parser.parse_sections(content)
        assert len(sections) == 3

        # First section: simple
        assert sections[0].type == "section"
        assert "Top Section" in sections[0].content

        # Second section: row with subsections
        assert sections[1].type == "row"
        assert len(sections[1].subsections) == 2
        assert "Left Column" in sections[1].subsections[0].content
        assert "Right Column" in sections[1].subsections[1].content

        # Third section: simple
        assert sections[2].type == "section"
        assert "Bottom Section" in sections[2].content

    # ========================================================================
    # Code Block Handling Tests
    # ========================================================================

    def test_sections_with_code_blocks_and_separators(self, parser: SectionParser):
        """Test that separators inside code blocks are ignored."""
        content = """Introduction text

```python
# This --- should not split
# And this *** should not split either
def function():
    return "---"
```

---

Conclusion text

```bash
echo "***"
# Another --- in code
```"""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        # First section should contain the entire code block
        first_section = sections[0]
        assert "Introduction text" in first_section.content
        assert "# This --- should not split" in first_section.content
        assert "And this *** should not split either" in first_section.content
        assert 'return "---"' in first_section.content

        # Second section
        second_section = sections[1]
        assert "Conclusion text" in second_section.content
        assert 'echo "***"' in second_section.content
        assert "# Another --- in code" in second_section.content

    def test_sections_with_nested_code_fences(self, parser: SectionParser):
        """Test handling of nested code fence types."""
        content = """Section A

````markdown
```python
print("nested")
```
````

---

Section B

```text
Simple code
```"""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        assert "Section A" in sections[0].content
        assert 'print("nested")' in sections[0].content
        assert "Section B" in sections[1].content
        assert "Simple code" in sections[1].content

    # ========================================================================
    # Directive Preservation Tests
    # ========================================================================

    def test_directive_preservation_for_later_parsing(self, parser: SectionParser):
        """Test that directives are preserved in content for DirectiveParser."""
        content = """[background=#f0f0f0][padding=20px]
## Header with background

Some content here.

[color=red][fontsize=16]
Red text paragraph.

---

[width=100%][height=400px]
Full width section.
***
[align=center][margin=10px]
Centered subsection."""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        # First section should preserve all directive content
        first_section = sections[0]
        assert "[background=#f0f0f0][padding=20px]" in first_section.content
        assert "[color=red][fontsize=16]" in first_section.content
        assert "## Header with background" in first_section.content
        assert "Red text paragraph." in first_section.content

        # Second section is a row
        assert sections[1].type == "row"
        subsections = sections[1].subsections
        assert len(subsections) == 2

        assert "[width=100%][height=400px]" in subsections[0].content
        assert "[align=center][margin=10px]" in subsections[1].content

    def test_complex_directive_patterns_preserved(self, parser: SectionParser):
        """Test preservation of complex directive patterns."""
        content = """[background=linear-gradient(45deg, red, blue)][border=2px solid rgba(0,0,0,0.3)]
Advanced styled section.

[transform=rotate(5deg)][box-shadow=0 4px 8px rgba(0,0,0,0.1)]
Another advanced section.

---

[cell-align=center][border-collapse=collapse]
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |"""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        # First section with advanced CSS
        first_content = sections[0].content
        assert "linear-gradient(45deg, red, blue)" in first_content
        assert "rgba(0,0,0,0.3)" in first_content
        assert "rotate(5deg)" in first_content
        assert "rgba(0,0,0,0.1)" in first_content

        # Second section with table directives
        second_content = sections[1].content
        assert "[cell-align=center][border-collapse=collapse]" in second_content
        assert "| Header 1 | Header 2 |" in second_content

    # ========================================================================
    # Empty Content and Edge Cases
    # ========================================================================

    def test_empty_sections_filtered(self, parser: SectionParser):
        """Test that empty sections are properly filtered."""
        content = """Section A
---

---


***

---
Section B"""

        sections = parser.parse_sections(content)
        # Should only have 2 sections (empty ones filtered)
        assert len(sections) == 2
        assert "Section A" in sections[0].content
        assert "Section B" in sections[1].content

    def test_content_starting_ending_with_separators(self, parser: SectionParser):
        """Test content that starts/ends with separators."""
        # Vertical separators
        content_v = """---
Section 1 content
---
Section 2 content
---"""
        sections_v = parser.parse_sections(content_v)
        assert len(sections_v) == 2
        assert "Section 1 content" in sections_v[0].content
        assert "Section 2 content" in sections_v[1].content

        # Horizontal separators
        content_h = """***
[width=1/2]
Col 1
***
[width=1/2]
Col 2
***"""
        sections_h = parser.parse_sections(content_h)
        assert len(sections_h) == 1
        assert sections_h[0].type == "row"
        assert len(sections_h[0].subsections) == 2

    def test_empty_input_content(self, parser: SectionParser):
        """Test parsing empty or whitespace-only content."""
        # Completely empty
        sections_empty = parser.parse_sections("")
        assert len(sections_empty) == 0

        # Whitespace only
        sections_ws = parser.parse_sections("   \n\t   \n  ")
        assert len(sections_ws) == 0

        # Only separators
        sections_sep = parser.parse_sections("---\n***\n---")
        assert (
            len(sections_sep) == 0
        )  # Content with only separators produces no sections

    def test_content_with_only_separators(self, parser: SectionParser):
        """Test content containing only separator patterns."""
        content_only_v = "---\n---\n---"
        sections_v = parser.parse_sections(content_only_v)
        # Current implementation preserves this as content
        assert len(sections_v) == 1
        assert sections_v[0].content == content_only_v

        content_only_h = "***\n***"
        sections_h = parser.parse_sections(content_only_h)
        assert len(sections_h) == 1
        assert sections_h[0].content == content_only_h

    # ========================================================================
    # ID Generation and Structure Tests
    # ========================================================================

    def test_unique_ids_generated(self, parser: SectionParser):
        """Test that unique IDs are generated for all sections."""
        content = """Section A
---
Section B1
***
Section B2
---
Section C"""

        sections = parser.parse_sections(content)

        # Collect all IDs
        all_ids = set()
        for section in sections:
            all_ids.add(section.id)
            if section.subsections:
                for subsection in section.subsections:
                    all_ids.add(subsection.id)

        # Should have 5 unique IDs (A, row wrapper, B1, B2, C)
        assert len(all_ids) == 5

        # All IDs should be non-None and non-empty
        for section_id in all_ids:
            assert section_id is not None
            assert section_id != ""

    def test_section_hierarchy_structure(self, parser: SectionParser):
        """Test proper section hierarchy structure."""
        content = """Top level
---
Row section left
***
Row section right
---
Another top level"""

        sections = parser.parse_sections(content)
        assert len(sections) == 3

        # First: simple section
        assert sections[0].type == "section"
        assert sections[0].subsections == []
        assert sections[0].elements == []

        # Second: row section
        assert sections[1].type == "row"
        assert len(sections[1].subsections) == 2
        assert sections[1].elements == []  # Row sections don't have direct elements

        # Subsections of row
        for subsection in sections[1].subsections:
            assert subsection.type == "section"
            assert subsection.subsections == []
            assert subsection.elements == []

        # Third: simple section
        assert sections[2].type == "section"
        assert sections[2].subsections == []

    # ========================================================================
    # Complex Content Structure Tests
    # ========================================================================

    def test_complex_nested_structure_preservation(self, parser: SectionParser):
        """Test preservation of complex nested content structures."""
        content = """[layout=hero]
# Main Title
[subtitle=true]
## Subtitle here

Main content paragraph.

---

[layout=two-column]
### Left Column Header
[width=60%][padding=20px]
Left column content with **formatting**.

* List item 1
* List item 2

```python
def example():
    return "code"
```

***

### Right Column Header
[width=40%][align=center]
Right column content.

> This is a blockquote
> with multiple lines.

| Table | Header |
|-------|--------|
| Cell  | Data   |

---

[layout=footer]
## Footer Section
[background=dark][color=white]
Footer content here."""

        sections = parser.parse_sections(content)
        assert len(sections) == 3

        # First section: hero layout
        hero_section = sections[0]
        assert hero_section.type == "section"
        assert "[layout=hero]" in hero_section.content
        assert "# Main Title" in hero_section.content
        assert "## Subtitle here" in hero_section.content
        assert "Main content paragraph." in hero_section.content

        # Second section: two-column row
        column_section = sections[1]
        assert column_section.type == "row"
        assert len(column_section.subsections) == 2

        left_col = column_section.subsections[0]
        assert "### Left Column Header" in left_col.content
        assert "[width=60%][padding=20px]" in left_col.content
        assert "* List item 1" in left_col.content
        assert "def example():" in left_col.content

        right_col = column_section.subsections[1]
        assert "### Right Column Header" in right_col.content
        assert "[width=40%][align=center]" in right_col.content
        assert "> This is a blockquote" in right_col.content
        assert "| Table | Header |" in right_col.content

        # Third section: footer
        footer_section = sections[2]
        assert footer_section.type == "section"
        assert "[layout=footer]" in footer_section.content
        assert "[background=dark][color=white]" in footer_section.content

    def test_section_with_only_directives_no_content(self, parser: SectionParser):
        """Test section that contains only directives."""
        content = """[width=100%][height=100%][background=blue]
---
Some actual content here."""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        # First section has only directives
        first_section = sections[0]
        assert first_section.content == "[width=100%][height=100%][background=blue]"

        # Second section has content
        second_section = sections[1]
        assert "Some actual content here." in second_section.content

    def test_whitespace_handling_around_separators(self, parser: SectionParser):
        """Test proper whitespace handling around separators."""
        content = """   Section A content

---

   Section B content
   with multiple lines

---

   Section C content   """

        sections = parser.parse_sections(content)
        assert len(sections) == 3

        # Content should be preserved but trimmed appropriately
        assert "Section A content" in sections[0].content
        assert "Section B content" in sections[1].content
        assert "with multiple lines" in sections[1].content
        assert "Section C content" in sections[2].content

    # ========================================================================
    # Error Handling and Robustness Tests
    # ========================================================================

    def test_malformed_separator_patterns(self, parser: SectionParser):
        """Test handling of malformed separator patterns."""
        content = """Section A
-- (incomplete)
Section B
---- (too many)
Section C
****** (way too many)
Section D"""

        sections = parser.parse_sections(content)
        # Malformed separators should be treated as content
        assert len(sections) == 1
        assert "Section A" in sections[0].content
        assert "-- (incomplete)" in sections[0].content
        assert "---- (too many)" in sections[0].content
        assert "****** (way too many)" in sections[0].content
        assert "Section D" in sections[0].content

    def test_mixed_line_endings_handling(self, parser: SectionParser):
        """Test handling of mixed line endings."""
        content = "Section A\r\n---\r\nSection B\n***\nSection C\r\n"
        sections = parser.parse_sections(content)

        # Should handle mixed line endings gracefully
        assert len(sections) == 2
        assert sections[1].type == "row"
        assert len(sections[1].subsections) == 2

    def test_very_long_content_handling(self, parser: SectionParser):
        """Test handling of very long content sections."""
        # Create long content
        long_paragraph = "This is a very long paragraph. " * 100
        content = f"""[config=large]
{long_paragraph}

---

[config=another]
Another section with long content.
{long_paragraph}"""

        sections = parser.parse_sections(content)
        assert len(sections) == 2

        # Content should be preserved completely - use more robust assertion
        # that accounts for leading directives in the raw content
        assert long_paragraph.strip() in sections[0].content
        assert long_paragraph.strip() in sections[1].content
        assert "[config=large]" in sections[0].content
        assert "[config=another]" in sections[1].content
