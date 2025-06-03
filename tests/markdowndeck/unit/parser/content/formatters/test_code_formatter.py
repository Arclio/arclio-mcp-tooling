"""Comprehensive tests for all content formatters with directive support."""

import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import ElementType, TextFormatType
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters import (
    CodeFormatter,
    ImageFormatter,
    ListFormatter,
    TableFormatter,
)


class TestCodeFormatter:
    """Enhanced tests for the CodeFormatter with directive support."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> CodeFormatter:
        return CodeFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    def test_can_handle_fence_token(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test fence token handling."""
        tokens = md_parser.parse("```python\nprint('hi')\n```")
        assert formatter.can_handle(tokens[0], tokens)

    def test_cannot_handle_other_tokens(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test rejection of non-fence tokens."""
        tokens = md_parser.parse("Just text")
        assert not formatter.can_handle(tokens[0], tokens)

    def test_process_code_block_with_directives(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test code block processing with directives (P1 fix)."""
        markdown = "```python\ndef hello():\n  return 'world'\n```"
        tokens = md_parser.parse(markdown)

        # Include directives that would come from preceding directive paragraph
        directives = {
            "background": {"type": "named", "value": "black"},
            "color": {"type": "hex", "value": "#00ff00"},
            "fontsize": 12,
            "border": {
                "width": "1px",
                "style": "solid",
                "color": {"type": "named", "value": "gray"},
            },
        }

        element, end_index = formatter.process(tokens, 0, {}, directives)

        assert element.element_type == ElementType.CODE
        assert element.code == "def hello():\n  return 'world'\n"
        assert element.language == "python"

        # Check that directives are properly applied
        assert element.directives["background"]["value"] == "black"
        assert element.directives["color"]["value"] == "#00ff00"
        assert element.directives["fontsize"] == 12
        assert element.directives["border"]["width"] == "1px"
        assert end_index == 0

    def test_process_code_block_no_language(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test code block without language specification."""
        markdown = "```\nSome plain text code\n```"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {}, {})

        assert element.language == "text"
        assert element.code == "Some plain text code\n"

    def test_process_code_block_with_section_directives(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test code block with both section and element directives."""
        markdown = "```bash\necho 'test'\n```"
        tokens = md_parser.parse(markdown)

        section_directives = {"margin": 10, "padding": 5}
        element_directives = {
            "background": {"type": "named", "value": "dark"},
            "margin": 15,
        }

        element, _ = formatter.process(
            tokens, 0, section_directives, element_directives
        )

        # Element directives should override section directives
        assert element.directives["margin"] == 15  # Overridden
        assert element.directives["padding"] == 5  # Inherited
        assert element.directives["background"]["value"] == "dark"  # Element-specific

    def test_process_empty_code_block(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test empty code block processing."""
        markdown = "```\n```"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {}, {})

        assert element.code == ""
        assert element.language == "text"

    def test_process_code_block_with_enhanced_css_directives(
        self, formatter: CodeFormatter, md_parser: MarkdownIt
    ):
        """Test code block with enhanced CSS directives (P8)."""
        markdown = '```json\n{"key": "value"}\n```'
        tokens = md_parser.parse(markdown)

        css_directives = {
            "background": {
                "type": "gradient",
                "value": "linear-gradient(90deg, #1e1e1e, #2d2d2d)",
                "definition": "90deg, #1e1e1e, #2d2d2d",
            },
            "border-radius": 8,
            "box-shadow": {"type": "css", "value": "0 4px 8px rgba(0,0,0,0.3)"},
        }

        element, _ = formatter.process(tokens, 0, {}, css_directives)

        assert element.directives["background"]["type"] == "gradient"
        assert element.directives["border-radius"] == 8
        assert element.directives["box-shadow"]["type"] == "css"


class TestImageFormatter:
    """Enhanced tests for the ImageFormatter with directive support."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> ImageFormatter:
        return ImageFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    def test_can_handle_paragraph_with_image(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test handling of paragraphs containing images."""
        tokens = md_parser.parse("![alt](url.jpg)")
        assert formatter.can_handle(tokens[0], tokens)

    def test_process_image_only_paragraph_with_directives(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test image-only paragraph processing with directives (P1 fix)."""
        markdown = "![Product Image](https://example.com/product.jpg)"
        tokens = md_parser.parse(markdown)

        # Directives that would come from preceding directive paragraph
        directives = {
            "width": 0.75,  # 75%
            "height": 400,
            "align": "center",
            "border": {
                "width": "2px",
                "style": "solid",
                "color": {"type": "named", "value": "gray"},
            },
            "border-radius": 10,
        }

        element, end_index = formatter.process(tokens, 0, {}, directives)

        assert element.element_type == ElementType.IMAGE
        assert element.url == "https://example.com/product.jpg"
        assert element.alt_text == "Product Image"

        # Check directive application
        assert element.directives["width"] == 0.75
        assert element.directives["height"] == 400
        assert element.directives["align"] == "center"
        assert element.directives["border"]["width"] == "2px"
        assert element.directives["border-radius"] == 10
        assert end_index == 2

    def test_process_paragraph_with_mixed_content(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test that mixed content paragraphs are not handled by ImageFormatter."""
        markdown = "Some text ![alt](url.jpg) more text"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {}, {})
        assert element is None

    def test_process_image_with_empty_alt_text(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test image processing with empty alt text."""
        markdown = "![](image.png)"
        tokens = md_parser.parse(markdown)
        directives = {"caption": "A beautiful image"}

        element, _ = formatter.process(tokens, 0, {}, directives)

        assert element.url == "image.png"
        assert element.alt_text == ""
        assert element.directives["caption"] == "A beautiful image"

    def test_process_image_no_url(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test image processing with no URL."""
        markdown = "![no url image]()"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {}, {})
        assert element is None

    def test_process_image_with_responsive_directives(
        self, formatter: ImageFormatter, md_parser: MarkdownIt
    ):
        """Test image with responsive design directives."""
        markdown = "![Responsive](image.jpg)"
        tokens = md_parser.parse(markdown)

        responsive_directives = {
            "width": 1.0,  # 100% width
            "max-width": 800,  # Max 800px
            "height": "auto",
            "object-fit": "cover",
            "loading": "lazy",
        }

        element, _ = formatter.process(tokens, 0, {}, responsive_directives)

        assert element.directives["width"] == 1.0
        assert element.directives["max-width"] == 800
        assert element.directives["object-fit"] == "cover"
        assert element.directives["loading"] == "lazy"


class TestListFormatter:
    """Enhanced tests for the ListFormatter with directive support."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> ListFormatter:
        return ListFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    def test_process_bullet_list_with_directives(
        self, formatter: ListFormatter, md_parser: MarkdownIt
    ):
        """Test bullet list processing with directives (P1 fix)."""
        markdown = "* First item\n* Second item with **bold**\n* Third item"
        tokens = md_parser.parse(markdown)

        # Directives from preceding directive paragraph
        directives = {
            "color": {"type": "named", "value": "blue"},
            "margin": 10,
            "list-style": "square",
            "spacing": 1.5,
        }

        element, end_index = formatter.process(tokens, 0, {}, directives)

        assert element.element_type == ElementType.BULLET_LIST
        assert len(element.items) == 3

        # Check directive application
        assert element.directives["color"]["value"] == "blue"
        assert element.directives["margin"] == 10
        assert element.directives["list-style"] == "square"
        assert element.directives["spacing"] == 1.5

        # Check items
        assert element.items[0].text == "First item"
        assert element.items[1].text == "Second item with bold"
        assert element.items[2].text == "Third item"

        # Check formatting in second item
        assert len(element.items[1].formatting) == 1
        assert element.items[1].formatting[0].format_type == TextFormatType.BOLD

    def test_process_ordered_list_with_directives(
        self, formatter: ListFormatter, md_parser: MarkdownIt
    ):
        """Test ordered list processing with directives."""
        markdown = "1. First item\n2. Second item\n3. Third item"
        tokens = md_parser.parse(markdown)

        directives = {
            "numbering-style": "roman",
            "color": {"type": "hex", "value": "#333333"},
            "indent": 20,
        }

        element, _ = formatter.process(tokens, 0, {}, directives)

        assert element.element_type == ElementType.ORDERED_LIST
        assert element.directives["numbering-style"] == "roman"
        assert element.directives["color"]["value"] == "#333333"
        assert element.directives["indent"] == 20

    def test_process_nested_list_with_directives(
        self, formatter: ListFormatter, md_parser: MarkdownIt
    ):
        """Test nested list processing with directives."""
        markdown = """* Level 1 Item 1
  * Level 2 Item A
  * Level 2 Item B
* Level 1 Item 2
  1. Nested ordered item
  2. Another nested ordered item"""
        tokens = md_parser.parse(markdown)

        directives = {"nested-indent": 25, "line-height": 1.6}

        element, _ = formatter.process(tokens, 0, {}, directives)

        assert len(element.items) == 2
        assert len(element.items[0].children) == 2  # First item has 2 children
        assert len(element.items[1].children) == 2  # Second item has 2 children

        # Check nested items
        assert element.items[0].children[0].text == "Level 2 Item A"
        assert element.items[0].children[1].text == "Level 2 Item B"

        # Check directive inheritance
        assert element.directives["nested-indent"] == 25
        assert element.directives["line-height"] == 1.6

    def test_process_list_with_complex_content(
        self, formatter: ListFormatter, md_parser: MarkdownIt
    ):
        """Test list with complex content and formatting."""
        markdown = """* Item with `code` and **bold** text
* Item with [link](http://example.com)
* Item with ~~strikethrough~~ text"""
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, {})

        # Check formatting in items
        item1 = element.items[0]
        assert "code" in item1.text
        assert "bold" in item1.text
        code_formats = [
            f for f in item1.formatting if f.format_type == TextFormatType.CODE
        ]
        bold_formats = [
            f for f in item1.formatting if f.format_type == TextFormatType.BOLD
        ]
        assert len(code_formats) == 1
        assert len(bold_formats) == 1

        item2 = element.items[1]
        link_formats = [
            f for f in item2.formatting if f.format_type == TextFormatType.LINK
        ]
        assert len(link_formats) == 1
        assert link_formats[0].value == "http://example.com"

        item3 = element.items[2]
        strike_formats = [
            f for f in item3.formatting if f.format_type == TextFormatType.STRIKETHROUGH
        ]
        assert len(strike_formats) == 1

    def test_process_list_with_section_and_element_directives(
        self, formatter: ListFormatter, md_parser: MarkdownIt
    ):
        """Test directive merging for lists."""
        markdown = "* Item 1\n* Item 2"
        tokens = md_parser.parse(markdown)

        section_directives = {"color": {"type": "named", "value": "black"}, "margin": 5}
        element_directives = {
            "color": {"type": "named", "value": "blue"},
            "padding": 10,
        }

        element, _ = formatter.process(
            tokens, 0, section_directives, element_directives
        )

        # Element directives should override section directives
        assert element.directives["color"]["value"] == "blue"  # Overridden
        assert element.directives["margin"] == 5  # Inherited
        assert element.directives["padding"] == 10  # Element-specific


class TestTableFormatter:
    """Enhanced tests for the TableFormatter with directive support."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> TableFormatter:
        return TableFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        md = MarkdownIt()
        md.enable("table")
        return md

    def test_process_table_with_directives(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table processing with directives (P1 fix)."""
        markdown = """| Name | Age | City |
|------|-----|------|
| Alice | 25 | NYC |
| Bob | 30 | LA |"""
        tokens = md_parser.parse(markdown)

        # Directives from preceding directive paragraph
        directives = {
            "border": {
                "width": "1px",
                "style": "solid",
                "color": {"type": "named", "value": "gray"},
            },
            "cell-align": "center",
            "cell-padding": 8,
            "header-background": {"type": "hex", "value": "#f0f0f0"},
            "width": 1.0,  # 100%
            "striped": True,
        }

        element, end_index = formatter.process(tokens, 0, {}, directives)

        assert element.element_type == ElementType.TABLE
        assert element.headers == ["Name", "Age", "City"]
        assert element.rows == [["Alice", "25", "NYC"], ["Bob", "30", "LA"]]

        # Check directive application
        assert element.directives["border"]["width"] == "1px"
        assert element.directives["cell-align"] == "center"
        assert element.directives["cell-padding"] == 8
        assert element.directives["header-background"]["value"] == "#f0f0f0"
        assert element.directives["width"] == 1.0
        assert element.directives["striped"] is True

    def test_process_table_with_formatting_in_cells(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table with formatted cell content."""
        markdown = """| **Name** | *Age* | `Code` |
|----------|-------|--------|
| **Alice** | *25* | `A001` |
| Bob | 30 | `B002` |"""
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, {})

        # Formatting should be stripped to plain text
        assert element.headers == ["Name", "Age", "Code"]
        assert element.rows[0] == ["Alice", "25", "A001"]
        assert element.rows[1] == ["Bob", "30", "B002"]

    def test_process_table_with_empty_cells(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table with empty cells."""
        markdown = """| Name | Age | |
|------|-----|--|
| Alice |  | 25 |
|  | Bob | 30 |"""
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, {})

        assert element.headers == ["Name", "Age", ""]
        assert element.rows == [["Alice", "", "25"], ["", "Bob", "30"]]

    def test_process_table_no_body_rows(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table with headers but no body rows."""
        markdown = """| Header1 | Header2 |
|---------|---------|"""
        tokens = md_parser.parse(markdown)

        element, _ = formatter.process(tokens, 0, {}, {})

        assert element.headers == ["Header1", "Header2"]
        assert element.rows == []

    def test_process_table_with_advanced_styling_directives(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table with advanced CSS styling directives (P8)."""
        markdown = """| Product | Price |
|---------|-------|
| Widget | $10 |
| Gadget | $20 |"""
        tokens = md_parser.parse(markdown)

        advanced_directives = {
            "border-collapse": "collapse",
            "border-spacing": 0,
            "background": {
                "type": "gradient",
                "value": "linear-gradient(180deg, #ffffff, #f8f9fa)",
                "definition": "180deg, #ffffff, #f8f9fa",
            },
            "box-shadow": {"type": "css", "value": "0 2px 8px rgba(0,0,0,0.1)"},
            "border-radius": 6,
            "overflow": "hidden",
        }

        element, _ = formatter.process(tokens, 0, {}, advanced_directives)

        assert element.directives["border-collapse"] == "collapse"
        assert element.directives["background"]["type"] == "gradient"
        assert element.directives["box-shadow"]["type"] == "css"
        assert element.directives["border-radius"] == 6

    def test_process_table_with_cell_specific_directives(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        """Test table with cell-specific styling directives."""
        markdown = """| Status | Count |
|--------|-------|
| Active | 150 |
| Inactive | 75 |"""
        tokens = md_parser.parse(markdown)

        cell_directives = {
            "cell-range": "A1:B1",  # Header row
            "header-font-weight": "bold",
            "header-text-align": "center",
            "data-text-align": "right",
            "alternating-row-colors": ["#ffffff", "#f8f9fa"],
        }

        element, _ = formatter.process(tokens, 0, {}, cell_directives)

        assert element.directives["cell-range"] == "A1:B1"
        assert element.directives["header-font-weight"] == "bold"
        assert element.directives["data-text-align"] == "right"
        assert element.directives["alternating-row-colors"] == ["#ffffff", "#f8f9fa"]


# ========================================================================
# Integration Tests for All Formatters
# ========================================================================


class TestFormatterIntegration:
    """Integration tests for all formatters working together."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        md = MarkdownIt()
        md.enable("table")
        md.enable("strikethrough")
        return md

    def test_formatter_precedence_image_vs_text(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        """Test that ImageFormatter takes precedence over TextFormatter for image-only content."""
        image_formatter = ImageFormatter(factory)

        # Image-only paragraph should be handled by ImageFormatter
        tokens = md_parser.parse("![test](image.jpg)")
        assert image_formatter.can_handle(tokens[0], tokens)

        element, _ = image_formatter.process(tokens, 0, {}, {})
        assert element.element_type == ElementType.IMAGE

    def test_complex_content_with_multiple_formatters(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        """Test complex content that would use multiple formatters."""
        # This would be handled by different formatters in a real scenario
        formatters = [
            ImageFormatter(factory),
            ListFormatter(factory),
            CodeFormatter(factory),
            TableFormatter(factory),
        ]

        # Test each formatter with appropriate content
        test_cases = [
            ("![image](test.jpg)", ElementType.IMAGE),
            ("* List item", ElementType.BULLET_LIST),
            ("```\ncode\n```", ElementType.CODE),
            ("| H |\n|---|\n| C |", ElementType.TABLE),
        ]

        for markdown, expected_type in test_cases:
            tokens = md_parser.parse(markdown)

            # Find which formatter can handle this
            handling_formatter = None
            for formatter in formatters:
                if formatter.can_handle(tokens[0], tokens):
                    handling_formatter = formatter
                    break

            assert handling_formatter is not None
            element, _ = handling_formatter.process(tokens, 0, {}, {})
            assert element.element_type == expected_type

    def test_directive_merging_consistency_across_formatters(
        self, factory: ElementFactory, md_parser: MarkdownIt
    ):
        """Test that directive merging works consistently across all formatters."""
        section_directives = {"color": {"type": "named", "value": "blue"}, "margin": 10}
        element_directives = {"color": {"type": "named", "value": "red"}, "padding": 5}

        formatters = [
            ImageFormatter(factory),
            ListFormatter(factory),
            CodeFormatter(factory),
            TableFormatter(factory),
        ]

        for formatter in formatters:
            # Test merge_directives method
            merged = formatter.merge_directives(section_directives, element_directives)

            # Element directives should override section directives
            assert merged["color"]["value"] == "red"  # Overridden
            assert merged["margin"] == 10  # Inherited
            assert merged["padding"] == 5  # Element-specific
