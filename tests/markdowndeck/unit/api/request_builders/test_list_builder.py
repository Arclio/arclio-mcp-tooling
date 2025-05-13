import pytest
from markdowndeck.api.request_builders.list_builder import ListRequestBuilder
from markdowndeck.models import (
    ElementType,
    ListElement,
    ListItem,
    TextFormat,
    TextFormatType,
)


@pytest.fixture
def builder() -> ListRequestBuilder:
    return ListRequestBuilder()


class TestListRequestBuilderStyling:
    def test_generate_list_with_color_directive_hex(self, builder: ListRequestBuilder):
        element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Colored Item")],
            object_id="list_color_hex",
            directives={"color": "#123456"},
        )
        requests = builder.generate_bullet_list_element_requests(element, "slide1")

        # createShape, insertText, createParagraphBullets, updateTextStyle for color
        assert len(requests) >= 4

        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r and "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert style_req["updateTextStyle"]["style"]["foregroundColor"][
            "rgbColor"
        ] == builder._hex_to_rgb("#123456")
        assert (
            style_req["updateTextStyle"]["fields"] == "foregroundColor.rgbColor"
        )  # Updated to be more specific
        assert style_req["updateTextStyle"]["textRange"]["type"] == "ALL"

    def test_generate_list_with_color_directive_theme(self, builder: ListRequestBuilder):
        element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Theme Colored Item")],
            object_id="list_color_theme",
            directives={"color": "ACCENT2"},
        )
        requests = builder.generate_bullet_list_element_requests(element, "slide1")

        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r and "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert style_req["updateTextStyle"]["style"]["foregroundColor"]["themeColor"] == "ACCENT2"
        assert style_req["updateTextStyle"]["fields"] == "foregroundColor.themeColor"  # Updated
        assert style_req["updateTextStyle"]["textRange"]["type"] == "ALL"

    def test_generate_list_with_fontsize_directive(self, builder: ListRequestBuilder):
        element = ListElement(
            element_type=ElementType.ORDERED_LIST,
            items=[ListItem(text="Sized Item")],
            object_id="list_fontsize",
            directives={"fontsize": 18},
        )
        requests = builder.generate_list_element_requests(
            element, "slide1", "NUMBERED_DIGIT_ALPHA_ROMAN"
        )

        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r and "fontSize" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert style_req["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 18
        assert style_req["updateTextStyle"]["style"]["fontSize"]["unit"] == "PT"
        assert style_req["updateTextStyle"]["fields"] == "fontSize"
        assert style_req["updateTextStyle"]["textRange"]["type"] == "ALL"

    def test_generate_list_with_font_directive(self, builder: ListRequestBuilder):
        element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Font Item")],
            object_id="list_font",
            directives={"font": "Arial"},
        )
        requests = builder.generate_bullet_list_element_requests(element, "slide1")

        style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r and "fontFamily" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert style_req["updateTextStyle"]["style"]["fontFamily"] == "Arial"
        assert style_req["updateTextStyle"]["fields"] == "fontFamily"

    def test_list_item_formatting_is_applied(self, builder: ListRequestBuilder):
        element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[
                ListItem(
                    text="Hello bold world",
                    formatting=[TextFormat(start=6, end=10, format_type=TextFormatType.BOLD)],
                )
            ],
            object_id="list_item_fmt",
        )
        requests = builder.generate_bullet_list_element_requests(element, "slide1")

        # createShape, insertText (full text), createParagraphBullets, updateTextStyle (for bold)
        assert len(requests) >= 4

        bold_style_req = next(
            (
                r
                for r in requests
                if "updateTextStyle" in r and r["updateTextStyle"]["style"].get("bold") is True
            ),
            None,
        )

        assert bold_style_req is not None
        assert bold_style_req["updateTextStyle"]["objectId"] == "list_item_fmt"
        assert bold_style_req["updateTextStyle"]["textRange"]["type"] == "FIXED_RANGE"
        assert bold_style_req["updateTextStyle"]["textRange"]["startIndex"] == 6
        assert bold_style_req["updateTextStyle"]["textRange"]["endIndex"] == 10
        assert bold_style_req["updateTextStyle"]["fields"] == "bold"
