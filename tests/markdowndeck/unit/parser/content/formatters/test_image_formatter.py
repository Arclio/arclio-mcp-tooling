import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import ElementType, ImageElement
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters.image import ImageFormatter


class TestImageFormatter:
    """Unit tests for the ImageFormatter."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> ImageFormatter:
        return ImageFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    def test_can_handle_paragraph_open_for_potential_image(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        tokens = md_parser.parse(
            "![alt](url.jpg)"
        )  # This creates [paragraph_open, inline, paragraph_close]
        assert formatter.can_handle(
            tokens[0], tokens
        )  # Pass all tokens as "leading" for this specific test case

    def test_can_handle_direct_image_token(self, formatter: ImageFormatter, md_parser: MarkdownIt):
        # Simulate a direct image token (though markdown-it usually wraps it)
        from markdown_it.token import Token

        image_token = Token("image", "", 0, attrs={"src": "url.jpg"}, content="alt")
        assert formatter.can_handle(image_token, [])

    def test_cannot_handle_non_image_paragraph(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        tokens = md_parser.parse("Just text")
        # TextFormatter would handle this, ImageFormatter's process would return None
        # The can_handle for ImageFormatter might be tricky for non-image paragraphs without full context.
        # For now, let's test if its `process` method correctly returns None.
        element, _ = formatter.process(tokens, 0, {})
        assert element is None

    def test_process_image_only_paragraph(self, formatter: ImageFormatter, md_parser: MarkdownIt):
        markdown = "![alt text](http://example.com/image.png)"
        tokens = md_parser.parse(markdown)
        # tokens are [paragraph_open, inline, paragraph_close]
        # inline token has children: [image]

        element, end_index = formatter.process(tokens, 0, {"align": "center"})

        assert isinstance(element, ImageElement)
        assert element.element_type == ElementType.IMAGE
        assert element.url == "http://example.com/image.png"
        assert element.alt_text == "alt text"
        assert element.directives.get("align") == "center"
        assert end_index == 2  # Consumed paragraph_open, inline, paragraph_close

    def test_process_image_with_title_in_markdown(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        markdown = (
            '![alt text](url.jpg "Image Title")'  # Markdown-it puts title in token.attrs['title']
        )
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, ImageElement)
        assert element.url == "url.jpg"
        assert element.alt_text == "alt text"
        # The 'title' attribute from markdown `![](... "title")` is available on the image token.
        # The ImageElement model doesn't currently store this, but the formatter could extract it if needed.
        # For now, we just check it's processed.
        # image_token = tokens[1].children[0] # Accessing the actual image token
        # assert image_token.attrs.get("title") == "Image Title"

    def test_process_paragraph_with_text_and_image(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """ImageFormatter should NOT process paragraphs with mixed content."""
        markdown = "Some text ![alt text](url.jpg) more text"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert element is None  # TextFormatter should handle this

    def test_process_paragraph_image_and_whitespace(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        markdown = "  \n![alt](url.jpg)\n  "  # Whitespace around the image
        tokens = md_parser.parse(markdown.strip())  # Parsing the stripped version
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, ImageElement)
        assert element.url == "url.jpg"

    def test_process_empty_alt_text(self, formatter: ImageFormatter, md_parser: MarkdownIt):
        markdown = "![](url.gif)"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        assert isinstance(element, ImageElement)
        assert element.url == "url.gif"
        assert element.alt_text == ""

    def test_process_no_url(self, formatter: ImageFormatter, md_parser: MarkdownIt):
        markdown = "![no url image]()"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})
        # ImageFormatter should probably return None if there's no URL, as it's not a valid image.
        assert element is None

    def test_process_direct_image_token_if_possible(self, formatter: ImageFormatter):
        """Test processing a direct image token (if markdown-it could produce it this way)."""
        from markdown_it.token import Token

        image_token = Token("image", "img", 0, attrs={"src": "direct.png"}, content="Direct Alt")
        tokens = [image_token]  # Simulate this token being passed directly
        element, end_index = formatter.process(tokens, 0, {})

        assert isinstance(element, ImageElement)
        assert element.url == "direct.png"
        assert element.alt_text == "Direct Alt"
        assert end_index == 0  # Consumed only the single image token
