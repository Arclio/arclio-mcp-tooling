"""
Unit tests for the Parser component, ensuring adherence to PARSER_SPEC.md.

Each test case directly corresponds to a specification in
`docs/markdowndeck/testing/TEST_CASES_PARSER.md`.
"""

import pytest
from markdowndeck.models import ElementType, TextFormatType
from markdowndeck.parser import Parser


class TestParser:
    """Tests the functionality of the MarkdownDeck Parser."""

    @pytest.fixture
    def parser(self) -> Parser:
        """Provides a fresh Parser instance for each test."""
        return Parser()

    def test_parser_c_01(self, parser: Parser):
        """
        Test Case: PARSER-C-01
        Validates parsing a simple slide into the correct "Unpositioned" state.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Title\nSome content."

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 1
        slide = deck.slides[0]

        # Check inventory list
        assert len(slide.elements) == 2
        element_types = [e.element_type for e in slide.elements]
        assert ElementType.TITLE in element_types
        assert ElementType.TEXT in element_types

        # Check sections hierarchy
        assert len(slide.sections) == 1
        root_section = slide.sections[0]
        assert len(root_section.children) == 1
        assert root_section.children[0].element_type == ElementType.TEXT

        # Verify Unpositioned IR state (all spatial attributes must be None)
        for element in slide.elements:
            assert (
                element.position is None
            ), f"Element {element.element_type} should have no position."
            assert (
                element.size is None
            ), f"Element {element.element_type} should have no size."
        for section in slide.sections:
            assert section.position is None, "Section should have no position."
            assert section.size is None, "Section should have no size."

    def test_parser_c_02(self, parser: Parser):
        """
        Test Case: PARSER-C-02
        Validates that '===' correctly splits markdown into multiple slides.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Slide 1\nContent 1\n===\n# Slide 2\nContent 2"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 2
        assert deck.slides[0].title == "Slide 1"
        assert deck.slides[1].title == "Slide 2"
        assert "Content 1" in deck.slides[0].elements[1].text
        assert "Content 2" in deck.slides[1].elements[1].text

    def test_parser_c_03(self, parser: Parser):
        """
        Test Case: PARSER-C-03
        Validates correct extraction of title, footer, notes, and directives.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = (
            "# Title [align=center]\n<!-- notes: My notes -->\nContent\n@@@\nFooter"
        )

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.title == "Title"
        assert slide.title_directives.get("align") == "center"
        assert slide.notes == "My notes"
        assert slide.footer == "Footer"
        assert "Content" in slide.elements[1].text
        # Verify that metadata strings have been properly removed from content elements
        content_text = slide.elements[1].text
        assert "<!-- notes:" not in content_text
        assert "@@@" not in content_text

    def test_parser_c_04(self, parser: Parser):
        """
        Test Case: PARSER-C-04
        Validates that an indented title is correctly identified and removed.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "   #   Indented Title\nContent below."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert slide.title == "Indented Title"
        text_element = next(
            (e for e in slide.elements if e.element_type == ElementType.TEXT), None
        )
        assert text_element is not None
        assert text_element.text == "Content below."

    def test_parser_c_05(self, parser: Parser):
        """
        Test Case: PARSER-C-05
        Validates that '---' correctly splits content into vertical sections.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Vertical Sections\nTop Section\n---\nBottom Section"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 2
        assert "Top Section" in slide.sections[0].children[0].text
        assert "Bottom Section" in slide.sections[1].children[0].text

    def test_parser_c_06(self, parser: Parser):
        """
        Test Case: PARSER-C-06
        Validates that '***' creates a 'row' section with nested children.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Horizontal Sections\nLeft Column\n***\nRight Column"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 1
        row_section = slide.sections[0]
        assert row_section.type == "row"
        assert len(row_section.children) == 2

        left_child_section = row_section.children[0]
        right_child_section = row_section.children[1]
        assert "Left Column" in left_child_section.children[0].text
        assert "Right Column" in right_child_section.children[0].text

    def test_parser_c_07(self, parser: Parser):
        """
        Test Case: PARSER-C-07
        Validates correct parsing of mixed vertical and horizontal sections.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "# Mixed Layout\nTop\n---\nLeft\n***\nRight\n---\nBottom"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 3
        assert slide.sections[0].type == "section"
        assert "Top" in slide.sections[0].children[0].text
        assert slide.sections[1].type == "row"
        assert len(slide.sections[1].children) == 2
        assert slide.sections[2].type == "section"
        assert "Bottom" in slide.sections[2].children[0].text

    def test_parser_c_08(self, parser: Parser):
        """
        Test Case: PARSER-C-08
        Validates that separators within code blocks are ignored.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "Top\n```\n---\n***\n===\n```\nBottom"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 1
        slide = deck.slides[0]
        assert len(slide.sections) == 1
        section_children = slide.sections[0].children
        assert len(section_children) == 3
        assert section_children[0].element_type == ElementType.TEXT
        assert section_children[0].text == "Top"
        assert section_children[1].element_type == ElementType.CODE
        assert section_children[1].code.strip() == "---\n***\n==="
        assert section_children[2].element_type == ElementType.TEXT
        assert section_children[2].text == "Bottom"

    def test_parser_c_09(self, parser: Parser):
        """
        Test Case: PARSER-C-09 (Updated for Unified Hierarchical Directive Scoping)
        Validates section-scoped directive parsing per Rule 2 (The Containment Rule).
        Standalone directives apply to the smallest containing section.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[align=center]\n## Centered Section\nContent"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]
        heading_element = next(
            e
            for e in section.children
            if e.element_type == ElementType.TEXT and "Centered Section" in e.text
        )

        # Assert
        # Per Rule 2: standalone directive should be on the section, not the element
        assert (
            section.directives.get("align") == "center"
        ), "Section should have the align directive"

        # The heading element should inherit from its parent section
        assert heading_element is not None
        # Note: inheritance behavior will be handled by layout manager,
        # but for now we verify the directive is on the section

    def test_parser_c_10(self, parser: Parser):
        """
        Test Case: PARSER-C-10
        Validates correct directive consumption for block elements.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[border=solid]\n- Item 1\n- Item 2"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]
        list_element = next(
            (e for e in section.children if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        # Assert
        assert list_element is not None
        assert list_element.directives.get("border") == "solid"

        # Check for spurious text element
        spurious_text = [
            e
            for e in section.children
            if e.element_type == ElementType.TEXT and e.text.strip() == "[border=solid]"
        ]
        assert len(spurious_text) == 0

    def test_parser_c_11(self, parser: Parser):
        """
        Test Case: PARSER-C-11
        Validates same-line directive parsing and removal from text.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[color=red] This text is red."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        text_element = slide.sections[0].children[0]

        # Assert
        assert text_element.text == "This text is red."
        assert text_element.directives.get("color") == {"type": "named", "value": "red"}

    def test_parser_c_12(self, parser: Parser):
        """
        Test Case: PARSER-C-12
        Validates correct creation of TextElement with inline formatting.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "Text with **bold**, *italic*, and `code` spans."

        # Act
        deck = parser.parse(markdown)
        text_element = deck.slides[0].sections[0].children[0]

        # Assert
        assert text_element.text == "Text with bold, italic, and code spans."
        formats = {f.format_type for f in text_element.formatting}
        assert {
            TextFormatType.BOLD,
            TextFormatType.ITALIC,
            TextFormatType.CODE,
        }.issubset(formats)

        bold_format = next(
            f for f in text_element.formatting if f.format_type == TextFormatType.BOLD
        )
        assert text_element.text[bold_format.start : bold_format.end] == "bold"

    def test_parser_e_01(self, parser: Parser):
        """
        Test Case: PARSER-E-01
        Validates that empty or whitespace-only markdown produces an empty Deck.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Act
        deck1 = parser.parse("")
        deck2 = parser.parse("   \n\t  ")

        # Assert
        assert len(deck1.slides) == 0
        assert len(deck2.slides) == 0

    def test_parser_e_02(self, parser: Parser):
        """
        Test Case: PARSER-E-02
        Validates that markdown with only separators produces an empty Deck.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "===\n---\n***"

        # Act
        deck = parser.parse(markdown)

        # Assert
        assert len(deck.slides) == 0

    def test_parser_e_03(self, parser: Parser):
        """
        Test Case: PARSER-E-03
        Validates a slide with only directives and no content.
        From: docs/markdowndeck/testing/TEST_CASES_PARSER.md
        """
        # Arrange
        markdown = "[width=100%][height=100%]"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Assert
        assert len(deck.slides) == 1
        assert len(slide.sections) == 1
        assert len(section.children) == 0
        assert section.directives.get("width") == 1.0
        assert section.directives.get("height") == 1.0

    def test_parser_c_13_image_and_text_in_paragraph(self, parser: Parser):
        """
        Test Case: PARSER-C-13 (Custom)
        Validates that an image and text in the same paragraph are parsed into two separate elements.
        """
        # Arrange
        markdown = "![alt text](image.png) This is the caption."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Assert
        # The parser should create two elements for the single paragraph
        assert (
            len(section.children) == 2
        ), "Should create an ImageElement and a TextElement"

        image_element = section.children[0]
        text_element = section.children[1]

        assert image_element.element_type == ElementType.IMAGE
        assert getattr(image_element, "url", "") == "image.png"

        assert text_element.element_type == ElementType.TEXT
        assert getattr(text_element, "text", "").strip() == "This is the caption."

    def test_parser_c_14_stale_content_is_cleared(self, parser: Parser):
        """
        Test Case: PARSER-C-14 (Custom)
        Validates that Section.content is cleared after its content is parsed into child elements.
        """
        # Arrange
        markdown = "[align=center]\nSome content here."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]
        section = slide.sections[0]

        # Assert
        assert len(section.children) > 0, "Section should have parsed child elements."
        assert section.content == "", "Section.content must be cleared after parsing."

    def test_parser_c_15_section_directives_are_inherited(self, parser: Parser):
        """
        Test Case: PARSER-C-15 (Updated for Task 3)
        Validates that section-level directives are correctly inherited by all child elements.
        This test now validates the correct behavior where directives apply to all elements in a section.
        """
        # Arrange
        markdown = "[align=center]\n## Centered\n\nThis text should be left-aligned."

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        # Find the heading and text elements (note: headings are parsed as TEXT with heading-like content)
        # Look at section children for elements
        section = slide.sections[0]
        elements = section.children

        # Find heading and text elements
        heading_element = None
        text_elements = []

        for element in elements:
            if element.element_type == ElementType.TEXT:
                if "Centered" in element.text:
                    heading_element = element
                elif "left-aligned" in element.text:
                    text_elements.append(element)

        assert heading_element is not None, "Should have a heading element"
        assert len(text_elements) > 0, "Should have at least one text element"
        text_element = text_elements[0]

        # The heading should have center alignment from the directive
        assert (
            heading_element.directives.get("align") == "center"
        ), "Heading should inherit center alignment from the section."

        # The subsequent text element SHOULD ALSO inherit the directive
        assert (
            text_element.directives.get("align") == "center"
        ), "Text element SHOULD inherit the section's alignment directive."

    def test_parser_c_16_inline_directive_parsing_in_lists(self, parser: Parser):
        """
        Test Case: PARSER-C-16 (Task 1.2)
        Validates that directives inside list items are properly parsed.
        This test should FAIL initially, demonstrating missing inline directive support.
        """
        # Arrange - based on the problematic markdown from Slide 5
        markdown = """- Context provision
[border=2pt solid TEXT1]
- GET endpoints equivalent"""

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        # Find the list element (using correct ElementType)
        list_element = next(
            (e for e in slide.elements if e.element_type == ElementType.BULLET_LIST),
            None,
        )

        assert list_element is not None, "Should have a list element"

        # The list text should NOT contain the raw directive string
        # Check all list item text for the directive string
        list_text = " ".join(item.text for item in list_element.items)
        assert (
            "[border=2pt solid TEXT1]" not in list_text
        ), "Raw directive string should be parsed out of list text"

        # The list element should have the parsed border directive
        assert (
            "border" in list_element.directives
        ), "List element should have parsed border directive"
        assert (
            list_element.directives["border"] == "2pt solid TEXT1"
        ), "Border directive should be correctly parsed"

    def test_parser_c_17_post_image_directive_parsing(self, parser: Parser):
        """
        Test Case: PARSER-C-17 (Task 1.3)
        Validates that directives immediately following images are correctly associated.
        This test should FAIL initially, demonstrating missing post-image directive support.
        """
        # Arrange
        markdown = "![Alt text](http://example.com/image.jpg) [padding=10]"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        # Find the image element
        image_element = next(
            (e for e in slide.elements if e.element_type == ElementType.IMAGE), None
        )

        assert image_element is not None, "Should have an image element"

        # The image should have the padding directive
        assert (
            "padding" in image_element.directives
        ), "Image element should have parsed padding directive"
        assert (
            image_element.directives["padding"] == 10.0
        ), "Padding directive should be correctly parsed as float"

    def test_parser_c_18_textformat_instantiation(self, parser: Parser):
        """
        Test Case: PARSER-C-18 (Task 2.1)
        Validates that TextFormat objects are properly instantiated with correct types.
        This test should FAIL initially, demonstrating broken TextFormat instantiation.
        """
        # Arrange
        markdown = "A **bold** link: [text](url)"

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        # Find the text element
        text_element = next(
            (e for e in slide.elements if e.element_type == ElementType.TEXT), None
        )

        assert text_element is not None, "Should have a text element"
        assert hasattr(
            text_element, "formatting"
        ), "Text element should have formatting attribute"

        # The formatting should be a list of TextFormat objects, not booleans or strings
        formatting = text_element.formatting
        assert isinstance(formatting, list), "Formatting should be a list"
        assert (
            len(formatting) == 2
        ), "Should have exactly two TextFormat objects (bold and link)"

        # Check that all formatting entries are TextFormat objects
        from markdowndeck.models.constants import TextFormatType
        from markdowndeck.models.elements.text import TextFormat

        for fmt in formatting:
            assert isinstance(
                fmt, TextFormat
            ), f"Formatting entry should be TextFormat object, got {type(fmt)}: {fmt}"
            assert isinstance(
                fmt.start, int
            ), f"TextFormat.start should be int, got {type(fmt.start)}: {fmt.start}"
            assert isinstance(
                fmt.end, int
            ), f"TextFormat.end should be int, got {type(fmt.end)}: {fmt.end}"
            assert isinstance(
                fmt.format_type, TextFormatType
            ), f"TextFormat.format_type should be TextFormatType, got {type(fmt.format_type)}: {fmt.format_type}"

        # Find bold and link formatting
        bold_format = next(
            (f for f in formatting if f.format_type == TextFormatType.BOLD), None
        )
        link_format = next(
            (f for f in formatting if f.format_type == TextFormatType.LINK), None
        )

        assert bold_format is not None, "Should have bold formatting"
        assert link_format is not None, "Should have link formatting"

        # Check positions are correct integers
        assert (
            bold_format.start == 2
        ), f"Bold should start at position 2, got {bold_format.start}"
        assert (
            bold_format.end == 6
        ), f"Bold should end at position 6, got {bold_format.end}"

        assert (
            link_format.start == 13
        ), f"Link should start at position 13, got {link_format.start}"
        assert (
            link_format.end == 17
        ), f"Link should end at position 17, got {link_format.end}"
        assert (
            link_format.value == "url"
        ), f"Link value should be 'url', got {link_format.value}"

    def test_parser_c_19_comprehensive_textformat_validation(self, parser: Parser):
        """
        Test Case: PARSER-C-19 (Task 2.1 Comprehensive)
        Validates that all formatting issues from TASK_002 are resolved.
        Tests boolean, string, and multi-line formatting edge cases.
        """
        from markdowndeck.models.constants import TextFormatType
        from markdowndeck.models.elements.text import TextFormat

        # Test case 1: Boolean formatting issue (should not be [true])
        markdown1 = "**Bold text** and *italic text*"
        deck1 = parser.parse(markdown1)
        text_element1 = next(
            (e for e in deck1.slides[0].elements if e.element_type == ElementType.TEXT),
            None,
        )

        assert text_element1 is not None, "Should have text element"
        assert (
            len(text_element1.formatting) == 2
        ), "Should have bold and italic formatting"

        for fmt in text_element1.formatting:
            assert isinstance(
                fmt, TextFormat
            ), f"Should be TextFormat object, not {type(fmt)}"
            assert not isinstance(fmt, bool), "Should not be a boolean"
            assert fmt.format_type in [
                TextFormatType.BOLD,
                TextFormatType.ITALIC,
            ], f"Unexpected format type: {fmt.format_type}"

        # Test case 2: String formatting issue (links should not be ["https://..."])
        markdown2 = "Visit [our website](https://example.com) for more info"
        deck2 = parser.parse(markdown2)
        text_element2 = next(
            (e for e in deck2.slides[0].elements if e.element_type == ElementType.TEXT),
            None,
        )

        assert text_element2 is not None, "Should have text element"
        assert len(text_element2.formatting) == 1, "Should have one link formatting"

        link_fmt = text_element2.formatting[0]
        assert isinstance(
            link_fmt, TextFormat
        ), f"Should be TextFormat object, not {type(link_fmt)}"
        assert not isinstance(link_fmt, str), "Should not be a string"
        assert link_fmt.format_type == TextFormatType.LINK, "Should be link format type"
        assert link_fmt.value == "https://example.com", "Should have correct URL value"

        # Test case 3: Multi-line formatting (should handle line breaks correctly)
        markdown3 = "**This is bold\nacross multiple lines**"
        deck3 = parser.parse(markdown3)
        text_element3 = next(
            (e for e in deck3.slides[0].elements if e.element_type == ElementType.TEXT),
            None,
        )

        assert text_element3 is not None, "Should have text element"
        assert len(text_element3.formatting) == 1, "Should have one bold formatting"

        bold_fmt = text_element3.formatting[0]
        assert isinstance(
            bold_fmt, TextFormat
        ), f"Should be TextFormat object, not {type(bold_fmt)}"
        assert bold_fmt.format_type == TextFormatType.BOLD, "Should be bold format type"
        assert bold_fmt.start == 0, "Bold should start at beginning"
        assert bold_fmt.end == len(
            text_element3.text
        ), "Bold should cover entire text including newline"
        assert "\n" in text_element3.text, "Text should preserve newline"

    def test_parser_c_20_prevent_section_directive_bleeding(self, parser: Parser):
        """
        Test Case: PARSER-C-20 (Task 4)
        Validates that section directives don't incorrectly bleed to unrelated elements.
        Ensures element-specific directives take precedence over section directives.
        """
        # Arrange
        markdown = """[background=gray]

### Title

[background=blue]

- Blue List

---

[background=red]

- Red List"""

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert
        assert len(slide.sections) == 2, "Should have 2 sections"

        # Find elements
        title_element = next(
            (
                e
                for e in slide.elements
                if e.element_type == ElementType.TEXT and "Title" in e.text
            ),
            None,
        )
        blue_list = None
        red_list = None

        for elem in slide.elements:
            if elem.element_type == ElementType.BULLET_LIST:
                list_text = " ".join(item.text for item in elem.items)
                if "Blue" in list_text:
                    blue_list = elem
                elif "Red" in list_text:
                    red_list = elem

        # Verify elements exist
        assert title_element is not None, "Should have a title element"
        assert blue_list is not None, "Should have a blue list element"
        assert red_list is not None, "Should have a red list element"

        # Task 4 assertions:
        # 1. First section should have gray background
        section1_bg = slide.sections[0].directives.get("background")
        assert section1_bg == {
            "type": "named",
            "value": "gray",
        }, f"Section 1 should have gray background, got {section1_bg}"

        # 2. Title should inherit gray background from section
        title_bg = title_element.directives.get("background")
        assert title_bg == {
            "type": "named",
            "value": "gray",
        }, f"Title should have gray background, got {title_bg}"

        # 3. Blue list should have blue background (overriding section)
        blue_bg = blue_list.directives.get("background")
        assert blue_bg == {
            "type": "named",
            "value": "blue",
        }, f"Blue list should have blue background, got {blue_bg}"

        # 4. Second section should have red background
        section2_bg = slide.sections[1].directives.get("background")
        assert section2_bg == {
            "type": "named",
            "value": "red",
        }, f"Section 2 should have red background, got {section2_bg}"

        # 5. Red list should inherit red background from its section
        red_bg = red_list.directives.get("background")
        assert red_bg == {
            "type": "named",
            "value": "red",
        }, f"Red list should have red background, got {red_bg}"

    def test_parser_c_21_nested_subsection_directive_targeting(self, parser: Parser):
        """
        Test Case: PARSER-C-21 (New for Unified Hierarchical Directive Scoping)
        Validates the "Targeting a specific column (nested subsection)" case from the cookbook.
        Demonstrates hierarchical proximity - directives apply to the smallest containing section.
        """
        # Arrange - from the cookbook example
        markdown = """Top Content
---
Left Column
***
[background=blue]
This right column is blue."""

        # Act
        deck = parser.parse(markdown)
        slide = deck.slides[0]

        # Assert - Structural validation
        assert (
            len(slide.sections) == 2
        ), "Should have 2 top-level sections (vertical split)"

        top_section = slide.sections[0]
        bottom_section = slide.sections[1]

        # Bottom section should have subsections (horizontal split)
        assert (
            len(bottom_section.children) >= 2
        ), "Bottom section should have left and right subsections"

        # Find the subsections
        left_subsection = None
        right_subsection = None

        for child in bottom_section.children:
            if hasattr(child, "children"):  # It's a section
                # Check content to identify left vs right
                content_text = ""
                for subchild in child.children:
                    if hasattr(subchild, "text"):
                        content_text += subchild.text

                if "Left Column" in content_text:
                    left_subsection = child
                elif "right column" in content_text:
                    right_subsection = child

        assert left_subsection is not None, "Should have left subsection"
        assert right_subsection is not None, "Should have right subsection"

        # CRITICAL ASSERTION: The background=blue directive should ONLY be on the right subsection
        assert (
            "background" not in top_section.directives
        ), "Top section should NOT have the background directive"
        assert (
            "background" not in bottom_section.directives
        ), "Bottom section should NOT have the background directive"
        assert (
            "background" not in left_subsection.directives
        ), "Left subsection should NOT have the background directive"
        # Check that the background directive is properly converted
        background_directive = right_subsection.directives.get("background")
        assert (
            background_directive is not None
        ), "Right subsection should have a background directive"
        assert background_directive == {
            "type": "named",
            "value": "blue",
        }, "Right subsection should have the blue background directive (converted format)"

        # Validate that the directive is properly scoped to just the right column
        assert (
            len(right_subsection.children) > 0
        ), "Right subsection should have content"

        # The content in the right subsection should be able to inherit the directive
        right_content = right_subsection.children[0]
        if hasattr(right_content, "text"):
            assert (
                "This right column is blue" in right_content.text
            ), "Right content should contain expected text"
