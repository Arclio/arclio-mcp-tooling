"""Updated unit tests for the SlideExtractor with enhanced title handling."""

import pytest
from markdowndeck.parser.slide_extractor import SlideExtractor


class TestSlideExtractor:
    """Updated unit tests for the SlideExtractor component."""

    @pytest.fixture
    def extractor(self) -> SlideExtractor:
        """Returns an instance of SlideExtractor."""
        return SlideExtractor()

    # ========================================================================
    # Basic Functionality Tests (Updated)
    # ========================================================================

    def test_extract_empty_markdown(self, extractor: SlideExtractor):
        """Test that empty markdown results in no slides."""
        slides = extractor.extract_slides("")
        assert len(slides) == 0

    def test_extract_single_slide_no_separator(self, extractor: SlideExtractor):
        """Test markdown with no '===' separator results in a single slide."""
        markdown = "# Slide One\nContent of slide one."
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] == "Slide One"
        assert slides[0]["content"] == "Content of slide one."
        assert slides[0]["index"] == 0

    def test_extract_multiple_slides(self, extractor: SlideExtractor):
        """Test basic slide splitting with '==='."""
        markdown = "# Slide 1\nContent1\n===\n# Slide 2\nContent2"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide 1"
        assert slides[0]["content"] == "Content1"
        assert slides[0]["index"] == 0
        assert slides[1]["title"] == "Slide 2"
        assert slides[1]["content"] == "Content2"
        assert slides[1]["index"] == 1

    def test_separator_with_varying_whitespace(self, extractor: SlideExtractor):
        """Test '===' separators with surrounding whitespace."""
        markdown = "# Slide A\nContentA\n  ===  \n# Slide B\nContentB"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide A"
        assert slides[1]["title"] == "Slide B"

    # ========================================================================
    # P3: Enhanced Title Handling Tests
    # ========================================================================

    def test_indented_title_extraction_and_removal(self, extractor: SlideExtractor):
        """Test extraction and removal of indented titles (P3 fix)."""
        markdown = """   #   Indented Title
Some content here.
More content."""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1

        slide = slides[0]
        assert slide["title"] == "Indented Title"
        assert slide["content"] == "Some content here.\nMore content."
        # Verify title line is completely removed
        assert "Indented Title" not in slide["content"]
        assert "#" not in slide["content"]

    def test_title_with_directives_extraction(self, extractor: SlideExtractor):
        """Test extraction of titles with directives."""
        markdown = """# [align=center][fontsize=24][color=blue]My Styled Title
Content here."""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1

        slide = slides[0]
        assert slide["title"] == "My Styled Title"
        assert slide["title_directives"]["align"] == "center"
        assert slide["title_directives"]["fontsize"] == 24.0
        assert slide["title_directives"]["color"] == {"type": "named", "value": "blue"}
        assert slide["content"] == "Content here."

    def test_title_with_directives_and_spaces(self, extractor: SlideExtractor):
        """Test title with directives and various spacing."""
        markdown = """#   [align=left]  [fontsize=18]   Spaced Title
Content after title."""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1

        slide = slides[0]
        assert slide["title"] == "Spaced Title"
        assert slide["title_directives"]["align"] == "left"
        assert slide["title_directives"]["fontsize"] == 18.0
        assert slide["content"] == "Content after title."

    def test_indented_title_with_directives(self, extractor: SlideExtractor):
        """Test indented title with directives (combined P3 and title directive features)."""
        markdown = """    # [color=red][align=right] Indented Styled Title
Some content.
More content."""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1

        slide = slides[0]
        assert slide["title"] == "Indented Styled Title"
        assert slide["title_directives"]["color"] == {"type": "named", "value": "red"}
        assert slide["title_directives"]["align"] == "right"
        # Content should not contain the title line
        assert "Indented Styled Title" not in slide["content"]
        assert slide["content"] == "Some content.\nMore content."

    def test_title_directive_edge_cases(self, extractor: SlideExtractor):
        """Test edge cases in title directive parsing."""
        # Empty directive values
        markdown1 = """# [align=][color=blue] Title With Empty Directive
Content"""
        slides1 = extractor.extract_slides(markdown1)
        assert slides1[0]["title"] == "Title With Empty Directive"
        assert slides1[0]["title_directives"]["align"] == ""
        assert slides1[0]["title_directives"]["color"] == {
            "type": "named",
            "value": "blue",
        }

        # Invalid directive format (should be ignored)
        markdown2 = """# [invalid:value][valid=good] Title With Mixed Directives
Content"""
        slides2 = extractor.extract_slides(markdown2)
        assert slides2[0]["title"] == "[invalid:value][valid=good] Title With Mixed Directives"
        # When there's an invalid directive format, entire directive parsing fails
        assert slides2[0]["title_directives"] == {}

    def test_no_title_slide(self, extractor: SlideExtractor):
        """Test a slide that does not start with a H1 title."""
        markdown = "This is content without a title.\nMore content."
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] is None
        assert slides[0]["title_directives"] == {}
        assert slides[0]["content"] == "This is content without a title.\nMore content."

    # ========================================================================
    # P7: Enhanced Code Fence Detection Tests
    # ========================================================================

    def test_slide_separator_in_various_code_blocks(self, extractor: SlideExtractor):
        """Test that '===' inside various code block types does not split slides (P7 enhancement)."""
        markdown = """# Slide with Multiple Code Blocks
```
Regular code with ===
```

````json
{
  "separator": "==="
}
````

~~~text
Text block with ===
~~~

More content.
===
# Second Slide
Content of second slide."""

        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2

        # First slide should contain all code blocks
        slide1 = slides[0]
        assert slide1["title"] == "Slide with Multiple Code Blocks"
        assert "Regular code with ===" in slide1["content"]
        assert '"separator": "==="' in slide1["content"]
        assert "Text block with ===" in slide1["content"]
        assert "More content." in slide1["content"]

        # Second slide
        slide2 = slides[1]
        assert slide2["title"] == "Second Slide"
        assert slide2["content"] == "Content of second slide."

    def test_nested_code_fence_types(self, extractor: SlideExtractor):
        """Test handling of different code fence types within one slide."""
        markdown = """# Code Fence Test
````markdown
```python
print("nested")
```
````
===
# Next Slide
Regular content."""

        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2

        slide1 = slides[0]
        assert 'print("nested")' in slide1["content"]
        assert slide1["title"] == "Code Fence Test"

    def test_code_fence_edge_cases(self, extractor: SlideExtractor):
        """Test edge cases in code fence detection."""
        # Mismatched fence types should not close
        markdown1 = """# Fence Mismatch
```
Code starts with triple backticks
~~~
This should still be in the code block
```
Content after code."""

        slides1 = extractor.extract_slides(markdown1)
        assert len(slides1) == 1
        content = slides1[0]["content"]
        assert "Code starts with triple backticks" in content
        assert "This should still be in the code block" in content

        # Code fence at end of slide
        markdown2 = """# Code at End
Some content
```
Code block
```"""
        slides2 = extractor.extract_slides(markdown2)
        assert len(slides2) == 1
        assert "Code block" in slides2[0]["content"]

    # ========================================================================
    # Footer, Notes, and Background Tests (Enhanced)
    # ========================================================================

    def test_slide_with_title_footer_and_directives(self, extractor: SlideExtractor):
        """Test comprehensive slide with title directives, footer, etc."""
        markdown = """# [align=center][color=blue]Comprehensive Slide
[background=#f0f0f0]
Main content here.
@@@
Footer content
<!-- notes: Speaker notes here -->"""

        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1

        slide = slides[0]
        assert slide["title"] == "Comprehensive Slide"
        assert slide["title_directives"]["align"] == "center"
        assert slide["title_directives"]["color"] == {"type": "named", "value": "blue"}
        # Background is no longer specially handled by SlideExtractor
        assert slide["background"] is None
        assert slide["footer"] == "Footer content"
        assert slide["notes"] == "Speaker notes here"
        # Background directive should remain in content for DirectiveParser
        assert "[background=#f0f0f0]" in slide["content"]

    def test_notes_in_footer_override_content_notes(self, extractor: SlideExtractor):
        """Test that notes in footer override notes in content."""
        markdown = """# Notes Test
Content with <!-- notes: Content notes -->
@@@
Footer text
<!-- notes: Footer notes -->"""

        slides = extractor.extract_slides(markdown)
        slide = slides[0]

        assert slide["notes"] == "Footer notes"  # Footer notes take precedence
        assert slide["footer"] == "Footer text"  # Notes removed from footer text
        # Content notes should be removed from content
        assert "<!-- notes: Content notes -->" not in slide["content"]

    def test_background_url_parsing(self, extractor: SlideExtractor):
        """Test background URL parsing with validation."""
        # Valid URL - background should remain in content for DirectiveParser
        markdown1 = """# Background Test
[background=url(https://example.com/image.jpg)]
Content"""
        slides1 = extractor.extract_slides(markdown1)
        # SlideExtractor no longer processes backgrounds
        assert slides1[0]["background"] is None
        # Background directive should remain in content
        assert "[background=url(https://example.com/image.jpg)]" in slides1[0]["content"]

        # Invalid URL should also remain in content for DirectiveParser to handle
        markdown2 = """# Invalid Background
[background=url(invalid-url)]
Content"""
        slides2 = extractor.extract_slides(markdown2)
        assert slides2[0]["background"] is None
        assert "[background=url(invalid-url)]" in slides2[0]["content"]

    # ========================================================================
    # Edge Cases and Error Handling
    # ========================================================================

    def test_empty_slides_filtered(self, extractor: SlideExtractor):
        """Test that empty slides are properly filtered."""
        markdown = """# First Slide
Content
===

===

===
# Last Slide
More content"""

        slides = extractor.extract_slides(markdown)
        # Should only have 2 slides (empty ones filtered)
        assert len(slides) == 2
        assert slides[0]["title"] == "First Slide"
        assert slides[1]["title"] == "Last Slide"

    def test_slide_with_only_footer(self, extractor: SlideExtractor):
        """Test slide that only contains footer."""
        markdown = "@@@\nJust a footer"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] is None
        assert slides[0]["content"] == ""
        assert slides[0]["footer"] == "Just a footer"

    def test_slide_with_only_notes(self, extractor: SlideExtractor):
        """Test slide that only contains notes."""
        markdown = "<!-- notes: Just notes -->"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] is None
        assert slides[0]["content"] == ""
        assert slides[0]["notes"] == "Just notes"

    def test_slide_with_only_background(self, extractor: SlideExtractor):
        """Test slide that only contains background directive."""
        markdown = "[background=#FF0000]"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] is None
        # Background directive should remain in content for DirectiveParser
        assert slides[0]["content"] == "[background=#FF0000]"
        # SlideExtractor no longer processes backgrounds
        assert slides[0]["background"] is None

    def test_mixed_line_endings_with_directives(self, extractor: SlideExtractor):
        """Test mixed line endings with title directives."""
        markdown = "# [align=left]Slide One\r\nContent One\r\n===\n# [align=right]Slide Two\nContent Two"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide One"
        assert slides[0]["title_directives"]["align"] == "left"
        assert slides[1]["title"] == "Slide Two"
        assert slides[1]["title_directives"]["align"] == "right"

    def test_complex_title_removal_scenarios(self, extractor: SlideExtractor):
        """Test complex title removal scenarios."""
        # Multiple spaces and tabs
        markdown1 = """	  #   	Weird Spacing Title
Content here."""
        slides1 = extractor.extract_slides(markdown1)
        assert slides1[0]["title"] == "Weird Spacing Title"
        assert slides1[0]["content"] == "Content here."

        # Title with special characters
        markdown2 = """# Title with "quotes" and 'apostrophes' & symbols!
Content below."""
        slides2 = extractor.extract_slides(markdown2)
        assert slides2[0]["title"] == "Title with \"quotes\" and 'apostrophes' & symbols!"
        assert slides2[0]["content"] == "Content below."

    def test_title_directive_invalid_values(self, extractor: SlideExtractor):
        """Test handling of invalid directive values in titles."""
        markdown = """# [fontsize=invalid][color=][align=bad] Title With Invalid Directives
Content"""
        slides = extractor.extract_slides(markdown)
        slide = slides[0]

        assert slide["title"] == "Title With Invalid Directives"
        # Invalid fontsize should be skipped or handled gracefully
        assert "fontsize" not in slide["title_directives"] or slide["title_directives"]["fontsize"] == "invalid"
        # Empty color should be preserved as structured value
        assert slide["title_directives"]["color"] == {"type": "named", "value": ""}
        # Invalid align should be preserved as-is
        assert slide["title_directives"]["align"] == "bad"

    def test_slide_object_id_generation(self, extractor: SlideExtractor):
        """Test that slide object IDs are properly generated."""
        markdown = """# Slide 1
Content 1
===
# Slide 2
Content 2"""

        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2

        # Check object IDs are unique and properly formatted
        assert slides[0]["object_id"].startswith("slide_0_")
        assert slides[1]["object_id"].startswith("slide_1_")
        assert slides[0]["object_id"] != slides[1]["object_id"]

        # Check speaker notes object IDs are None when no notes
        assert slides[0]["speaker_notes_object_id"] is None
        assert slides[1]["speaker_notes_object_id"] is None

    def test_speaker_notes_object_id_generation(self, extractor: SlideExtractor):
        """Test speaker notes object ID generation."""
        markdown = """# Slide With Notes
Content
<!-- notes: Some notes -->"""

        slides = extractor.extract_slides(markdown)
        slide = slides[0]

        assert slide["notes"] == "Some notes"
        assert slide["speaker_notes_object_id"] is not None
        assert slide["speaker_notes_object_id"].endswith("_notesShape")
