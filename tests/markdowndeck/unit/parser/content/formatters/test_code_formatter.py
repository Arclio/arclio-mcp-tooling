import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import CodeElement, ElementType
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters.code import CodeFormatter


class TestCodeFormatter:
    """Unit tests for the CodeFormatter."""

    @pytest.fixture
    def factory(self) -> ElementFactory:
        return ElementFactory()

    @pytest.fixture
    def formatter(self, factory: ElementFactory) -> CodeFormatter:
        return CodeFormatter(factory)

    @pytest.fixture
    def md_parser(self) -> MarkdownIt:
        return MarkdownIt()

    def test_can_handle_fence_token(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        tokens = md_parser.parse("```python\nprint('hi')\n```")
        assert formatter.can_handle(tokens[0], tokens)  # tokens[0] is fence

    def test_cannot_handle_other_tokens(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        tokens = md_parser.parse("Just text")
        assert not formatter.can_handle(tokens[0], tokens)  # paragraph_open

    def test_process_code_block_with_language(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        markdown = "```python\ndef hello():\n  return 'world'\n```"
        tokens = md_parser.parse(markdown)  # This is a single 'fence' token
        element, end_index = formatter.process(tokens, 0, {"custom": "val"})

        assert isinstance(element, CodeElement)
        assert element.element_type == ElementType.CODE
        assert element.code == "def hello():\n  return 'world'\n"  # Content includes trailing newline
        assert element.language == "python"
        assert element.directives.get("custom") == "val"
        assert end_index == 0  # Fence token is self-contained

    def test_process_code_block_no_language(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        markdown = "```\nSome plain text code\n```"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, CodeElement)
        assert element.language == "text"  # Default
        assert element.code == "Some plain text code\n"

    def test_process_empty_code_block(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        markdown = "```\n```"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, CodeElement)
        assert element.code == ""  # Content is empty string
        assert element.language == "text"  # Default

    def test_process_code_block_tilde_fences(self, formatter: CodeFormatter, md_parser: MarkdownIt):
        markdown = "~~~\nJust code\n~~~"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, CodeElement)
        assert element.code == "Just code\n"
