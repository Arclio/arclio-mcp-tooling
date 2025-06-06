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
    # This is a bit of a hack since the formatter part of the class is for parsing,
    # and the request generation part is for API building. We can instantiate it
    # directly as it doesn't require the factory for request generation methods.
    return ListRequestBuilder()


@pytest.fixture(autouse=True)
def inject_factory(builder: ListRequestBuilder):
    """Injects a mock factory to satisfy the constructor, though not used in these tests."""
    from unittest.mock import MagicMock

    builder.element_factory = MagicMock()


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
                if "updateTextStyle" in r
                and "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
            "rgbColor"
        ] == builder._hex_to_rgb("#123456")
        assert (
            style_req["updateTextStyle"]["fields"] == "foregroundColor"
        )  # Correct field mask
        assert style_req["updateTextStyle"]["textRange"]["type"] == "ALL"

    def test_generate_list_with_color_directive_theme(
        self, builder: ListRequestBuilder
    ):
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
                if "updateTextStyle" in r
                and "foregroundColor" in r["updateTextStyle"]["style"]
            ),
            None,
        )
        assert style_req is not None
        assert (
            style_req["updateTextStyle"]["style"]["foregroundColor"]["opaqueColor"][
                "themeColor"
            ]
            == "ACCENT2"
        )
        assert (
            style_req["updateTextStyle"]["fields"] == "foregroundColor"
        )  # Correct field mask
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
                if "updateTextStyle" in r
                and "fontSize" in r["updateTextStyle"]["style"]
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
                if "updateTextStyle" in r
                and "fontFamily" in r["updateTextStyle"]["style"]
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
                    formatting=[
                        TextFormat(start=6, end=10, format_type=TextFormatType.BOLD)
                    ],
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
                if "updateTextStyle" in r
                and r["updateTextStyle"]["style"].get("bold") is True
            ),
            None,
        )

        assert bold_style_req is not None
        assert bold_style_req["updateTextStyle"]["objectId"] == "list_item_fmt"
        assert bold_style_req["updateTextStyle"]["textRange"]["type"] == "FIXED_RANGE"

        # The builder creates a tab character `\t` for indentation, which shifts indices.
        # "Hello bold world \n" -> "\tHello bold world \n"
        # The start and end indices need to be offset by 1.
        assert bold_style_req["updateTextStyle"]["textRange"]["startIndex"] == 6 + 1
        assert bold_style_req["updateTextStyle"]["textRange"]["endIndex"] == 10 + 1
        assert bold_style_req["updateTextStyle"]["fields"] == "bold"

    def test_themed_list_with_subheading_clears_placeholder(
        self, builder: ListRequestBuilder
    ):
        """Test that a themed list with subheading generates a deleteText request."""
        subheading = {"text": "My Subheading", "placeholder_id": "ph_body"}
        list_element = ListElement(
            element_type=ElementType.BULLET_LIST,
            items=[ListItem(text="Item 1")],
            object_id="list_themed",
        )
        theme_placeholders = {ElementType.BULLET_LIST: "ph_body"}

        requests = builder.generate_bullet_list_element_requests(
            list_element, "slide1", theme_placeholders, subheading
        )

        # Check for deleteText request
        delete_req = next(
            (r for r in requests if "deleteText" in r),
            None,
        )
        assert delete_req is not None, "deleteText request should be present"
        assert delete_req["deleteText"]["objectId"] == "ph_body"
        assert delete_req["deleteText"]["textRange"]["type"] == "ALL"

        # Check for insertText request
        insert_req = next(
            (r for r in requests if "insertText" in r),
            None,
        )
        assert insert_req is not None
        assert "My Subheading" in insert_req["insertText"]["text"]
        assert "Item 1" in insert_req["insertText"]["text"]
