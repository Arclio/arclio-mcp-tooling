"""
Diagnostic tests for the Parser, based on complex real-world markdown.
These tests are designed to reproduce specific parsing issues observed during analysis.
"""

import pytest
from markdowndeck.models import ElementType, TextFormatType
from markdowndeck.parser import Parser


@pytest.fixture
def parser() -> Parser:
    """Provides a fresh Parser instance for each test."""
    return Parser()


class TestParserDiagnostics:
    """Targeted diagnostic tests for the markdowndeck parser."""

    def test_diag_p_01_complex_formatting(self, parser: Parser):
        """
        Validates that complex inline formatting with multiple types on a single line
        is parsed into a list of valid TextFormat objects, not booleans or other incorrect types.
        This test is based on Slide 2 of the diagnostic input.
        """
        # Arrange
        markdown = "- **Universal Standard**: MCP eliminates M×N integration complexity"

        # Act
        deck = parser.parse(markdown)
        list_element = deck.slides[0].elements[0]
        list_item = list_element.items[0]

        # Assert
        assert isinstance(list_item.formatting, list)
        assert len(list_item.formatting) > 0
        assert isinstance(list_item.formatting[0], object)
        assert list_item.formatting[0].format_type == TextFormatType.BOLD
        assert list_item.text.startswith("Universal Standard")

    def test_diag_p_02_list_item_with_standalone_directive(self, parser: Parser):
        """
        Validates that a directive on its own line within a list's content
        is correctly associated with individual list items per DIRECTIVES.md Rule 2.3.
        This test is based on Slide 5 of the diagnostic input.
        Updated to comply with The List Item Rule.
        """
        # Arrange
        markdown = """
- Context provision
[border=2pt solid TEXT1]
- GET endpoints equivalent
"""

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        list_element = next(
            (e for e in slide.elements if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        # Assert
        assert list_element is not None, "A ListElement should have been created."
        assert len(list_element.items) == 2, "The list should have two distinct items."
        assert "Context provision" in list_element.items[0].text
        assert "GET endpoints equivalent" in list_element.items[1].text

        # FIXED: According to DIRECTIVES.md Rule 2.3, the directive should apply to the second list item
        # The list element itself should NOT have the directive
        assert (
            "border" not in list_element.directives
        ), "List element should NOT have the directive (it applies to individual items per Rule 2.3)"

        # The second list item should have the directive
        second_item = list_element.items[1]
        assert (
            "border" in second_item.directives
        ), "Second list item should have the directive per DIRECTIVES.md Rule 2.3"
        assert second_item.directives["border"] == "2pt solid TEXT1"

        # The first list item should not have the directive
        first_item = list_element.items[0]
        assert (
            "border" not in first_item.directives
        ), "First list item should NOT have the directive"

    def test_diag_p_03_post_image_directive_consumption(self, parser: Parser):
        """
        Validates that directives immediately following an image are consumed and
        associated with the image, and do not create a spurious text element.
        This test is based on Slide 10 of the diagnostic input.
        """
        # Arrange
        markdown = "![Dev Tools](image.png)[padding=10][background=white]"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        elements = slide.sections[0].children

        # Assert
        assert len(elements) == 1, "Should only create one element (the image)."
        image_element = elements[0]
        assert image_element.element_type == ElementType.IMAGE
        assert "padding" in image_element.directives
        assert "background" in image_element.directives
        assert image_element.directives["padding"] == 10.0

    def test_diag_p_04_slide_level_directive_scoping(self, parser: Parser):
        """
        Validates that directives at the top of a slide, before the title, are
        scoped to the section containing the subsequent content per the new specification.
        Updated for Unified Hierarchical Directive Scoping model.
        """
        # Arrange - Add body content so sections are created
        markdown = (
            "[align=center][color=white]\n# Title\n## Subtitle\nSome body content."
        )
        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        next(e for e in slide.elements if e.element_type == ElementType.TITLE)
        next(e for e in slide.elements if e.element_type == ElementType.SUBTITLE)

        # Assert
        # Per the new specification: standalone directives should be section-level
        assert len(slide.sections) > 0, "Should have sections when there's body content"
        section = slide.sections[0]

        # The directives should be on the section, not the title
        assert (
            len(slide.title_directives) == 0
        ), "Title should have no directives (they're not on the same line)"

        # Section should have the directives
        assert (
            section.directives.get("align") == "center"
        ), "Section should have the align directive"
        assert (
            section.directives.get("color") is not None
        ), "Section should have the color directive"

        # Elements should inherit from section (this is the inheritance behavior)
        # Note: This tests the current inheritance behavior, which may be correct
        # depending on how we want directive inheritance to work

    def test_diag_p_05_list_item_formatting_type(self, parser: Parser):
        """
        Validates that formatting within a list item is a proper TextFormat object.
        This test specifically targets the `[true]` bug.
        """
        # Arrange
        markdown = "- **Universal Standard**: Some text."

        # Act
        deck = parser.parse(markdown)
        list_element = next(
            (
                e
                for e in deck.slides[0].elements
                if e.element_type == ElementType.BULLET_LIST
            ),
            None,
        )
        assert list_element is not None, "List element not found."
        list_item = list_element.items[0]

        # Assert
        assert isinstance(list_item.formatting, list), "Formatting should be a list."
        assert len(list_item.formatting) > 0, "Formatting list should not be empty."

        # This is the critical check
        formatting_object = list_item.formatting[0]
        assert not isinstance(
            formatting_object, bool
        ), "Formatting entry must not be a boolean."
        assert hasattr(
            formatting_object, "format_type"
        ), "Formatting object must have a 'format_type' attribute."
        assert formatting_object.format_type == TextFormatType.BOLD
        assert (
            list_item.text[formatting_object.start : formatting_object.end]
            == "Universal Standard"
        )

    def test_diag_p_01_structural_parsing_and_directive_scope(self, parser: Parser):
        """
        Validates the Unified Hierarchical Directive Scoping model:
        1. Element-Scoped Directives (Rule 1): Directives on same line as elements
        2. Section-Scoped Directives (Rule 2): Standalone directives apply to containing section
        """
        # Arrange: Use '===' as the correct slide separator.
        problematic_slide_markdown = """# Model Context Protocol
    [background=url(https://example.com/image.jpg)][color=white]
    **Revolutionizing AI**
    ===
    # Executive Summary
[width=60%][border=1pt solid red]
## Key Takeaways
- **Universal Standard**
    """
        # Act
        deck = parser.parse(problematic_slide_markdown)

        # Assert - Top-level structure
        assert (
            len(deck.slides) == 2
        ), "Should parse exactly two slides separated by '==='."

        # === Assertions for Slide 1: Testing Element-Scoped Directives (Rule 1) ===
        slide1 = deck.slides[0]
        title1 = next(
            (e for e in slide1.elements if e.element_type == ElementType.TITLE), None
        )
        body_text1 = next(
            (e for e in slide1.elements if "Revolutionizing AI" in e.text), None
        )

        assert title1 is not None, "Slide 1 must have a title element."
        assert body_text1 is not None, "Slide 1 must have a body text element."

        # CRITICAL ASSERTION 1: The standalone indented directives should be section-level (Rule 2)
        # Per Rule 2: directives on their own line apply to the containing section
        assert (
            len(slide1.title_directives) == 0
        ), "Title should have no directives (they're not on the same line)."

        # CRITICAL ASSERTION 2: The content section should have these standalone directives.
        assert (
            len(slide1.sections) == 1
        ), "Slide 1 should have one root section for the body content."
        root_section1 = slide1.sections[0]
        assert (
            "background_type" in root_section1.directives
        ), "Section should have the background directive (converted format)."
        assert (
            root_section1.directives["background_type"] == "image"
        ), "Background should be processed as image type."
        assert (
            "color" in root_section1.directives
        ), "Section should have the color directive."

        # === Assertions for Slide 2: Testing Section-Scoped Directives (Rule 2) ===
        slide2 = deck.slides[1]
        title2 = next(
            (e for e in slide2.elements if e.element_type == ElementType.TITLE), None
        )
        # Note: No subtitle2 lookup - per our specification, when standalone directives
        # appear before a subtitle, the subtitle stays in section content (Rule 2)
        list_element = next(
            (e for e in slide2.elements if e.element_type == ElementType.BULLET_LIST),
            None,
        )
        heading_element = next(
            (
                e
                for e in slide2.elements
                if e.element_type == ElementType.TEXT and "Key Takeaways" in e.text
            ),
            None,
        )

        assert title2 is not None, "Slide 2 Title not found"
        assert list_element is not None, "Slide 2 List not found"
        assert (
            heading_element is not None
        ), "Slide 2 should have 'Key Takeaways' as a text element (not subtitle)"

        # CRITICAL ASSERTION 3: Title directives should be empty (no same-line directives)
        assert (
            len(slide2.title_directives) == 0
        ), "Slide 2 title should have no directives (not on same line)."

        # CRITICAL ASSERTION 4: Root section should contain the standalone directives
        # Per Rule 2: standalone directives apply to the smallest containing section
        assert (
            len(slide2.sections) == 1
        ), "Slide 2 should have one root section for the content."
        root_section2 = slide2.sections[0]

        # The key test: standalone directives should be section-scoped, not title-scoped
        assert (
            root_section2.directives.get("width") == 0.6
        ), "Section directives were not parsed correctly - expected width=0.6 from '60%'."
        assert (
            "border" in root_section2.directives
        ), "Section border directive was not parsed correctly."

        # CRITICAL ASSERTION 5: Title should NOT have these section directives
        assert (
            "width" not in title2.directives
        ), "Title should NOT have section-level width directive."

    def test_diag_p_06_section_vs_element_directive_scope(self, parser: Parser):
        """
        Validates that section-level and element-level directives are scoped correctly.
        - A directive at the top of a section applies to the whole section.
        - A directive immediately preceding an element overrides the section's directive for that element only.
        """
        # Arrange
        markdown = """[align=center]
This text should be centered.

[align=left]
- This list item should be left-aligned.
- This one too.
"""
        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        text_element = next(
            (e for e in section.children if e.element_type == ElementType.TEXT), None
        )
        list_element = next(
            (e for e in section.children if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        # Assert
        assert (
            section.directives.get("align") == "center"
        ), "Section directive was not parsed correctly."

        assert text_element is not None, "Text element not found."
        assert (
            text_element.directives.get("align") == "center"
        ), "Text element should inherit alignment from section."

        assert list_element is not None, "List element not found."
        assert (
            list_element.directives.get("align") == "left"
        ), "List element should have its own overridden alignment."
