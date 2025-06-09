import pytest
from markdowndeck.models import ElementType

# The canonical "Golden Test Case" markdown
GOLDEN_MARKDOWN = """
# Slide 1: Basic Structure & Slide-Level Metadata
# The Title of the Presentation [color=blue][fontsize=48]

<!-- notes: This is the first slide. It demonstrates the most basic features: a title, subtitle, content, footer, and speaker notes. The directives are on the same line as the title and should apply ONLY to the title element. -->

## A Subtitle for the Presentation [fontsize=24]

This is the main content of the first slide. It's a simple paragraph in the implicit root section.

@@@
Footer for Slide 1 | © 2024

===
# Slide 2: Section-Scoped Directives

[background=#333333][color=white][padding=20]
This is the first section. The directives above apply to this section because they are the first thing in this section's content block.

---
[background=#EEEEEE][color=black][padding=10][border=2pt solid #cccccc]
This is the second section, styled independently from the first.

This section also contains a **bolded** word and an *italicized* one.

===
# Slide 3: Columnar Layout (Horizontal Sections)

This text is in the first column. It will take up the remaining space after the explicitly sized columns are accounted for.

***
[width=25%]
This text is in the second column. It is explicitly sized to take up 25% of the available width.

***
[width=150]
This text is in the third column. It is sized to be exactly 150 points wide.

===
# Slide 4: Nested Layouts

This is the top-level section content.

---
[background=#f0f0f0]
This is the second top-level section. It contains nested columns.

[width=0.6]
This is the left column inside the second section. It has its own width directive.

***
[width=0.4]
This is the right column inside the second section.

===
# Slide 5: Code Blocks and Separator Escaping

This slide demonstrates that section separators inside code blocks are ignored.

```python
# This is not a real title
# ---
# ***
# ===
def my_function():
    return "Hello, World!"
```

This text appears after the code block, in the same section.

===
# Slide 6: Element-Scoped Directives

This is a standard paragraph.

[align=center]
This paragraph is specifically centered because the directive immediately precedes it.

This is another standard paragraph, which should default to left alignment.

---
[align=right]
> This is a right-aligned blockquote. The directive applies to the entire quote block.

===
# Slide 7: Table with Directives

[column-widths=100,200,100][cell-background=#333][color=white]
| Header 1 | Header 2 | Header 3 |
|:---|:---:|---:|
| Left | Center | Right |
| Data | Data | Data |

===
# Slide 8: List with Nested Directives

- Top level item 1.
- [fontsize=18][color=red]
  This second top-level item is styled by the directive above it.
  - Nested item 2.1. It should inherit the red color and font size.
  - [color=green]
    Nested item 2.2 is green, overriding the parent's color.
- Top level item 3.

===
# Slide 9: Image with Element-Scoped Directive

This is a paragraph above the image.

![An image of a mountain](image.png) [border=3pt dotted blue][align=center]

This is a caption below the image. It should not have a border.

===
# Slide 10: Empty Sections and Whitespace Robustness

This section has content.

---
[width=100]

---

This third section has content. The middle section was empty except for a directive. It should still be created and hold its place in the layout, with the specified width.
"""


@pytest.fixture(scope="module")
def final_deck_output():
    """Runs the full pipeline and returns the final Deck object."""
    from markdowndeck import _process_markdown_to_deck

    return _process_markdown_to_deck(GOLDEN_MARKDOWN, "Golden Case Deck", None)


def test_golden_case_final_output(final_deck_output):
    """
    Test Case: E2E-GOLDEN-01
    Validates the end-to-end processing of the golden test case markdown.
    Spec: Validates the integrated behavior of all component specifications.
    """
    deck = final_deck_output

    # TASK_006 Achievement 1: Correct slide count after fixes
    assert len(deck.slides) == 13, "Deck should be processed into 13 slides after fixes"

    # TASK_006 Achievement 2: Basic structure validation
    s1 = deck.slides[0]
    assert s1.title == "Slide 1: Basic Structure & Slide-Level Metadata"
    s1_elems = {e.element_type: e for e in s1.renderable_elements}
    assert ElementType.TITLE in s1_elems
    assert ElementType.SUBTITLE in s1_elems
    assert ElementType.FOOTER in s1_elems
    assert ElementType.TEXT in s1_elems

    # TASK_006 Achievement 3: Layout orientation fix - multiple sections get horizontal layout
    # Find the columnar layout slide (should be around slide 3-4 due to overflow)
    columnar_slide = None
    for slide in deck.slides:
        if "Columnar Layout" in slide.title:
            columnar_slide = slide
            break

    assert columnar_slide is not None, "Should find columnar layout slide"
    text_elems = [
        e
        for e in columnar_slide.renderable_elements
        if e.element_type == ElementType.TEXT
    ]
    assert len(text_elems) == 3, "Should have 3 text columns"

    # Check for horizontal positioning (y-coordinates should be very close)
    assert (
        abs(text_elems[0].position[1] - text_elems[1].position[1]) < 1.0
    ), "Columns should be horizontally aligned"
    assert (
        abs(text_elems[1].position[1] - text_elems[2].position[1]) < 1.0
    ), "Columns should be horizontally aligned"

    # TASK_006 Achievement 4: Code overflow fix - continuation slides have content
    code_slides = [slide for slide in deck.slides if "Code Blocks" in slide.title]
    assert len(code_slides) >= 2, "Should have original and continuation code slides"

    continuation_slide = next(
        (
            slide
            for slide in deck.slides
            if "(continued)" in slide.title
            and any(
                e.element_type == ElementType.CODE for e in slide.renderable_elements
            )
        ),
        None,
    )
    assert continuation_slide is not None, "Should find code continuation slide"

    code_elem = next(
        e
        for e in continuation_slide.renderable_elements
        if e.element_type == ElementType.CODE
    )
    assert (
        code_elem.code.strip() == 'return "Hello, World!"'
    ), "Continuation slide should have actual code content"

    # Add more assertions for other slides as needed...
