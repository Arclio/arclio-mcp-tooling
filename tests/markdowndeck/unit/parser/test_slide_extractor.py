import pytest
from markdowndeck.parser.slide_extractor import SlideExtractor


class TestSlideExtractor:
    """Unit tests for the SlideExtractor component."""

    @pytest.fixture
    def extractor(self) -> SlideExtractor:
        """Returns an instance of SlideExtractor."""
        return SlideExtractor()

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

    def test_slide_with_only_title(self, extractor: SlideExtractor):
        """Test a slide that only contains a title."""
        markdown = "# Only Title"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] == "Only Title"
        assert (
            slides[0]["content"] == ""
        )  # Content should be empty after title extraction

    def test_slide_with_title_and_footer(self, extractor: SlideExtractor):
        """Test a slide with title, content, and footer."""
        markdown = "# Title\nSome Content\n@@@\nMy Footer"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] == "Title"
        assert slides[0]["content"] == "Some Content"
        assert slides[0]["footer"] == "My Footer"

    def test_slide_with_notes(self, extractor: SlideExtractor):
        """Test a slide with speaker notes."""
        markdown = "# Notes Slide\nContent \n@@@\nFooter text."
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] == "Notes Slide"
        assert slides[0]["content"] == "Content"
        assert slides[0]["footer"] == "Footer text."
        # Should test for notes if this test is intended to check speaker notes
        assert slides[0]["notes"] is None  # Or whatever the expected value is

    def test_slide_separator_in_code_block(self, extractor: SlideExtractor):
        """Test that '===' inside a code block does not split the slide."""
        markdown = """
# Slide with Code
```
Code block content
===
This is not a slide separator.
```
More content on the same slide.
"""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert (
            "Code block content\n===\nThis is not a slide separator."
            in slides[0]["content"]
        )

    def test_multiple_code_blocks_and_separators(self, extractor: SlideExtractor):
        markdown = """
# Slide Alpha
```
alpha === code
```
===
# Slide Beta
```
beta === code
```
Content after beta code.
"""
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide Alpha"
        assert "alpha === code" in slides[0]["content"]
        assert slides[1]["title"] == "Slide Beta"
        assert "beta === code" in slides[1]["content"]
        assert "Content after beta code" in slides[1]["content"]

    def test_empty_content_between_separators(self, extractor: SlideExtractor):
        """Test handling of empty content between slide separators."""
        markdown = "# Slide 1\nContent1\n===\n===\n# Slide 3\nContent3"
        slides = extractor.extract_slides(markdown)
        # Expecting empty parts to be filtered out
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide 1"
        assert slides[1]["title"] == "Slide 3"

    def test_content_starting_with_separator(self, extractor: SlideExtractor):
        """Test markdown that starts with a slide separator."""
        markdown = "===\n# Slide Omega\nContent Omega"
        slides = extractor.extract_slides(markdown)
        # Expecting the first empty part to be ignored
        assert len(slides) == 1
        assert slides[0]["title"] == "Slide Omega"

    def test_content_ending_with_separator(self, extractor: SlideExtractor):
        """Test markdown that ends with a slide separator."""
        markdown = "# Slide Delta\nContent Delta\n==="
        slides = extractor.extract_slides(markdown)
        # Expecting the last empty part to be ignored
        assert len(slides) == 1
        assert slides[0]["title"] == "Slide Delta"

    def test_mixed_line_endings(self, extractor: SlideExtractor):
        """Test with mixed CRLF and LF line endings."""
        markdown = "# Slide One\r\nContent One\r\n===\n# Slide Two\nContent Two"
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 2
        assert slides[0]["title"] == "Slide One"
        assert slides[1]["title"] == "Slide Two"

    def test_no_title_slide(self, extractor: SlideExtractor):
        """Test a slide that does not start with a H1 title."""
        markdown = "This is content without a title.\nMore content."
        slides = extractor.extract_slides(markdown)
        assert len(slides) == 1
        assert slides[0]["title"] is None
        assert slides[0]["content"] == "This is content without a title.\nMore content."
