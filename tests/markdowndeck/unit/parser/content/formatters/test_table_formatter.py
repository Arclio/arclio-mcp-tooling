import pytest
from markdown_it import MarkdownIt
from markdowndeck.models import ElementType, TableElement
from markdowndeck.parser.content.element_factory import ElementFactory
from markdowndeck.parser.content.formatters.table import TableFormatter


class TestTableFormatter:
    """Unit tests for the TableFormatter."""

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

    def test_can_handle_table_open_token(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        markdown = "| H1 | H2 |\n|---|---|\n| C1 | C2 |"
        tokens = md_parser.parse(markdown)
        assert formatter.can_handle(tokens[0], tokens)  # tokens[0] is table_open

    def test_cannot_handle_other_tokens(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        tokens = md_parser.parse("Just text")
        assert not formatter.can_handle(tokens[0], tokens)  # paragraph_open

    def test_process_simple_table(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        markdown = "| Header 1 | Header 2 |\n|---|---|\n| Cell A1 | Cell A2 |\n| Cell B1 | Cell B2 |"
        tokens = md_parser.parse(markdown)
        element, end_index = formatter.process(tokens, 0, {"border": "solid"})

        assert isinstance(element, TableElement)
        assert element.element_type == ElementType.TABLE
        assert element.headers == ["Header 1", "Header 2"]
        assert element.rows == [["Cell A1", "Cell A2"], ["Cell B1", "Cell B2"]]
        assert element.directives.get("border") == "solid"
        assert end_index == len(tokens) - 1  # Should consume all table tokens

    def test_process_table_no_body(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        markdown = "| H1 | H2 |\n|---|---|"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, TableElement)
        assert element.headers == ["H1", "H2"]
        assert element.rows == []

    def test_process_table_empty_cells(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        markdown = "| H1 || H3 |\n|---|---|---|\n| R1C1 |  | R1C3 |"
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, TableElement)
        assert element.headers == [
            "H1",
            "",
            "H3",
        ]  # Markdown-it often produces empty string for empty cell
        assert element.rows == [["R1C1", "", "R1C3"]]

    def test_process_table_cell_with_inline_formatting(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        # Markdown-it usually renders inline formatting inside table cells to plain text in the token content.
        # The TextFormat objects are not typically preserved per cell by default in markdown-it's table tokens.
        markdown = (
            "| **Bold H** | *Italic H* |\n|---|---|\n| `code cell` | [link](url) |"
        )
        tokens = md_parser.parse(markdown)
        element, _ = formatter.process(tokens, 0, {})

        assert isinstance(element, TableElement)
        assert element.headers == ["Bold H", "Italic H"]
        assert element.rows == [["code cell", "link"]]  # The text content of the link

    def test_malformed_table_should_not_break(
        self, formatter: TableFormatter, md_parser: MarkdownIt
    ):
        # This is more about markdown-it's leniency, but formatter should not crash.
        markdown = "| H1 | H2 \n|---|\n| C1 |"  # Fewer separator lines
        tokens = md_parser.parse(markdown)  # markdown-it might not form a table
        if tokens[0].type == "table_open":
            element, _ = formatter.process(tokens, 0, {})
            assert (
                element is not None
            )  # Or it might be None if table structure is too broken
        else:  # If markdown-it doesn't parse it as a table, formatter won't be called
            pass
