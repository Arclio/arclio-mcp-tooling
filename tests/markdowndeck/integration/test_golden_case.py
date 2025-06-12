"""
A comprehensive, end-to-end "golden case" test for the full pipeline.
"""

import pytest
from markdowndeck import markdown_to_requests

GOLDEN_MARKDOWN = """
# Slide 1: Title Styling [color=#0000FF]

This is the main content.

===
# Slide 2: Section Styling

[background=#333333]
This section should have a dark background.

---
[width=150][align=center]
This is a second, narrow, centered section.

===
# Slide 3: Columnar Layout

Implicit Column
***
[width=25%]
Proportional Column
***
[width=150]
Absolute Column

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


def _find_element_shape_id(slide_batch, text_content_substring: str) -> str | None:
    """Finds the objectId of the shape containing specific text."""
    for req in slide_batch["requests"]:
        if "insertText" in req and text_content_substring in req["insertText"]["text"]:
            return req["insertText"]["objectId"]
    return None


class TestGoldenCase:
    def test_slide_count(self, golden_output):
        """Asserts the correct number of slides are generated."""
        assert (
            len(golden_output["slide_batches"]) == 4
        ), "Golden markdown should produce 4 slides."

    def test_slide_1_title_styling(self, golden_output):
        """Asserts Slide 1's title has the correct color directive applied."""
        slide_1_batch = golden_output["slide_batches"][0]
        title_id = _find_element_shape_id(slide_1_batch, "Slide 1: Title Styling")
        assert title_id is not None, "Could not find title element for Slide 1."

        style_req = next(
            (
                r
                for r in slide_1_batch["requests"]
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == title_id
            ),
            None,
        )
        assert style_req is not None, "No text style update found for the title."

        color = style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
            "rgbColor"
        ]
        assert abs(color["blue"] - 1.0) < 1e-9, "Title color should be blue."

    def test_slide_2_section_background(self, golden_output):
        """Asserts Slide 2's first section has the correct background color."""
        slide_2_batch = golden_output["slide_batches"][1]
        section_id = _find_element_shape_id(slide_2_batch, "dark background")
        assert (
            section_id is not None
        ), "Could not find section text element for Slide 2."

        style_req = next(
            (
                r
                for r in slide_2_batch["requests"]
                if "updateShapeProperties" in r
                and r["updateShapeProperties"]["objectId"] == section_id
            ),
            None,
        )
        assert (
            style_req is not None
        ), "No shape properties update found for the section."

        fields = style_req["updateShapeProperties"]["fields"]
        assert "shapeBackgroundFill" in fields, "Background fill not being updated."

    def test_slide_3_column_widths(self, golden_output):
        """Asserts Slide 3's columns have correctly calculated widths."""
        slide_3_batch = golden_output["slide_batches"][2]

        implicit_id = _find_element_shape_id(slide_3_batch, "Implicit Column")
        proportional_id = _find_element_shape_id(slide_3_batch, "Proportional Column")
        absolute_id = _find_element_shape_id(slide_3_batch, "Absolute Column")

        shapes = {
            r["createShape"]["objectId"]: r["createShape"]
            for r in slide_3_batch["requests"]
            if "createShape" in r
        }

        assert implicit_id in shapes
        assert proportional_id in shapes
        assert absolute_id in shapes

        assert (
            abs(
                shapes[implicit_id]["elementProperties"]["size"]["width"]["magnitude"]
                - 390.0
            )
            < 1.0
        )
        assert (
            abs(
                shapes[proportional_id]["elementProperties"]["size"]["width"][
                    "magnitude"
                ]
                - 180.0
            )
            < 1.0
        )
        assert (
            abs(
                shapes[absolute_id]["elementProperties"]["size"]["width"]["magnitude"]
                - 150.0
            )
            < 1.0
        )

    def test_slide_4_code_escaping(self, golden_output):
        """Asserts Slide 4's code block content is preserved correctly."""
        slide_4_batch = golden_output["slide_batches"][3]
        code_id = _find_element_shape_id(slide_4_batch, "x = 1")
        assert code_id is not None, "Could not find code element for Slide 4."

        insert_req = next(
            (
                r
                for r in slide_4_batch["requests"]
                if "insertText" in r and r["insertText"]["objectId"] == code_id
            ),
            None,
        )
        assert (
            "---" in insert_req["insertText"]["text"]
        ), "Separator inside code block must be preserved."
