import pytest
from markdowndeck.parser.slide_extractor import SlideExtractor


class TestSlideExtractor:
    """Tests for the SlideExtractor component."""

    @pytest.fixture
    def extractor(self):
        """Create a slide extractor for testing."""
        return SlideExtractor()

    def test_extract_basic_slides(self, extractor):
        """Test extraction of basic slides separated by '==='."""
        markdown = """
        # Slide 1

        Content for slide 1

        ===

        # Slide 2

        Content for slide 2
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 2
        assert slides[0]["title"] == "Slide 1"
        assert "Content for slide 1" in slides[0]["content"]
        assert slides[1]["title"] == "Slide 2"
        assert "Content for slide 2" in slides[1]["content"]

    def test_extract_slides_with_footer(self, extractor):
        """Test extraction of slides with footers separated by '@@@'."""
        markdown = """
        # Slide With Footer

        Content

        @@@

        This is a footer
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 1
        assert slides[0]["title"] == "Slide With Footer"
        assert "Content" in slides[0]["content"]
        assert slides[0]["footer"] == "This is a footer"

    def test_extract_slides_with_notes(self, extractor):
        """Test extraction of slides with speaker notes in HTML comments."""
        markdown = """
        # Slide With Notes

        Content

        <!-- notes: These are speaker notes -->
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 1
        assert slides[0]["title"] == "Slide With Notes"
        assert slides[0]["notes"] == "These are speaker notes"
        assert "<!-- notes:" not in slides[0]["content"]

    def test_extract_slides_with_background(self, extractor):
        """Test extraction of slides with background directives."""
        markdown = """
        # Slide With Background

        [background=#f5f5f5]
        Content with gray background
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 1
        assert slides[0]["title"] == "Slide With Background"
        assert slides[0]["background"] is not None
        assert slides[0]["background"]["type"] == "color"
        assert slides[0]["background"]["value"] == "#f5f5f5"

    def test_extract_slides_with_background_image(self, extractor):
        """Test extraction of slides with image background directives."""
        markdown = """
        # Slide With Image Background

        [background=url(https://example.com/image.jpg)]
        Content with image background
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 1
        assert slides[0]["title"] == "Slide With Image Background"
        assert slides[0]["background"] is not None
        assert slides[0]["background"]["type"] == "image"
        assert slides[0]["background"]["value"] == "https://example.com/image.jpg"

    def test_extract_slides_with_complex_content(self, extractor):
        """Test extraction of slides with complex content including all features."""
        markdown = """
        # Complex Slide

        [background=#e6f7ff]
        Main content with **formatting**

        ```python
        def hello():
            print("Hello world")
        ```

        <!-- notes: Remember to explain the code -->

        @@@

        Slide footer with reference

        ===

        # Another Slide

        Second slide content
        """

        slides = extractor.extract_slides(markdown)

        assert len(slides) == 2

        # Check first slide
        assert slides[0]["title"] == "Complex Slide"
        assert slides[0]["background"]["value"] == "#e6f7ff"
        assert "Main content with **formatting**" in slides[0]["content"]
        assert "```python" in slides[0]["content"]
        assert slides[0]["notes"] == "Remember to explain the code"
        assert slides[0]["footer"] == "Slide footer with reference"

        # Check second slide
        assert slides[1]["title"] == "Another Slide"
        assert "Second slide content" in slides[1]["content"]
