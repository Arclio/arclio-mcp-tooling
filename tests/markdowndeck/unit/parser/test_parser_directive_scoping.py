import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserDirectiveScoping:
    """Tests for complex directive scoping scenarios."""

    def test_element_scoped_directives(self, parser: Parser):
        """Test Case: PARSER-E-06 (Element-Scoped)"""
        markdown = "# Title [color=blue]\n## Subtitle [fontsize=20]\n![img.png](url) [width=50][height=50]"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        title = slide.get_title_element()
        subtitle = slide.get_subtitle_element()
        image = next(e for e in slide.elements if e.element_type == ElementType.IMAGE)

        assert title.directives.get("color") is not None
        assert subtitle.directives.get("fontsize") == 20.0
        assert image.directives.get("width") == 50.0

    def test_section_scoped_directives(self, parser: Parser):
        """Test Case: PARSER-C-09 (Section-Scoped)"""
        markdown = "[align=center]\n## Centered Content"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        # Base directives apply to the slide, not the root section
        assert slide.base_directives.get("align") == "center"
        # The content parser will apply this to the element
        text_element = next(e for e in slide.elements if e.element_type == ElementType.TEXT and e.text == "Centered Content")
        assert text_element.directives.get("align") == "center"

    def test_directive_precedence(self, parser: Parser):
        """Test Case: PARSER-E-08 (Directive Precedence)"""
        markdown = "[align=center]\nThis text is centered.\n- A list [align=left]"
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # The base directive is center
        assert slide.base_directives.get("align") == "center"

        # The text element inherits the base directive
        text_element = next(e for e in slide.elements if e.element_type == ElementType.TEXT)
        assert text_element.directives.get("align") == "center"

        # The list element overrides the base directive
        list_element = next(e for e in slide.elements if e.element_type == ElementType.BULLET_LIST)
        assert list_element.directives.get("align") == "left"
