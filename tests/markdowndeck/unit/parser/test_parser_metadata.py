import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    return Parser()


class TestMetadataParser:
    def test_slide_with_base_directives(self, parser: Parser):
        """Validates that directives at the top of a slide become base_directives."""
        markdown = "[color=blue][fontsize=12]\n# My Title"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.base_directives.get("color") is not None
        assert slide.base_directives.get("fontsize") == 12.0
        assert slide.get_title_element().text == "My Title"

    def test_directive_precedence_scoping(self, parser: Parser):
        """Validates that base, section, and element directives are correctly scoped."""
        markdown = "[align=center]\n:::section[color=red]\nThis text is red.\n- A list [align=left]\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Base directive is center
        assert slide.base_directives.get("align") == "center"

        # The text element inherits from the section (red) and the base (center)
        text_element = next(
            e for e in slide.elements if e.element_type == ElementType.TEXT
        )
        assert text_element.directives.get("color") is not None  # from section
        assert text_element.directives.get("align") == "center"  # from base

        # The list element overrides the inherited alignment
        list_element = next(
            e for e in slide.elements if e.element_type == ElementType.BULLET_LIST
        )
        assert list_element.directives.get("align") == "left"  # from element
        assert list_element.directives.get("color") is not None  # from section

    def test_element_scoped_directives_on_meta_elements(self, parser: Parser):
        """Validates that directives on title/subtitle are stored correctly."""
        markdown = "# Title [color=blue]\n## Subtitle [fontsize=20]"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.title_directives.get("color") is not None
        assert slide.subtitle_directives.get("fontsize") == 20.0
