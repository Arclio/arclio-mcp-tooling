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
        el = factory.create_image_element("url.jpg", "Alt", directives={"align": "center"})
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
                [TextFormat(start=0, end=4, format_type=TextFormatType.BOLD, value=True)],
            ),
            (
                "*italic* text",
                [TextFormat(start=0, end=6, format_type=TextFormatType.ITALIC, value=True)],
            ),
            (
                "`code` text",
                [TextFormat(start=0, end=4, format_type=TextFormatType.CODE, value=True)],
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
                    TextFormat(start=5, end=11, format_type=TextFormatType.ITALIC, value=True),
                    TextFormat(start=0, end=17, format_type=TextFormatType.BOLD, value=True),
                ],
            ),
            (
                "text **bold** and *italic*",
                [
                    TextFormat(start=5, end=9, format_type=TextFormatType.BOLD, value=True),
                    TextFormat(start=14, end=20, format_type=TextFormatType.ITALIC, value=True),
                ],
            ),
            (
                "text at start **bold**",
                [TextFormat(start=13, end=17, format_type=TextFormatType.BOLD, value=True)],
            ),
            (
                "**bold** text at end",
                [TextFormat(start=0, end=4, format_type=TextFormatType.BOLD, value=True)],
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
        sorted_extracted = sorted(extracted, key=lambda f: (f.start, f.end, f.format_type.value))
        sorted_expected = sorted(expected_formats, key=lambda f: (f.start, f.end, f.format_type.value))

        assert sorted_extracted == sorted_expected, f"Formatting mismatch for: {markdown_text}"

    def test_extract_formatting_empty_text(self, factory: ElementFactory, md_parser: MarkdownIt):
        assert factory.extract_formatting_from_text("", md_parser) == []
        assert factory.extract_formatting_from_text("   ", md_parser) == []  # Whitespace only

    def test_strip_directives_from_code_content(self, factory: ElementFactory):
        """Test that directive patterns are stripped from code content."""
        # Test with directive prefix
        result = factory._strip_directives_from_code_content("[border=solid][padding=10px] GET endpoints equivalent")
        assert result == "GET endpoints equivalent"

        # Test with multiple directives
        result = factory._strip_directives_from_code_content("[align=center] [width=100%] code content")
        assert result == "code content"

        # Test with no directives
        result = factory._strip_directives_from_code_content("normal code content")
        assert result == "normal code content"

        # Test with empty content
        result = factory._strip_directives_from_code_content("")
        assert result == ""

        # Test with only directives (should return empty)
        result = factory._strip_directives_from_code_content("[border=solid][padding=10px]")
        assert result == ""

        # Test with whitespace and directives
        result = factory._strip_directives_from_code_content("  [align=center]  actual content  ")
        assert result == "actual content"

    def test_extract_formatting_with_directive_code_spans(self, factory: ElementFactory, md_parser: MarkdownIt):
        """Test that directive patterns are stripped from inline code spans during formatting extraction."""
        # Test direct stripping functionality - this protects against cases where
        # the markdown parser might incorrectly include directive patterns in code content
        test_cases = [
            # Direct test of stripping functionality
            (
                "[border=solid][padding=10px] GET endpoints equivalent",
                "GET endpoints equivalent",
            ),
            ("[align=center] code content here", "code content here"),
            (
                "normal code content",
                "normal code content",
            ),  # Control case with no directives
        ]

        for test_content, expected_cleaned in test_cases:
            result = factory._strip_directives_from_code_content(test_content)
            assert result == expected_cleaned, f"Expected '{expected_cleaned}' but got '{result}' from content: {test_content}"

        # Test integration: verify that normal markdown parsing with code spans works correctly
        # and that our protection doesn't interfere with normal operation
        normal_markdown_cases = [
            ("`normal code`", "normal code"),
            ("`another test`", "another test"),
            # Test case showing directive separation works correctly
            ("[border=solid] `clean code`", "clean code"),
        ]

        for markdown_text, expected_code_text in normal_markdown_cases:
            formatting = factory.extract_formatting_from_text(markdown_text, md_parser)

            # Find the CODE format
            code_formats = [f for f in formatting if f.format_type == TextFormatType.CODE]

            if expected_code_text:
                assert len(code_formats) == 1, f"Expected exactly one code format in: {markdown_text}"

                # Reconstruct the plain text to check what the formatting refers to
                plain_text_parts = []

                # Build the plain text as the formatter does
                tokens = md_parser.parse(markdown_text)
                for token in tokens:
                    if token.type == "inline" and hasattr(token, "children"):
                        for child in token.children:
                            if child.type == "text":
                                plain_text_parts.append(child.content)
                            elif child.type == "code_inline":
                                # Apply our cleaning logic (though in normal cases it won't change anything)
                                cleaned_content = factory._strip_directives_from_code_content(child.content)
                                plain_text_parts.append(cleaned_content)

                full_plain_text = "".join(plain_text_parts)
                code_format = code_formats[0]
                actual_code_text = full_plain_text[code_format.start : code_format.end]

                assert actual_code_text == expected_code_text, (
                    f"Expected code text '{expected_code_text}' but got '{actual_code_text}' from markdown: {markdown_text}"
                )

    def test_directive_stripping_integration_slide4_scenario(self, factory: ElementFactory, md_parser: MarkdownIt):
        """
        Test the specific scenario from Slide 4 where directive patterns could be mis-parsed
        into inline code spans, demonstrating protection against the REMAINING ISSUE B.
        """
        # Simulate a scenario where somehow directive patterns end up in code span content
        # This could happen due to parser edge cases or malformed input

        # Test the _extract_formatting_from_inline_token method with a mock token structure
        # that simulates the problematic case
        from markdown_it.token import Token

        # Create a mock inline token with a code_inline child that contains directive patterns
        inline_token = Token("inline", "", 0)
        inline_token.children = []

        # Create a text token for directive patterns that should be separate
        text_token = Token("text", "", 0)
        text_token.content = "[border=solid][padding=10px] "
        inline_token.children.append(text_token)

        # Create a code_inline token that might erroneously contain directive patterns
        # (this simulates a parser bug or edge case)
        code_token = Token("code_inline", "", 0)
        code_token.content = "[margin=5px] GET endpoints equivalent"  # Problematic content
        inline_token.children.append(code_token)

        # Extract formatting using our protected method
        formatting = factory._extract_formatting_from_inline_token(inline_token)

        # Verify that we get a CODE format
        code_formats = [f for f in formatting if f.format_type == TextFormatType.CODE]
        assert len(code_formats) == 1, "Should have exactly one code format"

        # The key test: verify that the problematic directive pattern was stripped
        # and only the actual code content remains in the calculated positions

        # Reconstruct what the plain text should look like after our cleaning
        expected_plain_text = "[border=solid][padding=10px] GET endpoints equivalent"
        # Position: directive text (30 chars) + cleaned code (23 chars)

        code_format = code_formats[0]
        expected_start = len("[border=solid][padding=10px] ")  # 30
        expected_end = expected_start + len("GET endpoints equivalent")  # 30 + 23 = 53

        assert code_format.start == expected_start, f"Code format should start at {expected_start}, got {code_format.start}"
        assert code_format.end == expected_end, f"Code format should end at {expected_end}, got {code_format.end}"

        # Extract the actual text that would be covered by this format
        actual_code_text = expected_plain_text[code_format.start : code_format.end]
        assert actual_code_text == "GET endpoints equivalent", (
            f"Code span should contain 'GET endpoints equivalent', got '{actual_code_text}'"
        )
