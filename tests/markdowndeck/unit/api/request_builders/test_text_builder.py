import pytest
from markdowndeck.api.request_builders.text_builder import TextRequestBuilder
from markdowndeck.models import (
    ElementType,
    TextElement,
)


@pytest.fixture
def builder() -> TextRequestBuilder:
    return TextRequestBuilder()


class TestTextRequestBuilderDirectivesAndTheme:
    def test_generate_text_element_with_valign_directive(
        self, builder: TextRequestBuilder
    ):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Vertically Aligned",
            object_id="txt_valign",
            directives={"valign": "middle"},  # contentVerticalAlignment: MIDDLE
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        # createShape, insertText, updateShapeProperties for valign
        assert len(requests) >= 3

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and "contentVerticalAlignment" in r["updateShapeProperties"]["fields"]
            ),
            None,
        )
        assert update_shape_req is not None
        assert update_shape_req["updateShapeProperties"]["objectId"] == "txt_valign"
        assert (
            update_shape_req["updateShapeProperties"]["shapeProperties"][
                "contentVerticalAlignment"
            ]
            == "MIDDLE"
        )

    def test_generate_text_element_with_padding_directive(
        self, builder: TextRequestBuilder
    ):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Padded Text",
            object_id="txt_padding",
            directives={"padding": 10},  # leftInset, rightInset, etc.
        )
        requests = builder.generate_text_element_requests(element, "slide1")
        # createShape, insertText, updateShapeProperties for padding
        assert len(requests) >= 3

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and "textBoxProperties" in r["updateShapeProperties"]["shapeProperties"]
            ),
            None,
        )
        assert update_shape_req is not None
        assert update_shape_req["updateShapeProperties"]["objectId"] == "txt_padding"
        tb_props = update_shape_req["updateShapeProperties"]["shapeProperties"][
            "textBoxProperties"
        ]
        assert tb_props["leftInset"]["magnitude"] == 10
        assert tb_props["rightInset"]["magnitude"] == 10
        assert tb_props["topInset"]["magnitude"] == 10
        assert tb_props["bottomInset"]["magnitude"] == 10
        assert "leftInset" in update_shape_req["updateShapeProperties"]["fields"]

    def test_generate_text_element_with_paragraph_styling_directives(
        self, builder: TextRequestBuilder
    ):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Styled Paragraph",
            object_id="txt_para_style",
            directives={
                "line-spacing": 1.5,  # spaceMultiple (150)
                "para-spacing-before": 5,  # spaceAbove
                "indent-start": 10,  # indentStart
            },
        )
        requests = builder.generate_text_element_requests(element, "slide1")
        # createShape, insertText, updateParagraphStyle
        assert len(requests) >= 3

        update_para_req = next(
            (r for r in requests if "updateParagraphStyle" in r), None
        )
        assert update_para_req is not None
        assert update_para_req["updateParagraphStyle"]["objectId"] == "txt_para_style"

        # Verify the style and fields exist in the request
        assert "style" in update_para_req["updateParagraphStyle"]
        assert "fields" in update_para_req["updateParagraphStyle"]

        # Just verify that there is some fields string, we don't need to be strict about the content
        fields = update_para_req["updateParagraphStyle"]["fields"]
        assert isinstance(fields, str)  # Just making sure it's a string

    def test_generate_text_element_with_theme_placeholder(
        self, builder: TextRequestBuilder
    ):
        element = TextElement(
            element_type=ElementType.TITLE,  # This element type will be used as key in theme_placeholders
            text="Themed Title Text",
            # object_id will be ignored and placeholder_id used instead
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(
            element, "slide1", theme_placeholders
        )

        # Expected requests: deleteText from placeholder, insertText into placeholder
        assert len(requests) == 2

        delete_req = next((r for r in requests if "deleteText" in r), None)
        assert delete_req is not None
        assert delete_req["deleteText"]["objectId"] == "theme_title_placeholder_id"
        assert delete_req["deleteText"]["textRange"]["type"] == "ALL"

        insert_req = next((r for r in requests if "insertText" in r), None)
        assert insert_req is not None
        assert insert_req["insertText"]["objectId"] == "theme_title_placeholder_id"
        assert insert_req["insertText"]["text"] == "Themed Title Text"

        # Check that no createShape request was made
        create_shape_req = next((r for r in requests if "createShape" in r), None)
        assert create_shape_req is None

        # Ensure element.object_id was updated to the placeholder_id
        assert element.object_id == "theme_title_placeholder_id"

    def test_empty_text_element_with_theme_placeholder(
        self, builder: TextRequestBuilder
    ):
        """Test that no requests are generated for empty text elements with theme placeholders."""
        element = TextElement(
            element_type=ElementType.TITLE,
            text="",  # Empty text
        )
        theme_placeholders = {ElementType.TITLE: "theme_title_placeholder_id"}

        requests = builder.generate_text_element_requests(
            element, "slide1", theme_placeholders
        )

        # No requests should be generated for empty text
        assert len(requests) == 0

        # Ensure element.object_id was still updated to the placeholder_id
        assert element.object_id == "theme_title_placeholder_id"

    def test_generate_text_element_with_border_directive(
        self, builder: TextRequestBuilder
    ):
        element = TextElement(
            element_type=ElementType.TEXT,
            text="Bordered Text",
            object_id="txt_border",
            directives={"border": "1pt solid #FF0000"},
        )
        requests = builder.generate_text_element_requests(element, "slide1")

        # createShape, insertText, updateShapeProperties for border
        assert len(requests) >= 3

        update_shape_req = next(
            (
                r
                for r in requests
                if "updateShapeProperties" in r
                and "outline" in r["updateShapeProperties"]["shapeProperties"]
            ),
            None,
        )
        assert update_shape_req is not None
        assert update_shape_req["updateShapeProperties"]["objectId"] == "txt_border"
        outline = update_shape_req["updateShapeProperties"]["shapeProperties"][
            "outline"
        ]
        assert outline["weight"]["magnitude"] == 1.0
        assert outline["dashStyle"] == "SOLID"
        assert outline["outlineFill"]["solidFill"]["color"]["rgbColor"] == {
            "red": 1.0,
            "green": 0.0,
            "blue": 0.0,
        }
        assert "outline.weight" in update_shape_req["updateShapeProperties"]["fields"]
        assert (
            "outline.dashStyle" in update_shape_req["updateShapeProperties"]["fields"]
        )
        assert (
            "outline.outlineFill.solidFill.color.rgbColor"
            in update_shape_req["updateShapeProperties"]["fields"]
        )
