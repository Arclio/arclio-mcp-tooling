# tests/markdowndeck/unit/parser/test_slide_extractor_bugs.py
from markdowndeck.parser import Parser


def test_extractor_fails_on_valid_markdown_with_blank_lines():
    """
    Tests that the current implementation incorrectly processes valid markdown
    with blank lines between meta elements as a grammar error, creating an error slide.
    This test is expected to FAIL before the fix and PASS after.
    """
    markdown_with_blank_lines = """
# Real Title

## Real Subtitle

[color=blue]

:::section
Body content
:::
"""
    parser = Parser()

    # The current buggy implementation creates an error slide instead of parsing correctly
    deck = parser.parse(markdown_with_blank_lines)

    # This assertion should fail initially (proving the bug exists)
    # because the current implementation creates an error slide with "Grammar Error" in the title
    assert len(deck.slides) == 1
    slide = deck.slides[0]

    # Currently this will be "Grammar Error in Slide 1" due to the bug
    # After the fix, it should be "Real Title"
    assert (
        "Grammar Error" not in slide.get_title_element().text
    ), f"Expected proper parsing, but got error slide with title: {slide.get_title_element().text}"


def test_refactored_extractor_correctly_parses_valid_markdown():
    """
    Tests that the refactored implementation correctly parses a slide with
    blank lines between meta-elements and correctly separates meta and body zones.
    """
    markdown_with_blank_lines = """
# Real Title [color=red]

## Real Subtitle

[fontsize=12]

:::section
Body content
:::

@@@
Footer content
"""
    parser = Parser()
    deck = parser.parse(markdown_with_blank_lines)

    # There should be no parsing error
    assert len(deck.slides) == 1
    slide = deck.slides[0]

    # 1. Verify Meta-Elements were extracted correctly
    assert slide.get_title_element().text == "Real Title"
    assert slide.get_subtitle_element().text == "Real Subtitle"
    assert slide.get_footer_element().text == "Footer content"

    # 2. Verify Directives were assigned correctly
    assert slide.title_directives == {
        "color": {"type": "color", "value": {"type": "named", "value": "red"}}
    }
    assert slide.subtitle_directives == {}
    assert slide.base_directives == {"fontsize": 12.0}

    # 3. Verify Body Content is correct and isolated
    # The root section should only contain the :::section block
    assert len(slide.root_section.children) == 1
    body_section = slide.root_section.children[0]

    # After content parsing, it should be a Section object
    from markdowndeck.models.slide import Section

    assert isinstance(body_section, Section)
    assert body_section.type == "section"

    # The section should contain one text element with "Body content"
    assert len(body_section.children) == 1
    text_element = body_section.children[0]
    assert text_element.text == "Body content"
