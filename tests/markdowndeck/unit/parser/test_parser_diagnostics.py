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
        is correctly associated with the list element, not mangled into text.
        This test is based on Slide 5 of the diagnostic input.
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
        assert (
            "border" in list_element.directives
        ), "Directive should be associated with the list."
        assert list_element.directives["border"] == "2pt solid TEXT1"

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
        scoped to the section containing the subsequent content, not just the first element.
        This is based on Slide 1 of the diagnostic input.
        """
        # Arrange
        markdown = "[align=center][color=white]\n# Title\n## Subtitle"
        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        title_element = next(
            e for e in slide.elements if e.element_type == ElementType.TITLE
        )
        subtitle_element = next(
            e for e in slide.elements if e.element_type == ElementType.SUBTITLE
        )

        # Assert
        # The ideal behavior is that the section gets the directives.
        # A less ideal but acceptable behavior is that both elements inherit it.
        # The failure case is when ONLY the title gets it.
        slide.sections[0].directives

        # For now, let's test if the directives are correctly applied to the title.
        # A more advanced test would check for inheritance.
        assert title_element.directives.get("align") == "center"
        assert title_element.directives.get("color") is not None

        # This is the key part: does the directive "bleed" or get applied correctly to the next element?
        # Given the current parser logic, it's likely to be associated with the title only.
        # A better parser would associate it with the parent section.
        # Let's test the most likely failure mode: the subtitle does NOT get the directive.
        # A more correct implementation would have the subtitle inherit from the section.
        # So we test if the subtitle's *own* directive dict has the value.
        assert (
            subtitle_element.directives.get("align") == "center"
        ), "Alignment should apply to the subtitle as well"
        assert (
            subtitle_element.directives.get("color") is not None
        ), "Color should apply to the subtitle as well"

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
        Validates the most critical parser bugs found during diagnostics:
        1.  Correct separation of slide-level directives from section content.
        2.  Correct association of directives with the slide/title, not the first content section.
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

        # === Assertions for Slide 1: Testing Directive Scoping ===
        slide1 = deck.slides[0]
        title1 = next(
            (e for e in slide1.elements if e.element_type == ElementType.TITLE), None
        )
        body_text1 = next(
            (e for e in slide1.elements if "Revolutionizing AI" in e.text), None
        )

        assert title1 is not None, "Slide 1 must have a title element."
        assert body_text1 is not None, "Slide 1 must have a body text element."

        # CRITICAL ASSERTION 1: The slide's title_directives should contain the directives,
        # NOT the section's directives. The `SlideExtractor` should have consumed them.
        assert (
            "background" in slide1.title_directives
        ), "Slide-level background directive was not parsed correctly."
        assert (
            "color" in slide1.title_directives
        ), "Slide-level color directive was not parsed correctly."

        # CRITICAL ASSERTION 2: The content section should NOT have these directives.
        assert (
            len(slide1.sections) == 1
        ), "Slide 1 should have one root section for the body content."
        root_section1 = slide1.sections[0]
        assert (
            "background" not in root_section1.directives
        ), "Background directive should NOT be on the content section."
        assert (
            "color" not in root_section1.directives
        ), "Color directive should NOT be on the content section."

        # CRITICAL ASSERTION 3: The body text element itself should not have the directives.
        assert (
            "background" not in body_text1.directives
        ), "Body text should NOT directly have the background directive."

        # === Assertions for Slide 2: Testing Structural Integrity ===
        slide2 = deck.slides[1]
        title2 = next(
            (e for e in slide2.elements if e.element_type == ElementType.TITLE), None
        )
        subtitle2 = next(
            (e for e in slide2.elements if e.element_type == ElementType.SUBTITLE),
            None,
        )
        list_element = next(
            (e for e in slide2.elements if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        assert title2 is not None, "Slide 2 Title not found"
        assert subtitle2 is not None, "Slide 2 Subtitle not found"
        assert list_element is not None, "Slide 2 List not found"

        # CRITICAL ASSERTION 4: Title and Subtitle are slide-level metadata and MUST NOT
        # be parsed as children of the first content section.
        assert (
            len(slide2.sections) == 1
        ), "Slide 2 should have one root section for the list."
        root_section2 = slide2.sections[0]

        assert all(
            child.element_type != ElementType.TITLE for child in root_section2.children
        ), "Section must not contain the slide Title."
        assert all(
            child.element_type != ElementType.SUBTITLE
            for child in root_section2.children
        ), "Section must not contain the slide Subtitle."

        # CRITICAL ASSERTION 5: The content section should contain the list element,
        # and it should have inherited the section's directives.
        assert (
            list_element in root_section2.children
        ), "List element must be a child of the content section."
        assert (
            root_section2.directives.get("width") == 0.6
        ), "Section directives were not parsed correctly."
        assert (
            list_element.directives.get("width") == 0.6
        ), "List element should inherit section directives."
