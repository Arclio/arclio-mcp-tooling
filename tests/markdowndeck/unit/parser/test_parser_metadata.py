import pytest
from markdowndeck.models import ElementType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestMetadataParser:
    def test_slide_with_base_directives(self, parser: Parser):
        """Validates that directives at the top of a slide become base_directives."""
        markdown = "[color=blue][fontsize=12]\n:::section\n# My Title\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.base_directives.get("color") is not None
        assert slide.base_directives.get("fontsize") == 12.0

        # UPDATED: The refactored parser correctly identifies "# My Title" as the slide title
        assert slide.get_title_element().text == "My Title"

        # The section should now be empty (title was correctly extracted)
        title_section = slide.root_section.children[0]
        assert len(title_section.children) == 0  # The title was correctly extracted

    def test_directive_precedence_scoping(self, parser: Parser):
        """Validates that base, section, and element directives are correctly scoped."""
        markdown = "[align=center]\n:::section[color=red]\nThis text is red.\n- A list [align=left]\n:::"
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Base directive is center
        assert slide.base_directives.get("align") == "center"

        section = slide.root_section.children[0]
        text_element = next(
            e for e in section.children if e.element_type == ElementType.TEXT
        )
        list_element = next(
            e for e in section.children if e.element_type == ElementType.BULLET_LIST
        )

        # The text element inherits from the section (red) and the base (center)
        assert text_element.directives.get("color") is not None
        assert text_element.directives.get("align") == "center"

        # The list element overrides the inherited alignment
        assert list_element.directives.get("align") == "left"
        assert list_element.directives.get("color") is not None

    def test_element_scoped_directives_on_meta_elements(self, parser: Parser):
        """Validates that directives on title/subtitle are stored correctly."""
        markdown = (
            "# Title [color=blue]\n## Subtitle [fontsize=20]\n:::section\nBody\n:::"
        )
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        assert slide.title_directives.get("color") is not None
        assert slide.subtitle_directives.get("fontsize") == 20.0
