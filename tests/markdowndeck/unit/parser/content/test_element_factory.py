"""Updated unit tests for the ElementFactory with enhanced directive handling."""

import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import (
    AlignmentType,
    ElementType,
    ListItem,
    TextElement,
    TextFormat,
    TextFormatType,
)
from markdowndeck.parser.content.element_factory import ElementFactory


class TestElementFactory:
    """Updated unit tests for the ElementFactory."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        md = MarkdownIt()
        md.enable("strikethrough")
        return md

    # ========================================================================
    # Element Creation Tests (Updated with Directive Support)
    # ========================================================================

    def test_create_title_element_with_directives(self, factory: ElementFactory):
        """Test title element creation with directives."""
        formatting = [TextFormat(0, 5, TextFormatType.BOLD)]
        directives = {
            "align": "left",
            "fontsize": 24,
            "color": {"type": "named", "value": "blue"},
        }

        element = factory.create_title_element("Title", formatting, directives)

        assert isinstance(element, TextElement)
        assert element.element_type == ElementType.TITLE
        assert element.text == "Title"
        assert element.formatting == formatting
        assert element.horizontal_alignment == AlignmentType.LEFT  # From directives
        assert element.directives == directives

    def test_create_title_element_default_alignment(self, factory: ElementFactory):
        """Test title element with default center alignment."""
        element = factory.create_title_element("Title")
        assert element.horizontal_alignment == AlignmentType.CENTER

    def test_create_subtitle_element_with_directives(self, factory: ElementFactory):
        """Test subtitle element creation with directives."""
        directives = {"fontweight": "bold", "margin": 10}
        element = factory.create_subtitle_element(
            "Subtitle", alignment=AlignmentType.RIGHT, directives=directives
        )

        assert element.element_type == ElementType.SUBTITLE
        assert element.horizontal_alignment == AlignmentType.RIGHT
        assert element.directives == directives

    def test_create_text_element_with_directives(self, factory: ElementFactory):
        """Test text element creation with comprehensive directives."""
        directives = {
            "color": {"type": "rgba", "r": 255, "g": 0, "b": 0, "a": 0.8},
            "background": {"type": "hex", "value": "#f0f0f0"},
            "border": {
                "width": "1px",
                "style": "solid",
                "color": {"type": "named", "value": "black"},
            },
            "padding": 15,
            "margin": 10,
        }

        element = factory.create_text_element("Text", directives=directives)
        assert element.directives == directives
        assert element.horizontal_alignment == AlignmentType.LEFT

    def test_create_list_element_with_directives(self, factory: ElementFactory):
        """Test list element creation with directives."""
        items = [ListItem(text="Item 1"), ListItem(text="Item 2")]
        directives = {"color": {"type": "named", "value": "blue"}, "margin": 5}

        # Bullet list
        bullet_list = factory.create_list_element(
            items, ordered=False, directives=directives
        )
        assert bullet_list.element_type == ElementType.BULLET_LIST
        assert bullet_list.directives == directives

        # Ordered list
        ordered_list = factory.create_list_element(
            items, ordered=True, directives=directives
        )
        assert ordered_list.element_type == ElementType.ORDERED_LIST
        assert ordered_list.directives == directives

    def test_create_image_element_with_directives(self, factory: ElementFactory):
        """Test image element creation with directives."""
        directives = {
            "width": 0.5,  # 50%
            "height": 300,
            "align": "center",
            "border": {
                "width": "2px",
                "style": "solid",
                "color": {"type": "hex", "value": "#ccc"},
            },
        }

        element = factory.create_image_element("test.jpg", "Test Image", directives)
        assert element.element_type == ElementType.IMAGE
        assert element.url == "test.jpg"
        assert element.alt_text == "Test Image"
        assert element.directives == directives

    def test_create_table_element_with_directives(self, factory: ElementFactory):
        """Test table element creation with directives."""
        headers = ["Name", "Age"]
        rows = [["Alice", "25"], ["Bob", "30"]]
        directives = {
            "border": {
                "width": "1px",
                "style": "solid",
                "color": {"type": "named", "value": "gray"},
            },
            "cell-align": "center",
            "width": 1.0,  # 100%
        }

        element = factory.create_table_element(headers, rows, directives)
        assert element.element_type == ElementType.TABLE
        assert element.headers == headers
        assert element.rows == rows
        assert element.directives == directives

    def test_create_code_element_with_directives(self, factory: ElementFactory):
        """Test code element creation with directives."""
        directives = {
            "background": {"type": "named", "value": "black"},
            "color": {"type": "hex", "value": "#00ff00"},
            "fontsize": 12,
            "border-radius": 4,
        }

        element = factory.create_code_element("print('hello')", "python", directives)
        assert element.element_type == ElementType.CODE
        assert element.code == "print('hello')"
        assert element.language == "python"
        assert element.directives == directives

    # ========================================================================
    # Enhanced Formatting Extraction Tests
    # ========================================================================

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
                [
                    TextFormat(
                        start=5, end=11, format_type=TextFormatType.ITALIC, value=True
                    ),
                    TextFormat(
                        start=0, end=17, format_type=TextFormatType.BOLD, value=True
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
        ],
    )
    def test_extract_formatting_from_text(
        self,
        factory: ElementFactory,
        md_parser: MarkdownIt,
        markdown_text: str,
        expected_formats: list[TextFormat],
    ):
        """Test formatting extraction from text."""
        extracted = factory.extract_formatting_from_text(markdown_text, md_parser)

        # Sort for consistent comparison
        sorted_extracted = sorted(
            extracted, key=lambda f: (f.start, f.end, f.format_type.value)
        )
        sorted_expected = sorted(
            expected_formats, key=lambda f: (f.start, f.end, f.format_type.value)
        )

        assert sorted_extracted == sorted_expected

    def test_extract_formatting_with_directive_text(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        """Test formatting extraction from text that contains directive patterns."""
        # Text that might confuse the parser with directive-like patterns
        text_with_directives = (
            "[color=red] This **bold** text has [brackets] but formatting."
        )

        formatting = factory.extract_formatting_from_text(
            text_with_directives, md_parser
        )

        # Should still extract bold formatting properly
        bold_formats = [f for f in formatting if f.format_type == TextFormatType.BOLD]
        assert len(bold_formats) == 1

        # The bold format should be positioned correctly relative to cleaned text
        bold_format = bold_formats[0]
        cleaned_text = factory._remove_directive_patterns(text_with_directives)
        bold_text = cleaned_text[bold_format.start : bold_format.end]
        assert "bold" in bold_text

    def test_extract_formatting_empty_and_whitespace(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        """Test formatting extraction with empty and whitespace text."""
        assert factory.extract_formatting_from_text("", md_parser) == []
        assert factory.extract_formatting_from_text("   ", md_parser) == []
        assert factory.extract_formatting_from_text("\n\t\n", md_parser) == []

    # ========================================================================
    # Directive Pattern Detection and Removal Tests
    # ========================================================================

    def test_remove_directive_patterns(self, factory: ElementFactory):
        """Test removal of directive patterns from text."""
        # Single directive at start
        text1 = "[color=blue] Regular text content"
        cleaned1 = factory._remove_directive_patterns(text1)
        assert cleaned1 == "Regular text content"

        # Multiple directives at start
        text2 = "[align=center][fontsize=14][margin=5px] Content here"
        cleaned2 = factory._remove_directive_patterns(text2)
        assert cleaned2 == "Content here"

        # No directives
        text3 = "Just regular text"
        cleaned3 = factory._remove_directive_patterns(text3)
        assert cleaned3 == "Just regular text"

        # Directives in middle (should not be removed)
        text4 = "Text with [color=red] in middle"
        cleaned4 = factory._remove_directive_patterns(text4)
        assert cleaned4 == "Text with [color=red] in middle"

    def test_strip_directives_from_code_content(self, factory: ElementFactory):
        """Test directive stripping from code content (enhanced)."""
        # Directive prefix in code
        code1 = "[border=solid][padding=10px] GET /api/users"
        cleaned1 = factory._strip_directives_from_code_content(code1)
        assert cleaned1 == "GET /api/users"

        # Multiple directive patterns
        code2 = "[align=center] [width=100%] const value = 42;"
        cleaned2 = factory._strip_directives_from_code_content(code2)
        assert cleaned2 == "const value = 42;"

        # No directives in code
        code3 = "function test() { return true; }"
        cleaned3 = factory._strip_directives_from_code_content(code3)
        assert cleaned3 == "function test() { return true; }"

        # Only directives (edge case)
        code4 = "[border=solid][padding=10px]"
        cleaned4 = factory._strip_directives_from_code_content(code4)
        assert cleaned4 == ""

        # Empty content
        assert factory._strip_directives_from_code_content("") == ""

    # ========================================================================
    # Enhanced Inline Token Processing Tests
    # ========================================================================

    def test_extract_formatting_from_inline_token_with_code_cleaning(
        self, factory: ElementFactory
    ):
        """Test inline token processing with code content cleaning."""
        from markdown_it.token import Token

        # Create mock inline token with code that has directive patterns
        inline_token = Token("inline", "", 0)
        inline_token.children = []

        # Text token
        text_token = Token("text", "", 0)
        text_token.content = "Code example: "
        inline_token.children.append(text_token)

        # Code token with directive patterns
        code_token = Token("code_inline", "", 0)
        code_token.content = "[margin=5px] fetch('/api/data')"
        inline_token.children.append(code_token)

        # More text
        text_token2 = Token("text", "", 0)
        text_token2.content = " is clean."
        inline_token.children.append(text_token2)

        formatting = factory._extract_formatting_from_inline_token(inline_token)

        # Should have code formatting
        code_formats = [f for f in formatting if f.format_type == TextFormatType.CODE]
        assert len(code_formats) == 1

        # Code format should cover cleaned content only
        code_format = code_formats[0]
        expected_start = len("Code example: ")
        expected_end = expected_start + len("fetch('/api/data')")

        assert code_format.start == expected_start
        assert code_format.end == expected_end

    def test_extract_formatting_complex_mixed_content(self, factory: ElementFactory):
        """Test formatting extraction from complex mixed content."""
        from markdown_it.token import Token

        # Create complex inline token: **bold** `code` [link](url) *italic*
        inline_token = Token("inline", "", 0)
        inline_token.children = []

        # Bold section
        inline_token.children.append(Token("strong_open", "", 0))
        text1 = Token("text", "", 0)
        text1.content = "bold"
        inline_token.children.append(text1)
        inline_token.children.append(Token("strong_close", "", 0))

        # Space
        space1 = Token("text", "", 0)
        space1.content = " "
        inline_token.children.append(space1)

        # Code
        code = Token("code_inline", "", 0)
        code.content = "code"
        inline_token.children.append(code)

        # Space
        space2 = Token("text", "", 0)
        space2.content = " "
        inline_token.children.append(space2)

        # Link
        link_open = Token("link_open", "", 0)
        link_open.attrs = {"href": "http://example.com"}
        inline_token.children.append(link_open)
        link_text = Token("text", "", 0)
        link_text.content = "link"
        inline_token.children.append(link_text)
        inline_token.children.append(Token("link_close", "", 0))

        # Space
        space3 = Token("text", "", 0)
        space3.content = " "
        inline_token.children.append(space3)

        # Italic
        inline_token.children.append(Token("em_open", "", 0))
        text2 = Token("text", "", 0)
        text2.content = "italic"
        inline_token.children.append(text2)
        inline_token.children.append(Token("em_close", "", 0))

        formatting = factory._extract_formatting_from_inline_token(inline_token)

        # Expected: bold, code, link, italic
        assert len(formatting) == 4

        format_types = [f.format_type for f in formatting]
        assert TextFormatType.BOLD in format_types
        assert TextFormatType.CODE in format_types
        assert TextFormatType.LINK in format_types
        assert TextFormatType.ITALIC in format_types

        # Check link value
        link_format = next(
            f for f in formatting if f.format_type == TextFormatType.LINK
        )
        assert link_format.value == "http://example.com"

    def test_extract_formatting_with_nested_formats(self, factory: ElementFactory):
        """Test formatting extraction with nested formats."""
        from markdown_it.token import Token

        # Create nested formatting: **bold *italic* text**
        inline_token = Token("inline", "", 0)
        inline_token.children = []

        inline_token.children.append(Token("strong_open", "", 0))
        text1 = Token("text", "", 0)
        text1.content = "bold "
        inline_token.children.append(text1)

        inline_token.children.append(Token("em_open", "", 0))
        text2 = Token("text", "", 0)
        text2.content = "italic"
        inline_token.children.append(text2)
        inline_token.children.append(Token("em_close", "", 0))

        text3 = Token("text", "", 0)
        text3.content = " text"
        inline_token.children.append(text3)
        inline_token.children.append(Token("strong_close", "", 0))

        formatting = factory._extract_formatting_from_inline_token(inline_token)

        # Should have both bold and italic
        bold_format = next(
            f for f in formatting if f.format_type == TextFormatType.BOLD
        )
        italic_format = next(
            f for f in formatting if f.format_type == TextFormatType.ITALIC
        )

        # Bold should encompass the entire content
        assert bold_format.start == 0
        assert bold_format.end == len("bold italic text")

        # Italic should be nested within bold
        assert italic_format.start == len("bold ")
        assert italic_format.end == len("bold italic")

    # ========================================================================
    # Error Handling and Edge Cases
    # ========================================================================

    def test_extract_formatting_malformed_tokens(self, factory: ElementFactory):
        """Test formatting extraction with malformed token structures."""
        from markdown_it.token import Token

        # Token without children
        inline_token1 = Token("inline", "", 0)
        # No children attribute
        formatting1 = factory._extract_formatting_from_inline_token(inline_token1)
        assert formatting1 == []

        # Token with empty children
        inline_token2 = Token("inline", "", 0)
        inline_token2.children = []
        formatting2 = factory._extract_formatting_from_inline_token(inline_token2)
        assert formatting2 == []

        # Non-inline token
        non_inline_token = Token("paragraph", "", 0)
        formatting3 = factory._extract_formatting_from_inline_token(non_inline_token)
        assert formatting3 == []

    def test_directive_pattern_edge_cases(self, factory: ElementFactory):
        """Test directive pattern handling edge cases."""
        # Malformed bracket patterns
        text1 = "[incomplete directive"
        cleaned1 = factory._remove_directive_patterns(text1)
        assert cleaned1 == text1  # Should be unchanged

        # Empty brackets
        text2 = "[] [=] [key=] Content"
        cleaned2 = factory._remove_directive_patterns(text2)
        # Should handle malformed patterns gracefully
        assert "Content" in cleaned2

        # Nested brackets (not valid directives)
        text3 = "[[nested=value]] Content"
        cleaned3 = factory._remove_directive_patterns(text3)
        assert cleaned3 == "[[nested=value]] Content"  # Should not match pattern

    def test_code_content_edge_cases(self, factory: ElementFactory):
        """Test code content processing edge cases."""
        # Whitespace only
        assert factory._strip_directives_from_code_content("   ") == "   "

        # Directive-like patterns that aren't valid directives
        code1 = "[not-a-directive] [invalid:value] real_code()"
        cleaned1 = factory._strip_directives_from_code_content(code1)
        # Should only strip valid directive patterns
        assert "real_code()" in cleaned1

        # Multiple valid directives with whitespace
        code2 = "  [border=solid]  [padding=10px]  \n  actual_code()  "
        cleaned2 = factory._strip_directives_from_code_content(code2)
        assert cleaned2.strip() == "actual_code()"

    # ========================================================================
    # Integration Tests
    # ========================================================================

    def test_create_elements_with_mixed_directive_types(self, factory: ElementFactory):
        """Test creating various elements with different directive types."""
        # Advanced CSS directives
        advanced_directives = {
            "background": {
                "type": "gradient",
                "value": "linear-gradient(45deg, red, blue)",
                "definition": "45deg, red, blue",
            },
            "border": {
                "width": "2px",
                "style": "dashed",
                "color": {"type": "rgba", "r": 128, "g": 128, "b": 128, "a": 0.7},
            },
            "box-shadow": {"type": "css", "value": "0 2px 4px rgba(0,0,0,0.1)"},
            "transform": {"type": "css", "value": "rotate(45deg) scale(1.1)"},
        }

        # Test with text element
        text_elem = factory.create_text_element(
            "Advanced styled text", directives=advanced_directives
        )
        assert text_elem.directives["background"]["type"] == "gradient"
        assert text_elem.directives["border"]["color"]["type"] == "rgba"
        assert text_elem.directives["box-shadow"]["type"] == "css"

        # Test with other element types
        list_elem = factory.create_list_element(
            [ListItem(text="Item")], directives=advanced_directives
        )
        assert list_elem.directives == advanced_directives

        table_elem = factory.create_table_element(
            ["H1"], [["C1"]], directives=advanced_directives
        )
        assert table_elem.directives == advanced_directives

    def test_element_creation_with_empty_directives(self, factory: ElementFactory):
        """Test element creation with empty or None directives."""
        # None directives
        elem1 = factory.create_text_element("Text", directives=None)
        assert elem1.directives == {}

        # Empty directives
        elem2 = factory.create_text_element("Text", directives={})
        assert elem2.directives == {}

        # Should not affect other properties
        assert elem1.text == "Text"
        assert elem1.element_type == ElementType.TEXT
