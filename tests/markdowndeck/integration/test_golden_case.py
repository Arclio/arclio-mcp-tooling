"""
A comprehensive, end-to-end "golden case" test for the full pipeline, updated for the new architecture.
"""

import pytest
from markdowndeck import markdown_to_requests

# REFACTORED: Updated to use the new fenced block syntax per ARCHITECTURE.md.
# The `---` and `***` separators are deprecated.
GOLDEN_MARKDOWN = """
# Slide 1: Title Styling [color=#0000FF]

This is the main content.

===
# Slide 2: Section Styling

:::section [background=#333333]
This section should have a dark background.
:::

:::section [width=150][align=center]
This is a second, narrow, centered section.
:::

===
# Slide 3: Columnar Layout

:::row
:::column
Implicit Column
:::
:::column [width=25%]
Proportional Column
:::
:::column [width=150]
Absolute Column
:::
:::

===
# Slide 4: Code Block Escaping
```python
# The '---' separator below is ignored.
---
x = 1
```
"""


@pytest.fixture(scope="module")
def golden_output():
    """Runs the full pipeline and returns the final API request dictionary."""
    return markdown_to_requests(GOLDEN_MARKDOWN, title="Golden Case Deck")


def _find_element_shape_by_text(slide_batch, text_content_substring: str) -> dict | None:
    """Finds the createShape request data for the shape containing specific text."""
    text_req = next(
        (r for r in slide_batch["requests"] if "insertText" in r and text_content_substring in r["insertText"]["text"]),
        None,
    )
    if not text_req:
        return None
    object_id = text_req["insertText"]["objectId"]

    shape_req = next(
        (r for r in slide_batch["requests"] if "createShape" in r and r["createShape"]["objectId"] == object_id),
        None,
    )
    return shape_req["createShape"] if shape_req else None


class TestGoldenCase:
    def test_slide_count(self, golden_output):
        """Asserts the correct number of slides are generated."""
        assert len(golden_output["slide_batches"]) == 4, "Golden markdown should produce 4 slides."

    def test_slide_1_title_styling(self, golden_output):
        """Asserts Slide 1's title has the correct color directive applied."""
        slide_1_batch = golden_output["slide_batches"][0]
        # Find the title shape by looking for an insertText request with its content
        text_req = next(
            (
                r
                for r in slide_1_batch["requests"]
                if "insertText" in r and "Slide 1: Title Styling" in r["insertText"]["text"]
            ),
            None,
        )
        assert text_req is not None, "Could not find text insert for Slide 1 title."
        title_shape_id = text_req["insertText"]["objectId"]

        style_req = next(
            (
                r
                for r in slide_1_batch["requests"]
                if "updateTextStyle" in r and r["updateTextStyle"]["objectId"] == title_shape_id
            ),
            None,
        )
        assert style_req is not None, "No text style update found for the title."

        color = style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert abs(color["blue"] - 1.0) < 1e-9, "Title color should be blue."

    def test_slide_2_section_background(self, golden_output):
        """Asserts Slide 2's first section has the correct background color."""
        slide_2_batch = golden_output["slide_batches"][1]
        section_shape = _find_element_shape_by_text(slide_2_batch, "dark background")
        assert section_shape is not None, "Could not find section text element for Slide 2."

        style_req = next(
            (
                r
                for r in slide_2_batch["requests"]
                if "updateShapeProperties" in r
                and r["updateShapeProperties"]["objectId"] == section_shape["objectId"]
                and "shapeBackgroundFill" in r["updateShapeProperties"].get("shapeProperties", {})
            ),
            None,
        )
        assert style_req is not None, "No shape properties update found for the section's element."

        props = style_req["updateShapeProperties"]
        color = props["shapeProperties"]["shapeBackgroundFill"]["solidFill"]["color"]["rgbColor"]
        assert abs(color["red"] - 0.2) < 0.01
        assert abs(color["green"] - 0.2) < 0.01
        assert abs(color["blue"] - 0.2) < 0.01

    def test_slide_3_column_widths(self, golden_output):
        """Asserts Slide 3's columns have correctly calculated widths."""
        slide_3_batch = golden_output["slide_batches"][2]

        implicit_shape = _find_element_shape_by_text(slide_3_batch, "Implicit Column")
        proportional_shape = _find_element_shape_by_text(slide_3_batch, "Proportional Column")
        absolute_shape = _find_element_shape_by_text(slide_3_batch, "Absolute Column")

        assert implicit_shape is not None
        assert proportional_shape is not None
        assert absolute_shape is not None

        # Content area width is 720 (no margins in this test fixture). No gap.
        # Absolute takes 150. Remaining: 570.
        # Proportional takes 25% of 720 = 180. Remaining: 390.
        # Implicit takes the rest.
        assert abs(implicit_shape["elementProperties"]["size"]["width"]["magnitude"] - 390.0) < 5.0
        assert abs(proportional_shape["elementProperties"]["size"]["width"]["magnitude"] - 180.0) < 5.0
        assert abs(absolute_shape["elementProperties"]["size"]["width"]["magnitude"] - 150.0) < 5.0

    def test_slide_4_code_escaping(self, golden_output):
        """Asserts Slide 4's code block content is preserved correctly."""
        slide_4_batch = golden_output["slide_batches"][3]
        code_shape = _find_element_shape_by_text(slide_4_batch, "x = 1")
        assert code_shape is not None, "Could not find code element for Slide 4."

        insert_req = next(
            (
                r
                for r in slide_4_batch["requests"]
                if "insertText" in r and r["insertText"]["objectId"] == code_shape["objectId"]
            ),
            None,
        )
        assert insert_req is not None
        assert "---" in insert_req["insertText"]["text"], "Separator inside code block must be preserved."
