import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import (
    AlignmentType,
    CodeElement,
    ElementType,
    ImageElement,
    ListElement,
    ListItem,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
    VerticalAlignmentType,
)
from markdowndeck.parser.content.element_factory import ElementFactory


class TestElementFactory:
    """Unit tests for the ElementFactory."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        # Basic markdown-it parser for formatting extraction tests
        md = MarkdownIt()
        md.enable("strikethrough")  # Ensure s_open/s_close tokens are generated
        return md

    def test_create_title_element(self, factory: ElementFactory):
        formatting = [TextFormat(0, 5, TextFormatType.BOLD)]
        el = factory.create_title_element("Title", formatting)
        assert isinstance(el, TextElement)
        assert el.element_type == ElementType.TITLE
        assert el.text == "Title"
        assert el.formatting == formatting
        assert el.horizontal_alignment == AlignmentType.CENTER

    def test_create_subtitle_element(self, factory: ElementFactory):
        el = factory.create_subtitle_element("Subtitle", alignment=AlignmentType.RIGHT)
        assert isinstance(el, TextElement)
        assert el.element_type == ElementType.SUBTITLE
        assert el.text == "Subtitle"
        assert el.horizontal_alignment == AlignmentType.RIGHT

    def test_create_text_element(self, factory: ElementFactory):
        directives = {"custom": "value"}
        el = factory.create_text_element("Some text", directives=directives)
        assert isinstance(el, TextElement)
        assert el.element_type == ElementType.TEXT
        assert el.text == "Some text"
        assert el.horizontal_alignment == AlignmentType.LEFT
        assert el.directives == directives

    def test_create_quote_element(self, factory: ElementFactory):
        el = factory.create_quote_element("A quote.", alignment=AlignmentType.CENTER)
        assert isinstance(el, TextElement)
        assert el.element_type == ElementType.QUOTE
        assert el.text == "A quote."
        assert el.horizontal_alignment == AlignmentType.CENTER

    def test_create_footer_element(self, factory: ElementFactory):
        el = factory.create_footer_element("Footer text")
        assert isinstance(el, TextElement)
        assert el.element_type == ElementType.FOOTER
        assert el.text == "Footer text"
        assert el.vertical_alignment == VerticalAlignmentType.BOTTOM

    def test_create_list_element(self, factory: ElementFactory):
        items = [ListItem(text="Item 1")]
        el_bullet = factory.create_list_element(items, ordered=False)
        assert isinstance(el_bullet, ListElement)
        assert el_bullet.element_type == ElementType.BULLET_LIST
        assert el_bullet.items == items

        el_ordered = factory.create_list_element(items, ordered=True)
        assert isinstance(el_ordered, ListElement)
        assert el_ordered.element_type == ElementType.ORDERED_LIST

    def test_create_image_element(self, factory: ElementFactory):
        el = factory.create_image_element(
            "url.jpg", "Alt", directives={"align": "center"}
        )
        assert isinstance(el, ImageElement)
        assert el.element_type == ElementType.IMAGE
        assert el.url == "url.jpg"
        assert el.alt_text == "Alt"
        assert el.directives == {"align": "center"}

    def test_create_table_element(self, factory: ElementFactory):
        headers = ["H1", "H2"]
        rows = [["R1C1", "R1C2"]]
        el = factory.create_table_element(headers, rows)
        assert isinstance(el, TableElement)
        assert el.element_type == ElementType.TABLE
        assert el.headers == headers
        assert el.rows == rows

    def test_create_code_element(self, factory: ElementFactory):
        el = factory.create_code_element("print('hi')", "python")
        assert isinstance(el, CodeElement)
        assert el.element_type == ElementType.CODE
        assert el.code == "print('hi')"
        assert el.language == "python"

    @pytest.mark.parametrize(
        ("markdown_text", "expected_formats"),
        [
            ("simple text", []),
            (
                "**bold** text",
                [
                    TextFormat(
                        start=0, end=4, format_type=TextFormatType.BOLD, value=True
                    )
                ],
            ),
            (
                "*italic* text",
                [
                    TextFormat(
                        start=0, end=6, format_type=TextFormatType.ITALIC, value=True
                    )
                ],
            ),
            (
                "`code` text",
                [
                    TextFormat(
                        start=0, end=4, format_type=TextFormatType.CODE, value=True
                    )
                ],
            ),
            (
                "~~strike~~ text",
                [
                    TextFormat(
                        start=0,
                        end=6,
                        format_type=TextFormatType.STRIKETHROUGH,
                        value=True,
                    )
                ],
            ),
            (
                "[link](http://example.com)",
                [
                    TextFormat(
                        start=0,
                        end=4,
                        format_type=TextFormatType.LINK,
                        value="http://example.com",
                    )
                ],
            ),
            (
                "**bold *italic* link**",
                [  # Order might vary based on parser's internal logic for nested, check presence and ranges
                    TextFormat(
                        start=5, end=11, format_type=TextFormatType.ITALIC, value=True
                    ),
                    TextFormat(
                        start=0, end=17, format_type=TextFormatType.BOLD, value=True
                    ),
                ],
            ),
            (
                "text **bold** and *italic*",
                [
                    TextFormat(
                        start=5, end=9, format_type=TextFormatType.BOLD, value=True
                    ),
                    TextFormat(
                        start=14, end=20, format_type=TextFormatType.ITALIC, value=True
                    ),
                ],
            ),
            (
                "text at start **bold**",
                [
                    TextFormat(
                        start=13, end=17, format_type=TextFormatType.BOLD, value=True
                    )
                ],
            ),
            (
                "**bold** text at end",
                [
                    TextFormat(
                        start=0, end=4, format_type=TextFormatType.BOLD, value=True
                    )
                ],
            ),
        ],
    )
    def test_extract_formatting_from_text(
        self,
        factory: ElementFactory,
        md_parser: MarkdownIt,
        markdown_text: str,
        expected_formats: list[TextFormat],
    ):
        """Test extraction of formatting from a simple text string."""
        extracted = factory.extract_formatting_from_text(markdown_text, md_parser)

        # Sort both lists of dataclasses by start index for consistent comparison
        sorted_extracted = sorted(
            extracted, key=lambda f: (f.start, f.end, f.format_type.value)
        )
        sorted_expected = sorted(
            expected_formats, key=lambda f: (f.start, f.end, f.format_type.value)
        )

        assert (
            sorted_extracted == sorted_expected
        ), f"Formatting mismatch for: {markdown_text}"

    def test_extract_formatting_empty_text(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        assert factory.extract_formatting_from_text("", md_parser) == []
        assert (
            factory.extract_formatting_from_text("   ", md_parser) == []
        )  # Whitespace only
