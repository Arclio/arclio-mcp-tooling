import pytest
from markdowndeck.api.api_generator import ApiRequestGenerator
from markdowndeck.models import (
    Deck,
    ElementType,
    ListElement,
    ListItem,
    Slide,
    TableElement,
    TextElement,
    TextFormat,
    TextFormatType,
)


@pytest.fixture
def api_generator() -> ApiRequestGenerator:
    return ApiRequestGenerator()


class TestApiGeneratorStylingBugs:
    def test_bug_font_family_not_applied(self, api_generator: ApiRequestGenerator):
        """
        Test Case: API-BUG-05
        Description: Exposes the bug where `font-family` directives are ignored.
        Expected to Fail: YES. The generated request will be missing the `fontFamily`
                     style property and/or the corresponding field mask.
        """
        # Arrange
        element = TextElement(
            element_type=ElementType.TEXT,
            text="This should be monospace.",
            object_id="font_family_el",
            position=(50, 50),
            size=(400, 100),
            directives={"font-family": "Courier New"},
        )
        slide = Slide(object_id="s1", renderable_elements=[element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]
        style_req = next(
            (
                r["updateTextStyle"]
                for r in requests
                if "updateTextStyle" in r
                and r["updateTextStyle"]["objectId"] == "font_family_el"
            ),
            None,
        )

        # Assert
        assert (
            style_req is not None
        ), "updateTextStyle request for font family is missing."
        assert (
            "fontFamily" in style_req["style"]
        ), "Style payload is missing 'fontFamily' key."
        assert style_req["style"]["fontFamily"] == "Courier New"
        assert (
            "fontFamily" in style_req["fields"]
        ), "Field mask is missing 'fontFamily'."

    def test_bug_list_item_color_directive_not_applied(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-BUG-06
        Description: Exposes the bug where a color directive on a list item is not applied.
        Expected to Fail: YES. No specific `updateTextStyle` request will be generated for
                     the styled list item's text range.
        """
        # Arrange
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            object_id="styled_list_1",
            position=(50, 50),
            size=(400, 200),
            items=[
                ListItem(text="Regular Item", level=0),
                ListItem(
                    text="Red Item",
                    level=0,
                    # This formatting would be added by a more advanced parser,
                    # but we can add it manually to test the generator.
                    formatting=[
                        TextFormat(
                            start=0,
                            end=8,
                            format_type=TextFormatType.COLOR,
                            value="red",
                        )
                    ],
                ),
            ],
        )
        slide = Slide(object_id="s1", renderable_elements=[list_element])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Find the styling request for the red text
        color_style_req = None
        for r in requests:
            if "updateTextStyle" in r:
                style = r["updateTextStyle"].get("style", {})
                if "foregroundColor" in style:
                    color = (
                        style["foregroundColor"]
                        .get("opaqueColor", {})
                        .get("rgbColor", {})
                    )
                    if color.get("red") == 1.0 and color.get("green") == 0.0:
                        color_style_req = r
                        break

        # Assert
        assert (
            color_style_req is not None
        ), "BUG CONFIRMED: No 'updateTextStyle' request was generated to apply the red color to the list item."

    def test_bug_table_row_text_color_not_applied(
        self, api_generator: ApiRequestGenerator
    ):
        """
        Test Case: API-BUG-07
        Description: Exposes the bug where a text `color` directive on a table row is not applied.
        Expected to Fail: YES. No `updateTextStyle` request for the table row will be generated.
        """
        # Arrange
        table = TableElement(
            element_type=ElementType.TABLE,
            object_id="table_text_color_bug",
            position=(50, 50),
            size=(400, 200),
            headers=["H1"],
            rows=[["R1"]],
            row_directives=[
                {},
                {"color": "#0000FF"},  # Blue text for the first data row
            ],
        )
        slide = Slide(object_id="s1", renderable_elements=[table])
        deck = Deck(slides=[slide])

        # Act
        requests = api_generator.generate_batch_requests(deck, "pres_id")[0]["requests"]

        # Find the specific text style request for the table cell
        text_color_req = None
        for r in requests:
            if "updateTextStyle" in r:
                update_req = r["updateTextStyle"]
                if (
                    update_req.get("objectId") == "table_text_color_bug"
                    and "cellLocation" in update_req
                ) and (
                    update_req["cellLocation"].get("rowIndex") == 1
                ):  # Row index 1 (first data row)
                    text_color_req = update_req
                    break

        # Assert
        assert (
            text_color_req is not None
        ), "BUG CONFIRMED: `updateTextStyle` request for the styled table row is missing."
        style = text_color_req["style"]
        assert (
            "foregroundColor" in style
        ), "foregroundColor property is missing from style."
        rgb = style["foregroundColor"]["opaqueColor"]["rgbColor"]
        assert (
            abs(rgb["blue"] - 1.0) < 0.01
        ), "Text color was not correctly set to blue."
