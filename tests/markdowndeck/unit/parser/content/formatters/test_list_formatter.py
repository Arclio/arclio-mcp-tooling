import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import ElementType, ListElement, TextFormatType
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters.list import ListFormatter


class TestListFormatter:
    """Unit tests for the ListFormatter."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> ListFormatter:
        return ListFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    @pytest.mark.parametrize("token_type", ["bullet_list_open", "ordered_list_open"])
    def test_can_handle_list_open_tokens(self, formatter: ListFormatter, token_type: str, md_parser: MarkdownIt):
        markdown = "* Item" if token_type == "bullet_list_open" else "1. Item"
        tokens = md_parser.parse(markdown)
        assert formatter.can_handle(tokens[0], tokens)  # tokens[0] is *_list_open

    def test_cannot_handle_other_tokens(self, formatter: ListFormatter, md_parser: MarkdownIt):
        tokens = md_parser.parse("Just text")  # Creates paragraph_open, etc.
        assert not formatter.can_handle(tokens[0], tokens)

    def test_process_simple_bullet_list(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = "* Item 1\n* Item 2"
        tokens = md_parser.parse(markdown)
        element, end_index = formatter.process(tokens, 0, {})

        assert isinstance(element, ListElement)
        assert element.element_type == ElementType.BULLET_LIST
        assert len(element.items) == 2
        assert element.items[0].text == "Item 1"
        assert element.items[0].level == 0
        assert element.items[1].text == "Item 2"
        assert end_index == len(tokens) - 1  # Should consume all tokens up to bullet_list_close

    def test_process_simple_ordered_list(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = "1. First\n2. Second"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, ListElement)
        assert element.element_type == ElementType.ORDERED_LIST
        assert len(element.items) == 2
        assert element.items[0].text == "First"
        assert element.items[1].text == "Second"

    def test_process_list_with_formatted_items(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = "* **Bold Item**\n* *Italic Item*"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, ListElement)
        assert element.items[0].text == "Bold Item"
        assert len(element.items[0].formatting) == 1
        assert element.items[0].formatting[0].format_type == TextFormatType.BOLD
        assert element.items[1].text == "Italic Item"
        assert len(element.items[1].formatting) == 1
        assert element.items[1].formatting[0].format_type == TextFormatType.ITALIC

    def test_process_nested_bullet_list(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = "* Level 1 Item 1\n  * Level 2 Item A\n  * Level 2 Item B\n* Level 1 Item 2"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, ListElement)
        assert len(element.items) == 2
        assert element.items[0].text == "Level 1 Item 1"
        assert element.items[0].level == 0
        assert len(element.items[0].children) == 2
        assert element.items[0].children[0].text == "Level 2 Item A"
        assert element.items[0].children[0].level == 1
        assert element.items[0].children[1].text == "Level 2 Item B"
        assert element.items[0].children[1].level == 1
        assert element.items[1].text == "Level 1 Item 2"
        assert element.items[1].level == 0
        assert len(element.items[1].children) == 0

    def test_process_deeply_nested_list(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = "1. L1\n   1. L2\n      * L3-bullet\n2. L1 Again"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, ListElement)
        assert element.element_type == ElementType.ORDERED_LIST
        assert len(element.items) == 2
        assert element.items[0].text == "L1"
        assert len(element.items[0].children) == 1
        l2_item = element.items[0].children[0]
        assert l2_item.text == "L2"
        assert l2_item.level == 1  # Level relative to its parent list type
        assert len(l2_item.children) == 1
        l3_item = l2_item.children[0]
        assert l3_item.text == "L3-bullet"
        assert l3_item.level == 2  # Level relative to its parent list type

    def test_process_empty_list(self, formatter: ListFormatter, md_parser: MarkdownIt):
        markdown = ""  # An empty list is hard to represent, usually markdown-it won't make list tokens
        tokens = md_parser.parse(markdown)  # Will be empty or just paragraph
        if tokens and tokens[0].type.endswith("_list_open"):  # Should not happen for empty string
            element, _ = formatter.process(tokens, 0, {})
            assert element is None or len(element.items) == 0
        else:  # More likely scenario
            pass  # No list tokens generated

        # Test list with empty item (markdown-it might parse this differently)
        markdown_empty_item = "* \n* Item 2"
        tokens_empty_item = md_parser.parse(markdown_empty_item)
        element_empty, _ = formatter.process(tokens_empty_item, 0, {})
        if element_empty:  # Check if element is created
            assert element_empty.items[0].text == ""  # First item text might be empty
            assert element_empty.items[1].text == "Item 2"
